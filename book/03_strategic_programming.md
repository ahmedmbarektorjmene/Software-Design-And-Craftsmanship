# 3. Strategic Programming and the Economics of Design

Every codebase is the sum of thousands of decisions made under pressure. The pressure is real: users need the feature, the release is Friday, the bug is embarrassing. The question is not whether to feel pressure but what to do while feeling it. Two programmers can face the same deadline and leave behind very different systems, not because one works harder, but because one treats each change as a transaction and the other treats it as an investment.

This chapter is about that difference, and about the economics that make it rational.

## Learning objectives

- Distinguish tactical from strategic programming and recognize the "tactical tornado."
- Explain technical debt in terms of options and interest, without treating it as a moral failing.
- Apply a continuous-investment model to design work.
- Decide when "good enough" is genuinely good enough, and when it is a false economy.
- Use broken windows, small steps, and reversibility to keep a codebase healthy.
- Choose explicit quality goals rather than assuming quality is one thing.

## 3.1 Tactical programming

**Tactical programming** optimizes for the current task: make the feature work, fix the bug, ship the release. It is not lazy or incompetent. It is often skillful, fast, and locally correct. Its failure mode is cumulative.

A tactical change looks like this:

```typescript
// The task: show whether an order has shipped.
// The quickest path: a string flag, set in three places.

interface Order {
  id: string;
  // ...
  status: string; // "new" | "paid" | "shipped" | "cancelled" (by convention)
}

function markShipped(order: Order): void {
  order.status = "shipped";
}
```

The comment states a convention, but nothing enforces it. A typo (`"Shippped"`) compiles. A new status added by another developer is not handled by the UI. The type system, which could have helped, has been switched off for this field. The change took two minutes and will cost hours later—not because it was wrong, but because it deferred a decision that was cheap to make now and expensive to make later.

The extreme form is the **tactical tornado**: a developer who produces working features at high speed, leaving a trail of shortcuts, duplicated logic, and undocumented assumptions. Tornadoes are often celebrated because their output is visible. The cleanup is distributed across everyone who follows, which makes the cost invisible in the short term and enormous in the long term.

## 3.2 Strategic programming

**Strategic programming** accepts that working code is necessary but not sufficient. Each change should leave the design at least as good as it was—ideally slightly better. The feature still ships; the difference is that the developer spends a little time asking:

- Does this change fit the existing abstractions, or does it fight them?
- Is the quick version creating a dependency or an implicit rule that will be hard to change?
- Can I make the interface simpler while I am here?
- Is there a test that would make the next change safe?

Strategy does not mean gold-plating. It means **paying attention to the trajectory**, not just the position. A strategic programmer will happily ship an imperfect design when the imperfection is visible, contained, and temporary. What they will not do is hide the imperfection in a place where it silently constrains future work.

The same tactical change, done strategically, might look like this:

```typescript
type OrderStatus = "new" | "paid" | "shipped" | "cancelled";

interface Order {
  id: string;
  status: OrderStatus;
}

function markShipped(order: Order): void {
  if (order.status !== "paid") {
    throw new Error(`Cannot ship order in status "${order.status}"`);
  }
  order.status = "shipped";
}
```

This is not more complex; it is the same logic with the states made explicit. The type now documents the domain, the transition rule is enforced in one place, and adding a status requires a compiler error at every unhandled site (with an exhaustive check, shown in Chapter 14). The extra five minutes are an investment with a clear return.

![Tactical work starts faster; strategic work sustains progress.](assets/tactical-vs-strategic.jpg){width=50%}

## 3.3 Technical debt, precisely

"Technical debt" is a useful metaphor if used carefully and a harmful one if used as a synonym for "code I don't like."

Debt has three parts:

- **Principal:** the work required to fix the design.
- **Interest:** the extra cost incurred by every change made while the debt exists.
- **Term:** how long the debt will remain.

A shortcut is rational when the interest is low, the term is short, and the principal is affordable. It is irrational when interest compounds—when every new feature must work around the shortcut, so the cost of fixing it grows faster than the cost of living with it.

