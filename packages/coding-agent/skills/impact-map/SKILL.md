---
name: impact-map
description: Pre-change blast-radius analysis and adversarial review BEFORE editing code. Use when making non-trivial changes (multi-file, behavior-changing, cross-surface). Produces an Impact Map, grep-verifies dependency edges, runs adversarial voices, and gates on a composite decision. Prevents the wrong code from being written.
---

# Impact Map

Required for every non-trivial change. For trivial single-file edits (typo,
comment, copy tweak) collapse steps 1-3 into a one-line note.

A change that cannot articulate its blast radius is not ready to be made.

## 1. Understand

Read the code paths involved. Identify the real requirement, not the stated
one. Use grep and file reads to trace the actual call graph — do not guess.

## 2. Impact Map (hard gate)

Produce a blast-radius analysis BEFORE editing. Fill the template in
[references/impact-map-template.md](references/impact-map-template.md). It must
answer:

- **What changes** — files/functions/endpoints touched.
- **Who depends on it** — every caller/consumer. Search the repo; list actual
  dependency edges with file:line citations, not a count. Invented dependencies
  are an AI failure mode — grep-verify every edge.
- **Blast radius** — frontend, backend, database schema, deployed services,
  hosting config, secrets. Cross-surface changes are high-risk by default.
- **Data implications** — reads/writes/deletes user data? Migration needed?
  Read + delete path exists for any new write path?
- **Failure modes** — what breaks if half-deployed? User-visible degradation
  must be signaled, never silent.
- **Rollback** — exact steps to revert, including deploy/secret/data reversal.
- **Tests** — the failing test(s) that will prove the change.

Save the map to a file in the project (e.g. `.devin/impact-maps/<slug>.md` or
`.impact-maps/<slug>.md`).

## 3. Adversarial review

Before executing, attack the map with three adversarial voices:

- **lambda (Local)** — every dependency edge in the map is real and evidenced.
  Grep each claimed caller/consumer. Discard edges that don't exist. List which
  are VERIFIED vs UNVERIFIED.
- **mu (Guide)** — is this the right seam? Propose at least one smaller or
  safer change that achieves the same intent, or justify why none exists.
  COHERENT or CONCERNS.
- **nu (Mirror)** — invariant audit: silent degradation (fallback signaled?),
  new write path without read/delete path, ID-mapping parity, data/auth
  boundary violations. PASS, WARNINGS, or CONCERNS.

Compose as **omega**: GO, REVISE MAP, or NO-GO with a confidence percentage.

If omega is REVISE MAP: update the map with findings and re-run. Do not proceed
on a map known to be wrong.

Report format:

```
IMPACT REVIEW: <change>
|- Phase 0: N edges verified, M missed edges found, K non-lexical couplings
|- lambda: [VERIFIED / UNVERIFIED]
|- mu: [COHERENT / CONCERNS]
|- nu: [PASS / WARNINGS / CONCERNS]
|- omega: [GO / REVISE MAP / NO-GO] - Confidence: XX%
    Verify first: 1) ... 2) ... 3) ...
```

## 4. Plan

State the approach, the tests to write first, and the rollback path.

## 5. Approve

For anything touching auth, payments, data deletion, or memory/retrieval, get
explicit human approval of the Impact Map + Plan before executing.

## 6. Execute (TDD)

- Write a failing test that encodes the desired behavior, watch it fail, make
  it pass, then refactor. Bug fixes start with a failing repro test.
- Characterization tests before refactors: pin current behavior with tests so
  the refactor cannot silently change it.
- Small steps: many small green commits over one large risky one.
- Refactor only on green — never refactor and change behavior in the same step.

## 7. Verify

Run the project's verification bar (typecheck, build, lint, tests). For
cross-surface changes, confirm hosting rewrites still route correctly.

## 8. Ship

Commit with a clear "why", push, and capture the decision. Then close the loop:
fill the Impact Map retrospective (section 9 of the template) with
predicted-vs-actual blast radius, and promote recurring misses to project
gotchas or persistent memory.

## Non-lexical coupling sweep

The coupling grep cannot see is what actually breaks. Check explicitly:

- Database string collection paths and all callers
- ID mapping touchpoints (UUID vs int keys, stable_key conversions)
- Hosting rewrite rules (stale deploy silently serves wrong content)
- Deployed-vs-local drift: does the change need a deploy to be true? What
  happens half-deployed?
- API endpoints consumed by frontend that aren't in the map

## When to skip

- Trivial single-file edits (typo, comment, copy tweak)
- CSS-only changes with no logic impact
- Hotfixes where the blast radius is obviously contained (still fill a
  one-line note)
