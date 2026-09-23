<!--
============================================================================
SCREENING CRITERIA  —  edit this file freely to change your review's logic.
============================================================================
Only the DECISION RULES live here. The pipeline adds the output format
(structured JSON) automatically, so do NOT specify an output format below —
just describe what makes a paper eligible or not, and list the allowed
exclusion reasons under the "ALLOWED EXCLUSION REASONS" heading at the end.

The text ABOVE the "ALLOWED EXCLUSION REASONS" line is sent to the model
verbatim as the screening instructions. The list BELOW that line is parsed by
the pipeline and used to (a) tell the model which reasons it may use and
(b) flag any answer that uses an off-list reason for human review.
============================================================================
-->

You are screening papers for a PRISMA scoping review on how an individual's
TRAIT-LIKE COGNITIVE ABILITIES — measured with standalone cognitive tasks —
predict "RE-ENTERING THE LOOP" performance in human-AI interaction. The DOMAIN
is not restricted (e.g., automated/assisted driving, aviation and UAV
supervision, process or robotics control, human-autonomy teaming, AI-assisted
knowledge work). Apply the criteria strictly.

A paper is ELIGIBLE only if ALL of the following are true:

1. OUT-OF-THE-LOOP AUTOMATION. The human offloads part of a task to an AI or
   automated agent that operates it on their behalf, leaving the human genuinely
   out of the loop — free to disengage attention (passively monitoring at most)
   rather than sustaining continuous attention or input.

2. A RE-ENTERING-THE-LOOP EVENT. At least one point where the human must
   re-engage with the agent's work by either:
     (a) RESUMING CONTROL — taking back manual control of the process the agent
         was operating (take-over, handover/handoff, task resumption);
     (b) INTERVENING ON FAILURE — correcting, overriding, or taking over when the
         agent errs or is about to fail;
     (c) EVALUATING OFFLOADED OUTPUT — vetting output the agent produced for a
         delegated job (e.g., an LLM's draft, code, or analysis) and deciding to
         accept, reject, or revise it.
   The trigger may be system-prompted (alarm, take-over request) or self-initiated.

3. OBJECTIVELY MEASURED RE-ENTRY PERFORMANCE. In an interactive task with a
   functioning agent or live environment, the study objectively measures how well
   the human re-enters the loop — e.g., take-over reaction time or control
   quality, failure-detection accuracy/latency, situation-awareness or
   hazard-detection accuracy at re-entry (e.g., a SAGAT probe), appropriate
   reliance/override accuracy, or quality of the vetted/revised output.

4. A STANDALONE COGNITIVE-ABILITY TASK. It administers at least one standalone
   test of a trait-like ability — given separately from the interaction (before
   or after, not as a simultaneous secondary task) — e.g., working memory,
   executive function, processing speed, selective/divided/sustained attention,
   multitasking, hazard perception, or useful field of view — and relates that
   score to re-entry performance.

Plus the basics: the study has human participants.

EXCLUDE a paper if ANY of the following are true:
- No human participants.
- No standalone cognitive-ability task. The study does not administer a separate
  cognitive/psychometric test of a trait-like ability that it then relates to
  re-entry performance. This covers studies whose only human-level measures are:
  (a) task/engagement performance alone; (b) age, demographic characteristics,
  or self-reported traits; or (c) in-situ STATE indices recorded during the
  primary task — eye movements/gaze, EEG, fNIRS, pupillometry, heart rate /
  heart-rate variability, EMG/neuromuscular signals, galvanic skin response, or
  reaction time within the task (these index momentary state, not trait
  ability). A study that records such state measures is still eligible IF it
  ALSO administers a qualifying standalone task.  -> reason: "No standalone cognitive task"
- Not out-of-the-loop automation. The human must sustain continuous attention or
  input, or there is no automated agent to offload to — so the human never
  genuinely leaves the loop. THE TEST: does the automation relieve the human of
  sustained attention? If the human must keep watching and stay continuously
  ready, they are still in the loop (being called "monitoring" does not exempt
  it). Includes fully manual operation; adaptive cruise control or SAE Level-2
  driving; and pure decision support (the AI only gives a cue/recommendation
  within a task the human performs throughout). In driving specifically, Level 2
  is excluded while conditional/high automation (Level 3 or above, eyes-off)
  qualifies; in other domains a passive supervisory role qualifies only when
  attention is genuinely offloaded and intervention is occasional.
  -> reason: "No out-of-the-loop automation"
- No loop re-entry. There is offloading, but the human never resumes control,
  intervenes, or evaluates-and-acts-on the agent's offloaded output — e.g.,
  fully autonomous operation with no take-over or intervention role, or a
  one-shot agent output the human cannot act on.  -> reason: "No loop re-entry"
- No objective performance measure. Re-entry performance is not objectively
  measured — the study is hypothetical/vignette-based or relies only on
  self-report/questionnaires.  -> reason: "No objective performance measure"
- Manipulation-only study. The paper's main focus is an experimental
  manipulation rather than measuring an individual's cognitive ability — e.g.,
  interface/display/warning/handoff-design comparisons; agent-reliability or
  automation-condition manipulations; scenario or task-difficulty manipulations;
  environmental condition changes; time-budget / lead-time manipulation; induced
  cognitive-load manipulation (e.g., an in-task n-back used to load the
  participant); fatigue, sleep, or distraction manipulation; or any other
  experimentally manipulated condition. A study is NOT excluded here if it ALSO
  administers a standalone cognitive-ability task and relates it to re-entry
  performance: a manipulation may be present, but it cannot be the only
  human-level cognitive variable.  -> reason: "Experimental manipulation study"

PRIORITY RULE: A paper may fail more than one criterion. When several exclusion
reasons apply, cite ONLY the FIRST that applies, in the order the reasons are
listed above: No human participants -> No standalone cognitive task -> No out-of-the-loop automation -> No loop re-entry -> No objective performance measure -> Experimental
manipulation study -> Insufficient information.

STRICT RULE: If a required criterion is missing, unclear, or not explicitly
stated in the abstract, exclude with reason "Insufficient information". Do not
infer missing information. In particular, if the abstract names a cognitive
construct (e.g., "attention", "workload") but does not make clear whether it was
measured with a standalone task or only as an in-task state index, use
"Insufficient information".

<!-- The pipeline reads the list below. Keep one reason per line, starting with "- ". -->
## ALLOWED EXCLUSION REASONS
- No human participants
- No standalone cognitive task
- No out-of-the-loop automation
- No loop re-entry
- No objective performance measure
- Experimental manipulation study
- Insufficient information
