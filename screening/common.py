"""Shared helpers used across the pipeline stages."""
from __future__ import annotations

import os
import re
import csv
import json
import shutil
import subprocess
import yaml
from datetime import datetime
from dataclasses import dataclass, field, asdict, fields as dataclass_fields
from typing import Optional


# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
def load_config(path: str = "config.yaml") -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


# --------------------------------------------------------------------------- #
# Multi-search layout
# --------------------------------------------------------------------------- #
# Each literature search is a self-contained run under
# <searches_dir>/<search>/ with its own inputs/, work/, outputs/,
# prior_screened/, and archives/. This resolver repoints cfg["paths"] at the
# active search so every downstream stage (which reads paths.inputs_dir etc.)
# works unchanged. Selecting a later search + dropping an earlier search's
# results into its prior_screened/ folder is how overlap across searches is
# skipped (see screening.prior).
def list_searches(cfg: dict) -> list[str]:
    base = (cfg.get("paths") or {}).get("searches_dir")
    if not base or not os.path.isdir(base):
        return []
    return sorted(d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d)))


def load_search_config(root_config_path: str = "config.yaml",
                       search: Optional[str] = None, create: bool = False,
                       template_path: str = "config.template.yaml"):
    """Resolve and load the config for the active search.

    The ROOT config only selects a search (paths.searches_dir + active_search);
    each search's COMPLETE config lives at <searches_dir>/<name>/config.yaml.
    Returns (cfg, search_name). With create=True a missing search config is
    seeded from `template_path`. Falls back to legacy single-file behaviour when
    the root config has no searches_dir (returns the root config unchanged, with
    search_name None).
    """
    root = load_config(root_config_path)
    rp = root.get("paths") or {}
    base = rp.get("searches_dir")
    if not base:
        return root, None                       # legacy flat single-config layout

    name = search or rp.get("active_search")
    if not name:
        raise SystemExit(
            f"No search selected. Set paths.active_search in {root_config_path} "
            f"or pass --search NAME.  Available: {list_searches(root) or '(none yet)'}")

    search_root = os.path.join(base, name)
    cfg_path = os.path.join(search_root, "config.yaml")
    if not os.path.isfile(cfg_path):
        if create:
            os.makedirs(search_root, exist_ok=True)
            if os.path.isfile(template_path):
                shutil.copy2(template_path, cfg_path)
                print(f"  + seeded {cfg_path} from {template_path} — edit it for this search")
            else:                                # minimal fallback if no template
                with open(cfg_path, "w", encoding="utf-8") as fh:
                    yaml.safe_dump({"paths": {"criteria_file": "criteria.md"}}, fh)
                print(f"  + created {cfg_path} (no {template_path} found) — fill it in")
        else:
            raise SystemExit(
                f"Search {name!r} has no config at {cfg_path}.\n"
                f"Scaffold it first with:  python run.py prepare --search {name}\n"
                f"Available: {list_searches(root) or '(none yet)'}")

    cfg = load_config(cfg_path)
    paths = cfg.setdefault("paths", {})
    paths["searches_dir"] = base                # carry the selector into the search cfg
    paths["active_search"] = name
    return cfg, name


