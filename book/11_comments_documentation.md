# 11. Comments and Documentation

Code can say *what* it does. It cannot say *why* it does it, what it promises, what it assumes, or what was tried and rejected. Those things live in comments—or they live nowhere, and are rediscovered by every person who touches the code.

Comments have a bad reputation because most comments are bad: they repeat the code, go stale, or narrate syntax. The answer is not to stop writing them. It is to write the ones that carry information only a human can provide.

## Learning objectives

- Explain what comments can express that code cannot.
- Refute the common excuses for not commenting, while taking their real concerns seriously.
- Write interface documentation that is complete, precise, and free of implementation detail.
- Write implementation comments that explain rationale, invariants, and surprises.
- Maintain comments as the code evolves.
- Navigate the debate between comments-first and self-documenting code.

## 11.1 What only a comment can say

Consider a function that computes a late fee:

```typescript
interface Invoice {
  readonly dueDate: Date;
  readonly lateFeePerDayCents: number;
  readonly principalCents: number;
}
declare function differenceInDays(later: Date, earlier: Date): number;

export function lateFeeCents(invoice: Invoice, asOf: Date): number {
  const daysLate = Math.max(0, differenceInDays(asOf, invoice.dueDate));
  return Math.min(daysLate * invoice.lateFeePerDayCents, invoice.principalCents);
}
```

The code says how. It does not say:

- whether `asOf` is inclusive;
- whether weekends count;
- why the fee is capped at the principal;
- what happens for a zero or negative principal;
- whether `invoice.dueDate` is in local time or UTC;
- whether the function is pure or reads a global rate;
- what the caller should do if the invoice is already paid.

Those facts are the interface. Without them, a caller must read the implementation, infer business rules, and hope.

```typescript
interface Invoice {
  readonly dueDate: Date;
  readonly lateFeePerDayCents: number;
  readonly principalCents: number;
}
declare function differenceInDays(later: Date, earlier: Date): number;

/**
 * Computes the late fee for an unpaid invoice as of a given date.
 *
 * The fee is `lateFeePerDayCents` for each calendar day after `dueDate`,
 * including weekends and holidays. The result is capped at the invoice
 * principal so a late fee can never exceed the amount owed.
 *
 * `dueDate` and `asOf` are interpreted in UTC. If `asOf` is on or before
 * the due date, the fee is zero. The function does not check payment
 * status; callers must not charge a fee for a paid invoice.
 *
 * @param invoice - The invoice; `principalCents` must be non-negative.
 * @param asOf - The date to evaluate, in UTC.
 * @returns The fee in cents, in the range [0, principalCents].
 */
export function lateFeeCents(invoice: Invoice, asOf: Date): number {
  const daysLate = Math.max(0, differenceInDays(asOf, invoice.dueDate));
  return Math.min(daysLate * invoice.lateFeePerDayCents, invoice.principalCents);
}
```

The comment adds information the type system cannot express: calendar semantics, the cap's rationale, the time zone, the payment-status precondition. It is not a translation of the code; it is the contract.

## 11.2 The four excuses

### "Good code is self-documenting"

Good code documents *what* and *how*. It does not document *why*, *what was rejected*, *what must remain true*, or *what the caller must not do*. A beautifully named function still cannot say "this workaround is here because the vendor's API returns 200 on failure." Self-documenting code reduces the need for comments; it does not eliminate it.

The legitimate core of the excuse: if a comment is needed to explain what the code does, the code may be too complicated. Fix the code first, then comment on what remains.

### "I don't have time"

Comments take time. So does reading code without them—repeatedly, by everyone, forever. Interface comments are especially cheap when written before the implementation, because they clarify the design while it is still malleable. A few minutes at the interface can save hours of confusion at every call site.

### "Comments go stale and become misleading"

True. A stale comment is worse than no comment because it is confidently wrong. The response is not to stop commenting; it is to treat comments as part of the code:

- keep them next to what they describe;
- update them in the same change as the code;
- avoid duplicating facts that are visible in the code;
- prefer comments about stable things (purpose, contract) over volatile things (implementation details);
- review comment diffs as seriously as code diffs.

### "All the comments I have seen are worthless"

Many are. That is an argument for better comments, not for none. The comments that are worthless usually fall into recognizable categories: restating the code, documenting history that belongs in version control, decorative banners, or auto-generated noise. Avoid those categories and the value rises quickly.

## 11.3 Interface comments

An interface comment describes everything a caller needs to use the abstraction correctly, and nothing about how it is implemented. It should cover:

- **Purpose:** what the abstraction is for.
- **Behavior:** what each operation does, including edge cases.
- **Parameters:** meaning, units, valid ranges, nullability.
- **Return value:** meaning, units, and what happens when there is no result.
- **Errors:** what can be thrown or returned, and what each means.
- **Side effects:** mutation, I/O, logging, events, global state.
- **Preconditions and postconditions:** what must be true before and after.
- **Invariants:** what remains true for the lifetime of the object.
- **Performance:** complexity, allocation, blocking behavior, if relevant.
- **Concurrency:** thread safety, reentrancy, ordering guarantees.
- **Ownership:** who closes, frees, or mutates a resource.

