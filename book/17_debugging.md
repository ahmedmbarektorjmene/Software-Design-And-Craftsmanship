# 17. Debugging

Debugging is where a programmer's model of the system meets evidence. The model is always incomplete; the evidence is always surprising. The craft lies in closing the gap systematically rather than by guessing.

This chapter treats debugging as an applied science: form hypotheses, reproduce reliably, narrow the search, understand the cause, fix it once, and prevent the class of defect from returning.

## Learning objectives

- Apply the scientific method to defect investigation.
- Reproduce a defect reliably before changing code.
- Use bisection and differential diagnosis to locate causes.
- Distinguish the defect's symptom, its cause, and the conditions that exposed it.
- Fix defects at the right level rather than at the point of failure.
- Turn every defect into a regression test.
- Debug production systems with the tools available there.

## 17.1 The scientific method, applied

A debug session is an experiment:

1. **Observe.** Record exactly what happened: inputs, outputs, logs, timestamps, environment.
2. **Hypothesize.** Propose a specific, falsifiable cause: "the cache returns a stale entry because the invalidation key omits the tenant."
3. **Predict.** State what you would see if the hypothesis were true: "adding the tenant to the key should make the second request fetch fresh data."
4. **Test.** Run the smallest experiment that distinguishes the hypothesis from its alternatives.
5. **Conclude.** Accept, reject, or refine. Record what you learned.

The discipline matters because the alternative—changing things and seeing what happens—destroys evidence and multiplies variables. Every uncontrolled change is a new suspect.

A useful rule: **one variable at a time**. If you change the config, the data, and the code before re-running, a different result tells you nothing about which change mattered.

## 17.2 Reproduce

A defect you cannot reproduce is a defect you cannot fix with confidence. Reproducibility requires capturing:

- **the exact input**, including the full request body, file contents, or sequence of user actions;
- **the environment**: version, platform, locale, time zone, feature flags, data state;
- **the timing**: was it the first request, a retry, a concurrent burst?
- **the observation**: the error message, stack trace, log lines, and the state at failure.

```typescript
// A reproduction harness: fixed inputs, fixed clock, explicit state.
interface ReproCase {
  readonly name: string;
  readonly seed: number;
  readonly clock: string;
  readonly input: unknown;
}

function runRepro(testCase: ReproCase, run: (input: unknown, now: Date) => unknown): unknown {
  const now = new Date(testCase.clock);
  return run(testCase.input, now);
}
```

If the defect only appears in production, build a reproduction from production evidence: the request ID in logs, the serialized payload, the database snapshot. "Cannot reproduce" usually means "have not captured enough state," not "the defect is metaphysical."

**Heisenbugs**—defects that disappear when observed—are usually timing, concurrency, or uninitialized-memory artifacts. Their disappearance is information: the observation mechanism changed timing. Reproduce them by increasing load, adding delays, or running under a race detector, not by staring harder.

![Reproducing a defect several ways to pin down its cause.](assets/reproducing-errors.png)

## 17.3 Locate

Once the defect reproduces, narrow the space of possible causes.

### Bisection

**Bisection** is the most reliable locating technique: repeatedly halve the search space.

- **In history:** find the last known-good commit and the first known-bad commit, then test the midpoint. `git bisect` automates this. It works because version history is a total order.
- **In data:** if a large input triggers the bug, cut it in half and test each half. Repeat until the minimal failing input remains.
- **In code:** if a pipeline of stages fails, check the intermediate values between stages. The first stage whose output is wrong contains the defect.
- **In configuration:** disable half the flags; if the bug persists, it is in the other half.

Bisection is powerful because it is logarithmic: a thousand suspects need about ten tests, not a thousand.

### Differential diagnosis

Compare a working case with a failing one and list the differences. Change one difference at a time to see whether it flips the outcome. The minimal difference that flips is the cause, or adjacent to it.

```typescript
// Differential: same code path, two tenants. One works, one does not.
const working = { tenant: "acme", userId: "u_1", role: "admin" };
const failing = { tenant: "globex", userId: "u_1", role: "admin" };
```

If only `tenant` differs, examine every place tenant affects behavior: keys, filters, feature flags, caches. The defect is usually where a value that *should* differ is treated as constant, or vice versa.

### Reading the stack

