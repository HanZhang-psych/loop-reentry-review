"""Stage 4 — SCREEN.

Screens each record with ONE selected model, sampled several times at varied
temperatures (self-consistency). The empirical agreement across samples is the
confidence signal — not the model's own self-reported confidence, which is
poorly calibrated — and any record whose samples are not consistent is routed
to human review. The screening criteria come from criteria.md (decision rules
only); this module supplies the fixed JSON output contract so parsing stays
robust even when you edit the criteria.

Self-consistency narrows random (sampling) error and gives a calibrated review
gate, but it does NOT provide an independent second opinion: every sample comes
from the same model and shares its systematic blind spots. The human review of
inconsistent records, plus the random audit of the auto-excluded pile, is what
covers the errors resampling cannot see.

Also provides a no-API "dry run" that estimates token usage and cost.
"""
from __future__ import annotations

import os
import re
import json
import time
import hashlib
from collections import Counter
from itertools import cycle, islice

from .common import Record


# --------------------------------------------------------------------------- #
# Criteria loading
# --------------------------------------------------------------------------- #
REASONS_HEADER = "## ALLOWED EXCLUSION REASONS"
INSUFFICIENT_INFO_REASON = "Insufficient information"


def load_criteria(path: str) -> tuple[str, list[str]]:
    """Returns (instructions_text, allowed_reasons)."""
    with open(path, "r", encoding="utf-8") as fh:
        raw = fh.read()
    # drop HTML comments (the file's own usage notes)
    raw = re.sub(r"<!--.*?-->", "", raw, flags=re.DOTALL)

    if REASONS_HEADER not in raw:
        raise ValueError(f"criteria file must contain a '{REASONS_HEADER}' section")
    instructions, reasons_block = raw.split(REASONS_HEADER, 1)
    reasons = [ln.strip()[2:].strip()
               for ln in reasons_block.splitlines()
               if ln.strip().startswith("- ")]
    return instructions.strip(), reasons


def build_system_prompt(instructions: str, reasons: list[str]) -> str:
    reason_list = "\n".join(f"  - {r}" for r in reasons)
    return (
        f"{instructions}\n\n"
        "OUTPUT FORMAT (strict):\n"
        "Return ONLY a single JSON object and nothing else. State your reasoning "
        "FIRST, then commit to the decision:\n"
        '{"rationale": "<one short clause naming the single decisive fact>", '
        '"eligible": "T" or "F", '
        '"reason": "<exact text of one allowed exclusion reason, or empty if eligible>"}\n\n'
        "Rules:\n"
        '  - Work out "rationale" before "eligible"; let the rationale drive the call.\n'
        '  - "eligible" is "T" (include) or "F" (exclude).\n'
        '  - If "F", "reason" MUST be exactly one of the allowed reasons below.\n'
        '  - If "T", leave "reason" empty.\n'
        f"Allowed exclusion reasons:\n{reason_list}\n"
    )


def build_user_content(rec: Record) -> str:
    return (
        f"Author: {rec.authors or 'N/A'}\n"
        f"Year: {rec.year or 'N/A'}\n"
        f"Title: {rec.title or 'N/A'}\n"
        f"Abstract: {rec.abstract or 'N/A'}"
    )


def sample_temperatures(cfg: dict) -> list[float]:
    """The exact temperature used for each self-consistency sample.

    The configured list is recycled (if shorter than `samples`) or truncated
    (if longer), so the returned list always has length == samples.
    """
    sc = cfg["screen"]["self_consistency"]
    n = int(sc["samples"])
    temps = sc.get("temperatures") or [0.0]
    return [float(t) for t in islice(cycle(temps), n)]