```typescript
// A deliberate, documented shortcut with a repayment trigger.
// DEBT: prices are stored as floating-point dollars. This is acceptable
// for the prototype (no arithmetic across currencies), but must become
// integer minor units before we support refunds or multi-currency totals.
// Repayment trigger: first refund feature, or first non-USD currency.
type PriceInDollars = number;
```

The comment is not decoration. It records the decision, the reason, and the trigger, which converts an invisible risk into a managed one. The worst debt is not the shortcut itself; it is the shortcut that no one remembers making.

> **Debt is not an excuse.** "We'll refactor later" is a plan only if someone owns the later. Without a trigger, a repayment estimate, and a place to track it, "later" means "never," and the interest is paid by people who did not incur the debt.

## 3.4 How much to invest

There is no universal percentage, but a useful planning heuristic is to reserve roughly **10–20% of development effort for design improvement**: extracting duplicated rules, simplifying interfaces, adding tests that make refactoring safe, improving names, deleting dead code.

This is not a separate phase. It is a habit distributed across ordinary work:

- When you touch a routine, leave its name accurate.
- When you add a third branch to a conditional, consider a table or a polymorphic dispatch.
- When you duplicate a rule, extract it or document why the copies must differ.
- When you fix a bug, add the regression test and ask what design would have prevented it.

The percentage is a budgeting aid, not a law. A prototype may invest almost nothing and be thrown away. A payment system may invest far more. The important part is that the investment is **conscious** and **continuous**, rather than a heroic cleanup project every two years. Large cleanups are risky precisely because they are large; continuous improvement keeps the diffs small and the tests green.

Two failure modes are common:

- **Zero investment.** The codebase degrades until change becomes terrifying. At that point, the "big rewrite" looks attractive—and usually fails, because the team has not practiced the design skills that would make the rewrite better.
- **Runaway investment.** The team polishes abstractions that no one uses, builds frameworks before understanding the problem, and misses the market. Design investment is justified by future change, not by aesthetic purity.

![The cost of a mistake rises with the complexity of the structure.](assets/simple-structure-mistake.png)

![More complex structures need more planning.](assets/complex-structure-planning.png)

![The cost of fixing a defect rises with the time before it is found.](assets/cost-of-late-defects.png)

![Neither the fastest nor the slowest development approach produces the fewest defects.](assets/development-approach-defects.png)

## 3.5 Broken windows

A broken window is a small, visible defect that signals that nobody is maintaining the place. In a codebase, broken windows include failing tests that everyone ignores, commented-out code, misleading names, TODO lists from three years ago, and lint warnings that have become background noise.

The mechanism is social and psychological: once one window is broken, breaking another costs less. Once a codebase is visibly neglected, each new shortcut feels normal. Conversely, a codebase that is visibly cared for exerts a mild pressure toward care.

The practical rule is not "fix every imperfection immediately." It is:

1. **Fix small things now** when the fix is cheap and safe.
2. **Board up what you cannot fix**: mark it, track it, and prevent it from spreading.
3. **Never let a known defect become invisible.** A failing test that is skipped with a comment is better than a failing test that is deleted; a documented workaround is better than an undocumented one.

Broken windows are the day-to-day enforcement mechanism for the investment model. You cannot schedule a cleanup for every small problem, but you can refuse to let small problems become the background.

## 3.6 Good enough, and not good enough

"Good enough software" is a legitimate and important idea: quality is not a single axis, and shipping a product that meets its users' needs is the point. A team that delays a release to polish an internal abstraction has misunderstood the economics.

But "good enough" is often misapplied. It is a statement about **fitness for a purpose**, not a permission slip for design neglect. The useful version distinguishes quality dimensions:

| Dimension | Question | "Good enough" means |
|-----------|----------|---------------------|
| Correctness | Does it do the right thing? | Meets the specified behavior, including edge cases that matter |
| Reliability | Does it keep doing it? | Failure rate acceptable for the domain |
| Usability | Can users accomplish their goal? | No blocking friction for the core task |
| Performance | Is it fast enough? | Meets the stated latency/throughput target |
| Security | Can it be abused? | No known exploitable class of vulnerability left unaddressed |
| Maintainability | Can we change it? | The next planned change is not blocked by the design |
| Testability | Can we verify it? | Critical behavior has automated checks |