def apply_search_layout(cfg: dict, search: Optional[str] = None,
                        create: bool = False) -> dict:
    """Repoint cfg["paths"] at the active search's self-contained folder.

    `search` (from --search) overrides paths.active_search. No-op when
    paths.searches_dir is unset (legacy flat layout). With create=True the
    search's inputs/ and prior_screened/ folders are made if missing.
    """
    paths = cfg.setdefault("paths", {})
    base = paths.get("searches_dir")
    if not base:
        return cfg                       # legacy flat layout — leave paths as-is

    name = search or paths.get("active_search")
    if not name:
        raise SystemExit(
            "No search selected. Set paths.active_search in config.yaml or pass "
            f"--search NAME.  Available: {list_searches(cfg) or '(none yet)'}")

    root = os.path.join(base, name)
    if not os.path.isdir(root) and not create:
        raise SystemExit(
            f"Search {name!r} not found under {base}/.  "
            f"Available: {list_searches(cfg) or '(none yet)'}.\n"
            f"Create it with:  mkdir -p {os.path.join(root, 'inputs')}   "
            f"(then drop your exports there)")

    paths["search"] = name
    paths["search_root"] = root
    paths["inputs_dir"] = os.path.join(root, "inputs")
    paths["work_dir"] = os.path.join(root, "work")
    paths["outputs_dir"] = os.path.join(root, "outputs")
    paths["prior_screened_dir"] = os.path.join(root, "prior_screened")
    paths["validate_dir"] = os.path.join(root, "validate")

    # default the prior-screened glob to THIS search's own folder (drop earlier
    # searches' result CSVs there); an explicit files: list in config wins.
    pc = cfg.setdefault("prior_screened", {})
    if not pc.get("files"):
        pc["files"] = [os.path.join(root, "prior_screened", "*.csv")]

    # keep each search's record-keeping archives separate too
    arch = cfg.setdefault("archive", {})
    if not arch.get("dir") or arch.get("dir") == "data/archives":
        arch["dir"] = os.path.join(root, "archives")

    # the abstract cache belongs to this search's work/ folder
    en = cfg.setdefault("enrich", {})
    if not en.get("cache_file") or en.get("cache_file") == "data/work/abstract_cache.json":
        en["cache_file"] = os.path.join(paths["work_dir"], "abstract_cache.json")

    if create:
        for sub in ("inputs", "prior_screened"):
            os.makedirs(os.path.join(root, sub), exist_ok=True)
    return cfg


def set_active_search(root_config_path: str, name: str) -> bool:
    """Point the ROOT config's paths.active_search at `name`, in place.

    Rewrites only the active_search value via regex so the root config's
    comments/formatting survive (yaml.safe_dump would strip them). Returns True
    if an active_search line was found and updated.
    """
    try:
        with open(root_config_path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return False
    pat = re.compile(
        r'(?m)^(?P<pre>\s*active_search\s*:\s*)(?P<val>[^\n#]*?)'
        r'(?P<sp>[ \t]*)(?P<cmt>#.*)?$')
    new_text, n = pat.subn(
        lambda m: f'{m.group("pre")}"{name}"{m.group("sp")}{m.group("cmt") or ""}',
        text, count=1)
    if n == 0:
        return False
    with open(root_config_path, "w", encoding="utf-8") as fh:
        fh.write(new_text)
    return True


# --------------------------------------------------------------------------- #
# Pipeline counts ledger
# --------------------------------------------------------------------------- #
# Each stage records its tallies here so the final PRISMA summary can report a
# complete flow (identified -> deduplicated -> screened), not just the screen box.
def _counts_path(cfg: dict) -> str:
    return os.path.join(cfg["paths"]["work_dir"], "pipeline_counts.json")


def update_counts(cfg: dict, **kv) -> dict:
    """Merge key/values into the counts ledger and persist it."""
    path = _counts_path(cfg)
    data = read_counts(cfg)
    data.update(kv)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    return data


def read_counts(cfg: dict) -> dict:
    path = _counts_path(cfg)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


# --------------------------------------------------------------------------- #
# Per-run archive (record keeping / reproducibility)
# --------------------------------------------------------------------------- #
def _git_commit() -> Optional[str]:
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"],
                           capture_output=True, text=True, timeout=5)
        return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else None
    except (OSError, subprocess.SubprocessError):
        return None