```typescript
/**
 * A bounded, thread-safe queue of jobs.
 *
 * Producers call `enqueue`; if the queue is full, the promise resolves
 * when space becomes available. Consumers call `dequeue`; if the queue
 * is empty, the promise resolves when a job arrives. Jobs are delivered
 * in FIFO order per producer.
 *
 * The queue owns the jobs; callers must not mutate a job after enqueueing.
 * `close` rejects pending and future operations with `QueueClosedError`.
 */
export interface JobQueue<T> {
  enqueue(job: T): Promise<void>;
  dequeue(): Promise<T>;
  close(): void;
  readonly size: number;
}
```

The comment says nothing about the array, the lock, or the condition variable. Those are implementation. It says everything a producer or consumer must know.

**Do not contaminate the interface with implementation details.** A comment like "uses a ring buffer with a mutex" may be useful to a maintainer, but it belongs in an implementation comment or a design note, not in the public contract. If callers start depending on the ring buffer, you can never replace it.

## 11.4 Implementation comments

Inside a function, comments should explain what the code cannot:

- **Why this approach?** Why a linear scan instead of a map, why a retry, why a cast.
- **What invariant holds?** "`items` is sorted by `dueDate`; binary search below relies on it."
- **What is surprising?** "The API returns 200 on failure; check the body."
- **What is a workaround?** Link to the issue, state the condition for removal.
- **What was tried and rejected?** Brief, if it prevents a future mistake.
- **What are the units and ranges** at a complex calculation.

```typescript
interface ItemResult { readonly status: "accepted" | "rejected" }
interface BatchResponse { readonly results: readonly ItemResult[] }
declare function batchSubmit(items: readonly string[]): Promise<BatchResponse>;

async function submit(items: readonly string[]): Promise<number> {
  // The vendor's batch endpoint returns 200 even when individual items fail;
  // `results[i].status` is the only reliable signal. Verified against API v3.2.
  const response = await batchSubmit(items);
  const failures = response.results.filter((result) => result.status !== "accepted");
  return failures.length;
}
```

```typescript
interface Rate { readonly effective: Date; readonly annualRate: number }

function latestRateOnOrBefore(rates: readonly Rate[], date: Date): number | undefined {
  // `rates` is sorted by effective date ascending. We scan backwards because
  // the common case is a recent date; a binary search would be faster for
  // large tables, but the table is capped at 200 entries by the loader.
  for (let i = rates.length - 1; i >= 0; i--) {
    const rate = rates[i];
    if (rate !== undefined && rate.effective <= date) return rate.annualRate;
  }
  return undefined;
}
```

Both comments record information that would otherwise be lost: an external API quirk and a deliberate performance trade-off. Neither restates the code.

**Comments that should not exist:** a comment that says `// Increment i by one` above `i++`, or `// Return the user` above `return user`, or `// Loop over the items` above a `for` loop. These add no information and train readers to ignore comments.

## 11.5 Comments first

Writing the interface comment **before** the implementation is a design technique, not a documentation chore. The comment forces you to decide:

- What is this abstraction for?
- What does each operation promise?
- What are the failure modes?
- What must the caller know?
- Is the interface small enough to describe?

If the comment is long and full of exceptions, the interface is probably too complex. If you cannot write it at all, the design is not ready. This is the same insight behind writing pseudocode before code: prose at the level of intent exposes gaps that syntax hides.

```typescript
interface Account {
  /**
   * Returns the available balance in cents, excluding pending holds.
   * Pending holds are released after 7 days; see `settleHolds`.
   */
  availableBalanceCents(accountId: string): number;
}
```

The comment is cheap to change now and expensive to change after ten call sites depend on the behavior. Write it first, challenge it, then implement.

## 11.6 Documentation beyond the code

Code comments are the most local documentation. Larger systems also need:

- **README:** what the project is, how to run it, how to test it, where to find more.
- **API reference:** generated from TSDoc or hand-written; describes the public surface.
- **Decision records:** why significant choices were made (Chapter 9).
- **Runbooks:** how to operate, monitor, and recover the system.
- **Glossary:** the domain vocabulary and its code equivalents.

The principle is the same at every scale: document what the reader cannot infer, and keep it close to the thing it describes. A README that duplicates the code's behavior will drift; a README that explains the architecture and the getting-started path stays useful.

**Build documentation in, don't bolt it on.** If a process requires documentation, make producing it part of the process: generate API docs from types, keep decision records in the repository, require a runbook for every service. Documentation that lives in a separate tool with a separate owner will be stale within a quarter.

## 11.7 Maintaining comments

Comments decay when they are treated as write-once artifacts. Techniques that slow the decay:

**Keep comments near the code.** A comment at the top of a 400-line file describing a function at the bottom will be missed. Put the comment directly above the declaration.

**Prefer higher-level comments.** "This module owns the retry policy for payment capture" survives refactoring better than "line 42 increments the counter."