A stack trace tells you the *path*, not necessarily the *cause*. The frame where the exception was thrown is often a victim: a null value arrived from three frames up. Read upward until you find the first frame where the state was already wrong.

The same applies to error messages. `Cannot read properties of undefined (reading 'id')` names the symptom. The cause is "the lookup returned undefined and the caller did not handle it."

## 17.4 Understand

Locating the failure is not the same as understanding the defect. Before fixing, answer:

- **What was the programmer's model?** What did the author believe was true?
- **What was actually true?** Which assumption was violated?
- **Why was the assumption reasonable?** Was it documented, implied by a type, or merely conventional?
- **What conditions exposed the gap?** Empty input, concurrency, a locale, a slow network, a specific data shape.
- **Could the same gap exist elsewhere?** If the assumption is common in the codebase, the defect is a class, not an instance.

The last question is the most valuable and the most often skipped. A null check added at one call site fixes one crash; a change to the type that made null possible fixes the class.

## 17.5 Fix

A fix should address the cause, at the right level.

**Levels of fix:**

- **Symptom:** catch the exception and return a default. Hides the defect; the corruption spreads.
- **Local cause:** add the missing null check. Correct if null is a legitimate value that this caller must handle.
- **Contract:** change the function to never return null, or to make the possibility explicit in its type. Correct if null was never supposed to be a valid result.
- **Design:** remove the shared mutable state, the temporal coupling, or the duplication that made the defect possible. Correct when the same defect class keeps recurring.

```typescript
interface OrderLine { readonly amountCents: number }
interface Order { readonly id: string; readonly lines?: readonly OrderLine[] }

// Symptom-level: the crash stops, the wrong data remains.
function totalFor(order: Order): number {
  try {
    return (order.lines ?? []).reduce((sum, line) => sum + line.amountCents, 0);
  } catch {
    return 0;
  }
}
```

```typescript
interface OrderLine { readonly amountCents: number }

// Contract-level: the type says lines always exist; the parser guarantees it.
interface Order {
  readonly id: string;
  readonly lines: readonly OrderLine[];
}

function totalFor(order: Order): number {
  return order.lines.reduce((sum, line) => sum + line.amountCents, 0);
}
```

The second version is shorter because it fixed the invariant at the boundary where orders are constructed. The defensive `try` was compensating for a broken contract elsewhere.

**Fix one thing at a time.** A fix that also refactors three functions cannot be verified by the regression test alone. Make the minimal fix, confirm it, then improve the structure in a separate step.

## 17.6 Prevent

Every defect is a gift: it reveals a gap in the tests, the types, or the process. Close the gap.

1. **Write a regression test that fails before the fix and passes after.** If you cannot make it fail first, you have not captured the defect.
2. **Ask why the test suite missed it.** No test for that path? A test that asserted the wrong thing? A fixture that never produced the condition?
3. **Ask why the type system missed it.** Could a narrower type, a branded ID, or a discriminated union have prevented it?
4. **Ask why the review missed it.** Was the assumption invisible in the diff? Would a comment or a smaller function have exposed it?
5. **Search for siblings.** If the defect was "forgot to await," search for other unawaited calls. If it was "wrong time zone," audit every date conversion.

```typescript
interface OrderLine { readonly amountCents: number }
interface Order { readonly id: string; readonly lines: readonly OrderLine[] }

function totalFor(order: Order): number {
  return order.lines.reduce((sum, line) => sum + line.amountCents, 0);
}

// The regression test names the defect and the condition that exposed it.
function testTotalHandlesOrderWithoutLines(): void {
  const order: Order = { id: "o_1", lines: [] };
  const total = totalFor(order);
  if (total !== 0) throw new Error(`expected 0, got ${total}`);
}
```

A defect that recurs after being "fixed" was fixed at the symptom level. A defect that never recurs was understood.

## 17.7 Tools

Tools extend observation. The most useful categories:

- **Debuggers.** Breakpoints, conditional breakpoints, watch expressions, and stepping. Best for local, deterministic defects where you can inspect state.
- **Logging.** Structured logs with correlation IDs. Best for production, concurrency, and anything that cannot be paused.
- **Tracing.** Distributed traces show causality across services. Best for latency and integration defects.
- **Assertions.** Fail fast at the point where an invariant breaks, with the state that broke it.
- **Diffing and bisection.** Version control tools that find the change that introduced the defect.
- **Static analysis and type checkers.** Catch whole classes before execution.
- **Replay and record.** Captured inputs replayed against the current code.