def archive_run(cfg: dict, config_path: str = "config.yaml", meta: dict = None) -> str:
    """Snapshot a complete run into one timestamped folder for record keeping.

    Copies the raw inputs, all intermediate work files, and all outputs, plus
    the exact criteria.md and config.yaml used, and writes a manifest.json with
    run metadata (timestamp, git commit, resolved settings, counts). The folder
    is fully self-contained so a run can be reproduced or audited later.
    """
    paths = cfg["paths"]
    archive_root = (cfg.get("archive") or {}).get("dir", "data/archives")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(archive_root, f"run_{stamp}")
    n = 1
    while os.path.exists(run_dir):                 # avoid same-second collision
        run_dir = os.path.join(archive_root, f"run_{stamp}_{n}")
        n += 1
    os.makedirs(run_dir, exist_ok=True)

    # the three data directories, each preserved as a subfolder
    for key, name in (("inputs_dir", "inputs"), ("work_dir", "work"),
                      ("outputs_dir", "outputs")):
        src = paths.get(key)
        if src and os.path.isdir(src):
            shutil.copytree(src, os.path.join(run_dir, name), dirs_exist_ok=True)

    # the protocol and settings exactly as used for this run
    for f in (paths.get("criteria_file"), config_path):
        if f and os.path.isfile(f):
            shutil.copy2(f, os.path.join(run_dir, os.path.basename(f)))

    manifest = {
        "run_id": os.path.basename(run_dir),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "git_commit": _git_commit(),
        "counts": read_counts(cfg),
    }
    if meta:
        manifest.update(meta)
    with open(os.path.join(run_dir, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    return run_dir


# --------------------------------------------------------------------------- #
# Unified record schema
# --------------------------------------------------------------------------- #
@dataclass
class Record:
    record_id: str = ""           # stable id assigned at ingest (used as batch custom_id)
    source_db: str = ""           # originating database (from filename), comma-joined if merged
    doi: Optional[str] = None     # normalized DOI (lowercase, no prefix) or None
    title: str = ""
    authors: str = ""             # raw author string (kept as-is for reporting)
    first_author: str = ""        # normalized surname, for dedup
    year: Optional[int] = None
    abstract: Optional[str] = None
    abstract_source: str = ""     # "export", "openalex", "crossref", or "" if none
    raw_id: str = ""              # original key/id from the export

    def to_row(self) -> dict:
        return asdict(self)


def record_fieldnames() -> list[str]:
    return [f.name for f in dataclass_fields(Record)]


# --------------------------------------------------------------------------- #
# Normalization
# --------------------------------------------------------------------------- #
_DOI_PREFIX = re.compile(r"^\s*(https?://(dx\.)?doi\.org/|doi:\s*)", re.IGNORECASE)


def normalize_doi(doi) -> Optional[str]:
    if not doi:
        return None
    doi = str(doi).strip()
    doi = _DOI_PREFIX.sub("", doi).strip().lower()
    # strip trailing punctuation / urls that sometimes ride along
    doi = doi.split()[0] if doi else doi
    return doi or None


def normalize_title(title) -> str:
    if not title:
        return ""
    t = str(title).lower()
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return " ".join(t.split())


def first_author_surname(authors) -> str:
    """Best-effort surname of the first author for blocking/dedup."""
    if not authors:
        return ""
    if isinstance(authors, (list, tuple)):
        authors = authors[0] if authors else ""
    s = str(authors).strip()
    # split off the first author from common separators
    s = re.split(r"\s*;\s*|\s+and\s+", s)[0]
    if "," in s:                      # "Surname, Given"
        surname = s.split(",")[0]
    else:                             # "Given Surname"
        surname = s.split()[-1] if s.split() else s
    return re.sub(r"[^a-z]", "", surname.lower())


def clean_year(value) -> Optional[int]:
    if value is None:
        return None
    m = re.search(r"(19|20)\d{2}", str(value))
    return int(m.group(0)) if m else None


def clean_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        value = "; ".join(str(v) for v in value)
    return re.sub(r"\s+", " ", str(value)).strip()


# --------------------------------------------------------------------------- #
# CSV IO for records
# --------------------------------------------------------------------------- #
def read_csv_dicts(path: str) -> list[dict]:
    """Read a CSV as UTF-8, falling back to Excel's CSV (Macintosh) encoding."""
    try:
        with open(path, "r", newline="", encoding="utf-8-sig") as fh:
            return list(csv.DictReader(fh))
    except UnicodeDecodeError:
        with open(path, "r", newline="", encoding="mac_roman") as fh:
            rows = list(csv.DictReader(fh))
        print(f"  ! read CSV (Macintosh) encoding: {path}")
        return rows


def write_records_csv(records: list[Record], path: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=record_fieldnames())
        writer.writeheader()
        for r in records:
            writer.writerow(r.to_row())


def read_records_csv(path: str) -> list[Record]:
    out = []
    for row in read_csv_dicts(path):
        rec = Record(**{k: row.get(k, "") for k in record_fieldnames()})
        rec.year = int(rec.year) if str(rec.year).strip().isdigit() else None
        rec.doi = rec.doi or None
        rec.abstract = rec.abstract or None
        out.append(rec)
    return out