**Avoid duplication.** If a fact is stated in three comments, two will be wrong eventually. State it once, where it is most visible.

**Check comment diffs.** When reviewing a change, ask: did the code's contract change? If so, did the comment? A diff that changes behavior without touching the comment is a warning sign.

**Delete dead comments.** Commented-out code, obsolete TODOs, and explanations of removed features are noise. Version control remembers; the codebase does not need to.

**Give TODOs an owner and a trigger.** `// TODO: replace with streaming` is a wish. `// TODO(alex): replace with streaming before importing files > 1 GB; see issue #482` is a plan.

## 11.8 The self-documenting-code debate

Two positions are common:

**Position 1: Comments are essential.** Code expresses mechanism; comments express intent, rationale, and contract. A codebase without comments forces every reader to reverse-engineer decisions. Interface comments are part of the design and should be written first.

**Position 2: Code should be self-documenting.** If code needs extensive comments to be understood, improve the code: better names, smaller functions, clearer types, explicit structure. Comments are a failure to express intent in code, and they drift.

The positions are less opposed than they appear. Both agree that:

- comments should not restate the code;
- names and structure are the first documentation;
- comments should carry information the code cannot.

They differ on **emphasis and timing**. Position 1 treats comments as a primary design artifact; Position 2 treats them as a last resort after the code has been made as clear as possible.

A workable synthesis:

1. **Make the code say as much as it can.** Names, types, structure, and tests are documentation.
2. **Comment what remains.** Contracts, rationale, invariants, surprises, and cross-module decisions.
3. **Write interface comments before the body** when the interface is non-trivial; they are design tools.
4. **Do not comment the obvious.** A comment that repeats the code is a maintenance cost with no benefit.
5. **Keep comments honest.** A stale comment is a defect; update or delete it.

The disagreement is real where it concerns volume: one school expects substantial commentary in production code, another expects only sparse, high-value notes. The right volume depends on the team, the domain, and the code's complexity—but the *kind* of comment that earns its place is the same in both schools.

## 11.9 TSDoc in practice

TypeScript's doc-comment syntax gives structure to interface documentation:

```typescript
/**
 * Calculates the interest accrued on a loan between two dates.
 *
 * Uses the actual/365 convention: the actual number of days elapsed
 * divided by 365, applied to the outstanding principal. The calculation
 * does not compound; callers that need compounding should call this
 * function once per period.
 *
 * @param principalCents - Outstanding principal in cents; must be >= 0.
 * @param annualRate - Annual nominal rate as a fraction (0.05 = 5%).
 * @param from - Start date, inclusive, in UTC.
 * @param to - End date, exclusive, in UTC.
 * @returns Interest in cents, rounded half-up.
 * @throws RangeError if `principalCents` is negative or `annualRate` is negative.
 *
 * @example
 * interestCents(100_000, 0.05, new Date("2026-01-01"), new Date("2026-01-31"));
 * // 411
 */
export function interestCents(
  principalCents: number,
  annualRate: number,
  from: Date,
  to: Date,
): number {
  if (principalCents < 0 || annualRate < 0) {
    throw new RangeError("principal and rate must be non-negative");
  }
  const days = (to.getTime() - from.getTime()) / 86_400_000;
  return Math.round(principalCents * annualRate * (days / 365));
}
```

The tags are not decoration; they establish a contract that tools can check and readers can scan. The `@example` is executable documentation: it shows the unit and the rounding.

## Summary

- Code expresses mechanism; comments express intent, contract, rationale, invariants, and surprises.
- The four excuses contain real concerns (stale comments, noise) but do not justify abandoning comments; they justify better ones.
- Interface comments describe behavior, parameters, errors, side effects, preconditions, performance, and concurrency—without implementation detail.
- Implementation comments explain why, invariants, workarounds, and non-obvious decisions.
- Comments-first is a design technique: if you cannot describe the contract, the interface is not ready.
- Maintain comments like code: keep them near, update them with changes, avoid duplication, and delete dead ones.
- Self-documenting code and comments-first are complementary: make the code say as much as possible, then document what it cannot.

## Exercises

1. **Interface comment.** Choose a public function with no documentation. Write a complete interface comment covering behavior, parameters, errors, side effects, and one edge case. Then check whether the implementation actually satisfies it.
2. **Delete the noise.** Find ten comments in a file. Classify each as contract, rationale, invariant, surprise, TODO, or restatement. Delete the restatements and rewrite one rationale comment to be more useful.
3. **Comment the why.** Find a piece of code with a non-obvious workaround. Add a comment stating the cause, the workaround, and the condition for removal.
4. **Stale comment hunt.** Search for comments that contradict the code. For each, decide whether the code or the comment is wrong, and fix both.
5. **Comments-first.** Take an interface you are about to implement. Write its documentation before writing the body. What design problems did the exercise reveal?
6. **Documentation map.** List the documentation your project has (README, API docs, decision records, runbooks, glossary). For each, identify the reader and the failure mode when it is missing or stale. What is the smallest useful addition?
