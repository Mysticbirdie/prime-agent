# Impact Map — <short change title>

> Fill sections 1-8 out BEFORE editing. A change that cannot articulate its blast
> radius is not ready to be made. Fill section 9 out AFTER shipping — the
> retrospective is what makes the next map better.

**Date**:
**Author/agent**:
**Related task / issue**:

---

## 1. What changes
- Files / functions / endpoints touched:
- Intended behavior change:

## 2. Dependency edges (who depends on this)
> Search the repo; list actual callers/consumers with file:line, not a count.
> Grep-verify every edge. Invented dependencies are an AI failure mode.
- Callers of the changed code:
- Consumers of the changed data/contract (frontend, other services, tests):

## 3. Blast radius (check all that apply)
- [ ] Frontend (React/TS)
- [ ] Backend functions / API
- [ ] Database schema / collections
- [ ] Deployed services (which: )
- [ ] Hosting config / rewrites
- [ ] Secrets / env
- [ ] Memory / retrieval substrate
- Cross-surface? (yes/no — if yes, this is high-risk, require phased rollout):

## 4. Data implications
- Reads / writes / deletes user data? (which):
- Migration required? (describe):
- ID mapping addressed (UUID vs int keys, stable_key conversions)? (yes/n-a):
- Read + delete path exists for any new write path? (yes/n-a):

## 5. Failure modes
- What breaks if this is half-deployed?
- User-visible degradation, and how it is **signaled** (never silent):

## 6. Rollback
- Exact steps to revert (code, deploy, secrets, data):

## 7. Tests (TDD)
- Failing test(s) that prove the change:
- Characterization tests pinned before refactor? (yes/n-a):
- Recall@k parity required (memory change)? (yes/no — number: ):

## 8. Verification bar
- [ ] Typecheck + build green
- [ ] Test suite green
- [ ] Recall@k parity demonstrated (if memory change)
- [ ] Hosting rewrites confirmed (if cross-surface)
- [ ] Diff self-reviewed for edge cases

## 9. Retrospective (fill AFTER shipping)
> The loop-closer. Every "fix one, break ten" incident is training data — record
> it here or it's thrown away.
- Predicted blast radius vs. actual — what broke that sections 1-5 did NOT predict?
- Root cause of each miss (non-lexical coupling, deployed drift, dynamic
  dispatch, schema path, wrong assumption):
- Feed-forward: what should future maps check that this one didn't? (Promote
  recurring misses to project gotchas or persistent memory.)
- Was the map load-bearing (did it change the plan/approach) or ceremonial?