A practical note: **logging is a design decision**. Logs that say `"error"` are useless; logs that say `"failed to reserve stock for order o_123 at warehouse w_9: 3 of 5 units available"` are a debugging session in one line. Design log messages for the person who will read them at 3 a.m.

## 17.8 Debugging production

Production debugging has constraints that local debugging does not: you cannot pause the process, you may not have the data, and the cost of a wrong change is high.

Principles:

- **Observe before acting.** Read the logs, metrics, and traces before changing anything. A restart destroys evidence.
- **Stabilize first, diagnose second—sometimes.** If users are affected, mitigate (roll back, disable the feature, shed load), then diagnose with the preserved evidence.
- **Prefer reversible mitigations.** A feature flag or a rollback is safer than a hot patch.
- **Keep the evidence.** Snapshot the failing instance, export the logs, capture the payload.
- **Write the timeline.** What happened, in what order, with what observations. The timeline often reveals the cause before the code does.
- **Follow up with a blameless review.** The goal is a systemic fix: a test, a guardrail, an alert, a design change.

```typescript
// Structured log entry: enough context to reconstruct the failure.
interface LogEntry {
  readonly level: "info" | "warn" | "error";
  readonly event: string;
  readonly correlationId: string;
  readonly orderId?: string;
  readonly detail: Record<string, unknown>;
}

function logFailure(entry: LogEntry): void {
  // In a real system this writes JSON to stdout for the log pipeline.
  console.error(JSON.stringify(entry));
}
```

The correlation ID is what makes production logs usable: it ties a user's request to every service, query, and retry it touched.

## 17.9 The psychology of debugging

Debugging is emotionally expensive. The defect is often in code you wrote, the pressure is real, and the temptation to change things randomly is strong. A few habits help:

- **Separate the ego from the code.** The defect is a fact about the system, not a verdict on the author.
- **Take a break when stuck.** Fresh attention finds what fatigue hides.
- **Explain the problem aloud.** Describing it to a colleague—or a rubber duck—forces the model into words, and the gap often appears.
- **Question the assumption you are most sure of.** The defect usually lives there.
- **Keep a log of what you tried.** It prevents loops and makes the eventual fix explainable.

The best debuggers are not the fastest typists; they are the most disciplined about evidence.

## Summary

- Treat debugging as experiment: observe, hypothesize, predict, test, conclude—one variable at a time.
- Reproduce reliably by capturing input, environment, timing, and observation.
- Locate with bisection and differential diagnosis; read stack traces for the path, not the cause.
- Understand the violated assumption and ask whether the same gap exists elsewhere.
- Fix at the right level: symptom, local cause, contract, or design.
- Prevent recurrence with a regression test and by closing the gap in tests, types, or review.
- Design logs and traces for the person debugging at 3 a.m.
- In production, preserve evidence, prefer reversible mitigations, and follow up with a systemic fix.

## Exercises

1. **Reproduce a defect.** Take a recently fixed bug. Write down the minimal input, environment, and observation that reproduce it. Would a colleague be able to reproduce it from your notes alone?
2. **Bisect a history.** Find a regression in a repository's history and locate the introducing commit with `git bisect`. How many steps did it take compared with a linear scan?
3. **Minimize an input.** Take a large failing input and halve it repeatedly until it is minimal. What did the minimal case reveal that the original hid?
4. **Levels of fix.** Find a defensive `try/catch` or null check. Decide whether it is a symptom fix, a local fix, or a contract fix. What would the higher-level fix look like?
5. **Regression test.** For a fixed defect, write a test that fails on the old code and passes on the new. Verify that it actually fails when you revert the fix.
6. **Sibling search.** Take a defect class (unawaited promise, missing time zone, off-by-one). Search the codebase for other instances. How many did you find?
7. **Log design.** Rewrite three log messages to include the operation, the relevant identifiers, and the observed state. Would they be enough to diagnose a failure without a debugger?
8. **Production timeline.** Reconstruct a production incident as a timeline of observations and actions. Where was evidence destroyed? What would you preserve next time?