# --------------------------------------------------------------------------- #
# Dry-run cost estimate (no API key needed)
# --------------------------------------------------------------------------- #
# Batch pricing = 50% of standard, in USD per million tokens (input, output).
BATCH_RATES = {
    "claude-opus-4-8":   (2.50, 12.50),
    "claude-sonnet-4-6": (1.50,  7.50),
    "claude-sonnet-4-5": (1.50,  7.50),
    "claude-haiku-4-5":  (0.50,  2.50),
}
_DEFAULT_RATE = (2.50, 12.50)

# Prompt-caching minimum cacheable prefix (tokens) by model. If the criteria
# block is below this, `cache_control` silently becomes a no-op and the full
# prompt is billed on EVERY request. Values from the official docs:
# https://platform.claude.com/docs/en/build-with-claude/prompt-caching (2026-07)
# Confirmed empirically for sonnet-4-6 (1024): a real run cached a 1,761-token
# criteria prompt (~$48 vs ~$151 uncached). Note haiku-4-5 is 4096 — the same
# 1,761-token prompt does NOT cache there, which is why Haiku ran pricier.
MIN_CACHEABLE = {
    "claude-fable-5":    512,
    "claude-mythos-5":   512,
    "claude-opus-4-8":   1024,
    "claude-opus-4-7":   2048,
    "claude-opus-4-6":   4096,
    "claude-opus-4-5":   4096,
    "claude-opus-4-1":   1024,
    "claude-sonnet-5":   1024,
    "claude-sonnet-4-6": 1024,
    "claude-sonnet-4-5": 1024,
    "claude-haiku-4-5":  4096,
    "claude-haiku-3-5":  2048,
}
_DEFAULT_MIN_CACHEABLE = 2048