"Good enough" must be chosen **per dimension**, explicitly, and communicated. A release can be good enough on visual polish and not good enough on data loss. A prototype can be good enough on maintainability and not on correctness. The failure is to use the phrase globally, as if quality were a single dial that can be turned down.

There is a genuine tension here, and it should not be smoothed over:

- One view holds that shipping early and refining in response to users is usually the highest-value strategy; perfection is a form of waste, and requirements will change anyway.
- Another holds that working code is not enough, that continuous design investment is what keeps the cost of change low, and that "we'll clean it up later" is the most expensive sentence in software.
- A third holds that prevention is cheaper than rework, so quality should be designed in from the start rather than inspected in at the end.

These are not as contradictory as they sound. The first is about **product scope and market timing**; the second is about **design trajectory**; the third is about **defect economics**. You can ship a narrow product early (first view), keep the design healthy as you go (second view), and prevent defects rather than chase them (third view). What you cannot do is use any one of them to excuse neglect of the other two.

## 3.7 Small steps and reversibility

Strategic work is easier when changes are small and reversible.

- **Small steps** keep the feedback loop short. A 50-line change can be reviewed, tested, and understood; a 2,000-line change cannot. Small steps also make it easier to identify which change caused a regression.
- **Reversibility** keeps options open. Prefer designs that can be changed: abstract third-party dependencies behind your own interface, keep policy in configuration or data, avoid hard-coding assumptions about deployment or vendors.
- **No final decisions.** Treat significant decisions as current best hypotheses, documented with the conditions under which you would revisit them.

Reversibility has a cost: abstraction layers and configuration add indirection. The art is to make reversible the decisions that are **likely to change and expensive to reverse**, and to keep the rest simple.

## 3.8 Quality is a process, not an inspection

If defects are cheaper to prevent than to find and fix, then quality must be built into the way work is done: clear requirements, deliberate design, small changes, tests written alongside code, reviews, static analysis, and honest measurement. Inspecting quality at the end—a test phase, a bug bash—catches only what escaped.

This does not mean process ceremony. It means that the **shape of the work** determines the defect rate. A team that writes large batches, integrates rarely, and tests manually will produce more defects than a team that works in small increments with automated checks—regardless of how talented the individuals are.

The economic argument is simple: the cost of a defect grows with how far it travels from its origin. A misunderstanding caught in a requirements conversation costs minutes. The same misunderstanding caught in code review costs hours. Caught in production, it costs customers, incident response, and trust. The cheapest defect is the one that never enters the code; the second cheapest is the one caught the same day.

## Summary

- Tactical programming optimizes the current task and defers design decisions; strategic programming treats each change as an investment in the system's future.
- Technical debt is principal, interest, and term. It is rational when interest is low, term is short, and repayment is planned; it is corrosive when invisible.
- Reserve roughly 10–20% of effort for continuous design improvement; avoid both zero investment and runaway polish.
- Broken windows are small visible defects that lower the standard for everything around them. Fix, board up, or track—never ignore.
- "Good enough" is a per-dimension, purpose-specific judgment, not a global permission to neglect design.
- Small steps, reversibility, and prevention beat large cleanups and end-stage inspection.

## Exercises

1. **Classify a shortcut.** Find a deliberate shortcut in your codebase. Write down its principal, its interest, and its term. Is there a repayment trigger? If not, propose one.
2. **Investment audit.** For the last two weeks, estimate the fraction of your time spent on design improvement (not new features, not bug fixes). Is it closer to 0%, 10%, or 30%? What would you change?
3. **Broken windows.** Walk through your repository and list five broken windows. For each, decide: fix now, board up (mark/track), or accept deliberately. What makes the difference?
4. **Good-enough matrix.** Take a feature you are building. Rate it on each dimension in the table (correctness, reliability, usability, performance, security, maintainability, testability) as "must be excellent," "good enough," or "not a goal." Share the result with a stakeholder. Where do your expectations differ?
5. **Reversibility test.** Identify a decision in your system that would be expensive to reverse (a database choice, a public API shape, a file format). What would it cost to make it reversible? Is the cost worth it? Write a one-paragraph recommendation.
6. **Small-step challenge.** Take a change you are planning and split it into three commits, each of which leaves the system working and tested. If you cannot, explain what coupling prevents it.