def _system_prompt_tokens(system_prompt: str, model: str) -> tuple[int, str]:
    """Token count of the criteria block, and how it was obtained.

    The realistic estimate turns on whether this clears the model's cache floor,
    so measure it exactly with count_tokens when a key is available; fall back to
    char/4 otherwise. Returns (tokens, "api" | "approx").
    """
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            import anthropic
            c = anthropic.Anthropic()
            probe = [{"role": "user", "content": "x"}]
            total = c.messages.count_tokens(
                model=model, system=system_prompt, messages=probe).input_tokens
            base = c.messages.count_tokens(model=model, messages=probe).input_tokens
            return max(1, total - base), "api"
        except Exception:
            pass
    return max(1, len(system_prompt) // 4), "approx"


def estimate_cost(records, system_prompt, cfg, model, samples) -> dict:
    """Estimate batch-screening cost, modelling prompt caching.

    Reports BOTH an upper bound (`est_usd` — the full criteria prompt billed on
    every request) and a realistic figure (`realistic_usd`) that accounts for
    caching: when the criteria block clears the model's minimum cacheable prefix
    it is written once per batch and read at ~10% price on every other request.
    The per-record abstract is unique and never cached, so it is always billed at
    full input price. This is a PREDICTION from MIN_CACHEABLE + a count_tokens
    proxy; probe_prompt_caching() confirms it against the live API.
    """
    def toks(s):
        return max(1, len(s) // 4)

    s_cfg = cfg["screen"]
    chunk = int(s_cfg.get("batch_chunk_size", 3000)) or 3000
    use_cache = bool(s_cfg.get("use_prompt_caching", False))

    sys_t, sys_source = _system_prompt_tokens(system_prompt, model)
    user_t = sum(toks(build_user_content(r)) for r in records)   # per sample, unique
    overhead = 15 * len(records)                                 # per sample, framing

    n_rec = len(records)
    n_req = n_rec * samples
    in_rate, out_rate = BATCH_RATES.get(model, _DEFAULT_RATE)
    read_rate, write_rate = in_rate * 0.10, in_rate * 1.25

    out_t = 80 * n_req                          # rationale + verdict JSON
    # Upper bound: full system prompt on every request (caching ignored).
    up_in = (user_t + overhead + sys_t * n_rec) * samples
    upper = up_in / 1e6 * in_rate + out_t / 1e6 * out_rate

    # Realistic: cache-aware. The criteria block caches only if enabled AND it
    # clears the model's floor; otherwise it is billed full price every request.
    min_cache = MIN_CACHEABLE.get(model, _DEFAULT_MIN_CACHEABLE)
    caching = use_cache and sys_t >= min_cache
    if caching:
        n_batches = ((n_rec + chunk - 1) // chunk) * samples   # one prefix write each
        writes = min(n_batches, n_req)
        reads = n_req - writes
        sys_cost = (writes * sys_t * write_rate + reads * sys_t * read_rate) / 1e6
        read_frac = reads / n_req
    else:
        sys_cost = n_req * sys_t * in_rate / 1e6
        read_frac = 0.0
    user_cost = (user_t * samples) / 1e6 * in_rate
    over_cost = (overhead * samples) / 1e6 * in_rate
    realistic = sys_cost + user_cost + over_cost + out_t / 1e6 * out_rate

    return {
        "records": n_rec, "samples": samples, "model": model,
        "input_tokens": up_in, "output_tokens": out_t,
        "est_usd": round(upper, 2), "realistic_usd": round(realistic, 2),
        "caching": caching, "sys_tokens": sys_t, "sys_source": sys_source,
        "min_cacheable": min_cache, "cache_read_frac": round(read_frac, 2),
        # Exact count -> tight band; char/4 approx can be ~15% off, so widen it.
        "borderline": use_cache and abs(sys_t - min_cache) < (
            128 if sys_source == "api" else max(128, int(0.20 * min_cache))),
    }


# --------------------------------------------------------------------------- #
# Live prompt-caching probe (ground truth — one real API call pair)
# --------------------------------------------------------------------------- #
def probe_prompt_caching(system_prompt: str, model: str, cfg: dict) -> dict:
    """Live check of whether this model ACTUALLY caches the criteria prefix.

    estimate_cost only *predicts* caching from the MIN_CACHEABLE table and a
    count_tokens proxy. This measures it: it sends the exact system block the
    batch will send (same text, same cache_control) twice via the Messages API
    and reads the cache accounting back from `usage`. The prefix caches iff the
    second, identical request is served with cache_read_input_tokens > 0.

    Costs a fraction of a cent (max_tokens=1). Requires ANTHROPIC_API_KEY. On
    any failure returns {"error": "..."} so the caller can degrade to the
    prediction rather than crash.
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return {"error": "ANTHROPIC_API_KEY not set — cannot run a live probe"}

    import anthropic

    client = anthropic.Anthropic()
    system_block = [{"type": "text", "text": system_prompt,
                     "cache_control": {"type": "ephemeral"}}]
    probe_msg = [{"role": "user", "content": "verify prompt caching"}]

    def _usage():
        u = client.messages.create(
            model=model, max_tokens=1, temperature=0.0,
            system=system_block, messages=probe_msg).usage
        return {
            "input": u.input_tokens,
            "write": getattr(u, "cache_creation_input_tokens", 0) or 0,
            "read": getattr(u, "cache_read_input_tokens", 0) or 0,
        }

    try:
        first = _usage()    # cold: writes the prefix to cache (unless already warm)
        second = _usage()   # warm: reads the prefix from cache iff it is cacheable
    except Exception as e:  # noqa: BLE001 — surface any API failure to the caller
        return {"error": f"{type(e).__name__}: {e}"}

    # The identical second request is the definitive signal: a cacheable prefix
    # is read back; a below-floor prefix is re-billed as full input on both.
    active = second["read"] > 0
    cached_tokens = first["write"] or second["read"] or first["read"]
    return {
        "active": active,
        "cached_prefix_tokens": cached_tokens,
        "first": first, "second": second,
        "min_cacheable": MIN_CACHEABLE.get(model, _DEFAULT_MIN_CACHEABLE),
    }


# --------------------------------------------------------------------------- #
# Result parsing + aggregation across samples
# --------------------------------------------------------------------------- #
def parse_verdict(text: str, allowed_reasons: list[str]) -> dict:
    """Parse one sample's raw text into a single verdict dict."""
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return {"rationale": "", "eligible": "", "reason": "",
                "parse_error": True, "off_vocab_reason": False, "raw": text[:500]}
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return {"rationale": "", "eligible": "", "reason": "",
                "parse_error": True, "off_vocab_reason": False, "raw": text[:500]}

    elig = str(obj.get("eligible", "")).strip().upper()
    if elig not in ("T", "F"):
        elig = ""
    reason = str(obj.get("reason", "") or "").strip()
    return {
        "rationale": str(obj.get("rationale", "") or "").strip(),
        "eligible": elig,
        "reason": reason,
        "parse_error": False,
        "off_vocab_reason": bool(elig == "F" and reason and reason not in allowed_reasons),
        "raw": text[:500],
    }


def aggregate_samples(verdicts: list[dict], cfg: dict) -> dict:
    """Combine N single-sample verdicts into one self-consistency verdict.

    Confidence is empirical: it is the agreement fraction across the parseable
    samples. Ties break toward INCLUDE (recall-first). A record is "consistent"
    — and therefore auto-decidable — only when enough samples parsed AND their
    agreement meets `review_below_agreement`. Everything else routes to review.
    """
    sc = cfg["screen"]["self_consistency"]
    n_total = len(verdicts)
    valid = [v for v in verdicts if v.get("eligible") in ("T", "F")]
    n_valid = len(valid)
    off_vocab = any(v.get("off_vocab_reason") for v in verdicts)

    if n_valid == 0:
        return {"eligible": "", "reason": "", "confidence": "", "rationale": "",
                "votes_include": 0, "votes_exclude": 0,
                "valid_samples": 0, "total_samples": n_total,
                "agreement": 0.0, "consistent": False, "parse_error": True,
                "off_vocab_reason": off_vocab, "insufficient_info": False,
                "forced_include_insufficient": False}

    votes = Counter(v["eligible"] for v in valid)
    vt, vf = votes.get("T", 0), votes.get("F", 0)
    final = "T" if vt >= vf else "F"            # tie -> include (recall-first)
    agreement = max(vt, vf) / n_valid

    if agreement >= 1.0:
        conf = "high"
    elif agreement >= 0.75:
        conf = "medium"
    else:
        conf = "low"

    reason, insufficient = "", False
    if final == "F":
        f_reasons = [v["reason"] for v in valid if v["eligible"] == "F" and v["reason"]]
        if f_reasons:
            reason = Counter(f_reasons).most_common(1)[0][0]
        insufficient = (reason == INSUFFICIENT_INFO_REASON)

    # a rationale from a sample that matches the final verdict, for the audit row
    rationale = next((v["rationale"] for v in valid
                      if v["eligible"] == final and v["rationale"]), "")

    # insufficient-information policy: optionally resolve at full text instead
    policy = cfg["screen"].get("insufficient_info_policy", "review")
    forced_include = False
    if final == "F" and insufficient and policy == "include":
        final, reason, forced_include = "T", "", True

    threshold = float(sc.get("review_below_agreement", 1.0))
    min_valid = sc.get("min_valid_samples")
    min_valid = int(min_valid) if min_valid else (n_total // 2 + 1)
    consistent = (n_valid >= min_valid) and (agreement >= threshold)

    return {
        "eligible": final, "reason": reason, "confidence": conf, "rationale": rationale,
        "votes_include": vt, "votes_exclude": vf,
        "valid_samples": n_valid, "total_samples": n_total,
        "agreement": round(agreement, 3), "consistent": consistent,
        "parse_error": any(v.get("parse_error") for v in verdicts),
        "off_vocab_reason": off_vocab,
        "insufficient_info": insufficient,
        "forced_include_insufficient": forced_include,
    }


def review_flag(verdict: dict, cfg: dict) -> str:
    """Returns a human-review reason, or '' if the record can be auto-decided."""
    if verdict.get("eligible") not in ("T", "F"):
        return "no parseable verdict across samples"
    if not verdict.get("consistent"):
        return (f"samples not consistent "
                f"({verdict['votes_include']}T / {verdict['votes_exclude']}F "
                f"of {verdict['total_samples']})")
    if verdict.get("off_vocab_reason"):
        return "model used an exclusion reason not in your list"
    # uncertainty is the dangerous direction: never silently drop "insufficient
    # information" excludes (unless policy already flipped them to include).
    policy = cfg["screen"].get("insufficient_info_policy", "review")
    if policy == "review" and verdict.get("eligible") == "F" and verdict.get("insufficient_info"):
        return "insufficient-information exclude (verify before dropping)"
    return ""


# --------------------------------------------------------------------------- #
# Batch submission (one model, sampled N times)
# --------------------------------------------------------------------------- #
def _chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def _build_requests(records, system_prompt, model, temperature, cfg):
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request

    s = cfg["screen"]
    if s["use_prompt_caching"]:
        system_block = [{"type": "text", "text": system_prompt,
                         "cache_control": {"type": "ephemeral"}}]
    else:
        system_block = system_prompt

    return [
        Request(
            custom_id=r.record_id,
            params=MessageCreateParamsNonStreaming(
                model=model,
                max_tokens=s["max_tokens"],
                temperature=temperature,
                system=system_block,
                messages=[{"role": "user", "content": build_user_content(r)}],
            ),
        )
        for r in records
    ]


def _with_retry(fn, what, attempts=6, base_delay=5.0, max_delay=120.0):
    """Call fn(), retrying transient API failures with exponential backoff.

    Only retries server/connection/rate-limit errors (e.g. the 502s Cloudflare
    occasionally returns). Client errors (bad request, auth) are not transient
    and propagate immediately.
    """
    import anthropic
    transient = (anthropic.InternalServerError,    # 5xx, incl. 502 / 529 overloaded
                 anthropic.APIConnectionError,      # network drop / timeout
                 anthropic.RateLimitError)          # 429
    for i in range(1, attempts + 1):
        try:
            return fn()
        except transient as e:
            if i == attempts:
                print(f"  !! {what}: {type(e).__name__} — giving up after {attempts} attempts")
                raise
            delay = min(base_delay * 2 ** (i - 1), max_delay)
            print(f"  ! {what}: {type(e).__name__} (attempt {i}/{attempts}); "
                  f"retrying in {int(delay)}s")
            time.sleep(delay)


def _batch_fingerprint(model, temps, system_prompt, record_ids) -> str:
    """Stable id for a screening job. Changing the model, temperatures, criteria
    prompt, or record set invalidates a saved checkpoint so it is never reused
    for a different run."""
    h = hashlib.sha256()
    h.update(model.encode("utf-8"))
    h.update(repr([float(t) for t in temps]).encode("utf-8"))
    h.update(system_prompt.encode("utf-8"))
    h.update("\n".join(record_ids).encode("utf-8"))
    return h.hexdigest()


def _save_checkpoint(path, fingerprint, submitted):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump({"fingerprint": fingerprint, "submitted": submitted}, fh)
    os.replace(tmp, path)       # atomic; a crash mid-write can't corrupt it


def _load_checkpoint(path, fingerprint):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return None
    if data.get("fingerprint") != fingerprint:
        print("  ! found a batch checkpoint, but model/temps/criteria/records "
              "changed since — ignoring it and submitting fresh")
        return None
    return [tuple(x) for x in data.get("submitted", [])]


class _PlainBar:
    """Minimal stand-in used when tqdm isn't installed: prints at ~10% steps."""
    def __init__(self, total, desc):
        self.total, self.desc, self.n, self._shown = total, desc, 0, -1
    def update(self, inc):
        self.n += inc
        pct = int(100 * self.n / self.total) if self.total else 100
        if pct >= self._shown + 10:
            self._shown = pct - (pct % 10)
            print(f"  {self.desc}: {self.n}/{self.total} ({pct}%)")
    def close(self):
        print(f"  {self.desc}: done ({self.n}/{self.total})")


def _progress(total, desc):
    """A tqdm progress bar over `total` requests, or a plain fallback."""
    try:
        from tqdm import tqdm
        return tqdm(total=total, desc=f"  {desc}", unit="req")
    except ImportError:
        return _PlainBar(total, desc)


def screen_records(records, system_prompt, cfg, model, temps):
    """Screen every record `len(temps)` times on one model (self-consistency).

    Returns {record_id: [raw_text per sample]} aligned with `temps`. Submitted
    batch ids are checkpointed to work/04_batches.json so that an interrupted
    run RESUMES (reusing the batches you already paid for) instead of
    resubmitting. Delete that file to force a fresh submission. All transient
    API errors are retried with backoff.
    """
    import anthropic

    client = anthropic.Anthropic(max_retries=5)   # reads ANTHROPIC_API_KEY
    s = cfg["screen"]
    ckpt = os.path.join(cfg["paths"]["work_dir"], "04_batches.json")
    fingerprint = _batch_fingerprint(model, temps, system_prompt,
                                     [r.record_id for r in records])

    submitted = _load_checkpoint(ckpt, fingerprint)   # list of (sample_index, batch_id)
    if submitted:
        print(f"  resuming: {len(submitted)} batch(es) already submitted "
              f"(from {ckpt})")
    else:
        submitted = []
        for si, temp in enumerate(temps):
            for ci, chunk in enumerate(_chunks(records, s["batch_chunk_size"]), 1):
                batch = _with_retry(
                    lambda chunk=chunk, temp=temp: client.messages.batches.create(
                        requests=_build_requests(chunk, system_prompt, model, temp, cfg)),
                    what=f"submit sample {si + 1}/{len(temps)} chunk {ci}")
                submitted.append((si, batch.id))
                _save_checkpoint(ckpt, fingerprint, submitted)   # persist after each
                print(f"  submitted sample {si + 1}/{len(temps)} (temp={temp}) "
                      f"chunk {ci}: {len(chunk)} requests (id={batch.id})")

    out = {r.record_id: [None] * len(temps) for r in records}
    total = len(records) * len(temps)

    # ---- wait for all batches, showing live request-level progress --------- #
    # Batches run in parallel server-side; poll them all each cycle and advance
    # the bar by how many individual requests have finished (succeeded/errored).
    pending = {bid for _, bid in submitted}
    done = {bid: 0 for _, bid in submitted}
    bar = _progress(total, f"screening {len(records)} recs x {len(temps)} samples")
    while pending:
        for bid in list(pending):
            batch = _with_retry(lambda bid=bid: client.messages.batches.retrieve(bid),
                                what=f"poll {bid}")
            rc = batch.request_counts
            done[bid] = rc.succeeded + rc.errored + rc.canceled + rc.expired
            if batch.processing_status == "ended":
                pending.discard(bid)
        bar.update(sum(done.values()) - bar.n)
        if pending:
            time.sleep(30)
    bar.update(total - bar.n)        # finish the bar even if some requests errored
    bar.close()

    # ---- collect results --------------------------------------------------- #
    for si, bid in submitted:
        results = _with_retry(lambda bid=bid: list(client.messages.batches.results(bid)),
                              what=f"fetch results {bid}")
        for res in results:
            if res.result.type == "succeeded":
                blocks = res.result.message.content
                text = "".join(b.text for b in blocks if getattr(b, "type", "") == "text")
            else:
                text = json.dumps({"_api_error": res.result.type})
            out[res.custom_id][si] = text

    return out
