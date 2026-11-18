# 21. Requirements, Architecture, and Estimation

Three activities sit before and around code: deciding what to build, deciding how the pieces will fit, and predicting how long it will take. All three are uncertain, all three are political, and all three are badly served by false precision.

This chapter is about doing them with appropriate rigor: defining the problem before the solution, treating requirements as a loop rather than a document, using architecture to protect the decisions that are expensive to reverse, and estimating with ranges instead of promises.

## Learning objectives

- Define a problem precisely before committing to a solution.
- Treat requirements as a feedback loop with explicit assumptions and unknowns.
- Distinguish architectural decisions from ordinary ones.
- Evaluate a design's reversibility and choose where to invest in it.
- Produce estimates as ranges with stated confidence and assumptions.
- Decompose work to reduce uncertainty and avoid the planning fallacy.

## 21.1 Define the problem

Most project failures are decided at the start, before a line of code exists. The team builds the wrong thing, or builds the right thing for a user who does not exist, or solves a problem that the organization had already solved.

A good problem statement answers:

- **Who has the problem?** A specific person or role, not "users."
- **What are they doing now?** The current workaround, in detail.
- **What is wrong with it?** The cost: time, errors, risk, frustration.
- **What would better look like?** The outcome observed from outside, not the feature list.
- **How would we know?** A measurable change.

"We need a dashboard" is a solution. "Operations staff spend forty minutes each morning reconciling three spreadsheets to find orders stuck in transit, and about one in twenty is missed" is a problem. The second invites several solutions, one of which might be a scheduled email rather than a dashboard.

The most valuable question is often: **what happens if we do nothing?** If the answer is "nothing much," the project may be a solution looking for a problem.

![The problem definition is the foundation for everything that follows.](assets/problem-definition-foundation.png)

## 21.2 Requirements as a loop

Requirements are often treated as a fixed input: gather them, sign them off, build to them. In practice, the requirements change because the users learn what is possible, the market moves, and the team discovers that some requirements are incompatible.

A more honest model is a loop:

1. **Elicit.** Talk to the people who have the problem. Observe the work, do not just ask about it.
2. **Model.** Express what you learned as scenarios, rules, and constraints. Find the conflicts.
3. **Prototype.** Show something concrete. People react to artifacts far better than to descriptions.
4. **Refine.** Update the model and the priority order with what you learned.
5. **Repeat** until the remaining uncertainty is small enough to build, or until the cost of learning more exceeds the value.

Practices that make the loop work:

- **Separate needs from solutions.** "The report must be emailed at 6 a.m." is a solution; "the team must know the overnight failures before the stand-up" is a need.
- **Record assumptions.** Every requirement rests on beliefs about users, volumes, and behavior. Write them down so they can be invalidated.
- **Rank by value and cost.** A flat list of must-haves makes every trade-off a crisis. A ranked list lets the team drop the least valuable item when time runs short.
- **Make the unknowns explicit.** A requirement you do not understand is a risk, not a commitment.
- **Keep a decision log.** What was decided, when, by whom, and why. The "why" is what future readers need.

```typescript
// A requirement expressed as a testable outcome rather than a feature.
interface ServiceLevel {
  readonly name: string;
  readonly measure: "p95-latency-ms" | "error-rate" | "throughput-rps";
  readonly threshold: number;
  readonly workload: string;
}

const checkoutTarget: ServiceLevel = {
  name: "checkout responsiveness",
  measure: "p95-latency-ms",
  threshold: 300,
  workload: "200 rps, carts of 20 items, 10% coupon usage",
};
```

Writing the requirement as a measurable object forces the questions that prose hides: measured how, under what load, against what threshold.

![Know what you are aiming at before you shoot.](assets/aim-before-shooting.png)

![Without good requirements, the general problem may be right while specific aspects are wrong.](assets/requirements-missing-the-mark.png)

## 21.3 Architecture

**Architecture** is the set of decisions that are expensive to change later: the overall decomposition, the choice of major technologies, the data model, the integration style, the deployment topology, and the cross-cutting policies (security, observability, consistency).

Not every decision is architectural. Choosing a helper library is not; choosing a database paradigm is. The distinction is **cost of reversal**.

| Decision | Cost to reverse | Architectural? |
|----------|-----------------|----------------|
| Helper library | Hours | No |
| Internal function signature | Hours to days | No |
| Module boundary | Days | Sometimes |
| Data model / schema | Weeks to months | Yes |
| Database engine | Months | Yes |
| Synchronous vs. event-driven integration | Months | Yes |
| Monolith vs. services | Quarters | Yes |
| Public API contract | Years (external consumers) | Yes |

Architecture earns its keep by protecting the expensive decisions: making them deliberately, documenting the reasoning, and isolating them so that the cheap decisions stay cheap.

### Prerequisites for good architecture

Architecture is a response to constraints, and it cannot be good without knowing them:

- **Functional scope.** What must the system do? At least the core, stable parts.
- **Quality attributes.** Performance, availability, security, cost, operability. These often determine the structure more than the features do.
- **Constraints.** Team skills, existing systems, regulatory requirements, budget, timeline.
- **Context.** Who else consumes the system, and what do they already depend on?

Without these, architecture becomes speculation: elaborate structures justified by imagined requirements. A common failure is a microservice topology for a team of four with an unproven product, or a "future-proof" abstraction for a requirement nobody has asked for.

### Reversibility

The most useful architectural property is **reversibility**: how cheaply a decision can be undone.

Techniques:

- **Wrap external dependencies** behind your own interfaces, so a vendor can be replaced.
- **Separate the domain model from the storage schema**, with an explicit mapping layer.
- **Version wire formats and public APIs** from the start.
- **Keep policy in configuration or data**, not hard-coded in the deployment.
- **Use feature flags** to decouple deploy from release.
- **Prefer boring, well-understood technology** where the requirements do not demand otherwise.

Reversibility is not free: indirection, abstraction, and configuration add complexity. Invest in it where the decision is both **likely to change** and **expensive to undo**. A blanket "abstract everything" policy is just speculative generality with better branding.

```typescript
interface Order { readonly id: string; readonly totalCents: number }
interface Database {
  query(sql: string, params: readonly unknown[]): Promise<void>;
  queryOne<T>(sql: string, params: readonly unknown[]): Promise<T | undefined>;
}

// A storage interface owned by the domain: the database is a detail.
export interface OrderStore {
  save(order: Order): Promise<void>;
  findById(id: string): Promise<Order | undefined>;
}

// Infrastructure implements it; the domain never imports the driver.
export class PostgresOrderStore implements OrderStore {
  constructor(private readonly db: Database) {}

  async save(order: Order): Promise<void> {
    await this.db.query(
      "insert into orders (id, total_cents) values ($1, $2) on conflict (id) do update set total_cents = $2",
      [order.id, order.totalCents],
    );
  }

  async findById(id: string): Promise<Order | undefined> {
    const row = await this.db.queryOne<{ id: string; total_cents: number }>(
      "select id, total_cents from orders where id = $1",
      [id],
    );
    return row ? { id: row.id, totalCents: row.total_cents } : undefined;
  }
}
```

The interface is small and expressed in domain terms. If the database changes, only the implementation changes—provided the domain does not leak SQL types into its own model.

### Documenting architecture

Architecture that exists only in someone's head is re-litigated at every change. A minimal record is enough:

- **Context:** the system, its users, and its external dependencies.
- **Structure:** the major components and how they communicate.
- **Decisions:** the significant choices, with alternatives and consequences.
- **Constraints:** what must not change, and why.
- **Risks:** what is uncertain and what would trigger a revisit.

Diagrams help if they are few, current, and at a consistent level of abstraction. A diagram that shows every class is not architecture; it is a map at the wrong scale.

![Without a good architecture, the problem may be right and the solution wrong.](assets/architecture-wrong-solution.png)

![External quality characteristics interact: improving one can help, harm, or leave another unchanged.](assets/quality-characteristics.png)

## 21.4 Estimation

Estimation is predicting the future under uncertainty. It is not a promise, and treating it as one produces two failure modes: padded estimates that destroy trust, and optimistic estimates that destroy schedules.

### The cone of uncertainty

Estimates are least accurate at the beginning. Early in a project, the range might be 0.25× to 4× the eventual duration; after the requirements are stable, 0.8× to 1.25×. This is not a failure of skill; it is a property of information. The response is to estimate in ranges, and to narrow them by learning, not by pressure.

### Ranges, not points

An estimate should be a range with a confidence level and a statement of assumptions:

> "Six to nine weeks, 80% confidence, assuming the payment provider's sandbox is available by week two and no new compliance requirements appear."

A single number invites the listener to hear the optimistic end. A range with assumptions lets them see what would change it.

### Decomposition

Large estimates are unreliable because they aggregate many unknowns. Decompose until each piece is something you have done before, estimate the pieces, and sum with an allowance for integration.

```typescript
interface Estimate {
  readonly optimisticDays: number;
  readonly likelyDays: number;
  readonly pessimisticDays: number;
}

// PERT: weighted toward the likely value, with explicit tails.
function pertDays(estimate: Estimate): number {
  const { optimisticDays: o, likelyDays: m, pessimisticDays: p } = estimate;
  return (o + 4 * m + p) / 6;
}

// Standard deviation of the PERT distribution.
function pertStdDev(estimate: Estimate): number {
  return (estimate.pessimisticDays - estimate.optimisticDays) / 6;
}

const apiWork: Estimate = { optimisticDays: 3, likelyDays: 5, pessimisticDays: 12 };
const uiWork: Estimate = { optimisticDays: 4, likelyDays: 6, pessimisticDays: 10 };

const total = pertDays(apiWork) + pertDays(uiWork);
const spread = Math.sqrt(pertStdDev(apiWork) ** 2 + pertStdDev(uiWork) ** 2);
// total ≈ 10.5 days; one standard deviation ≈ 2.1 days
```

The formula does not make the estimate true. It makes the uncertainty explicit, and it exposes the two things that most inflate schedules: a long pessimistic tail (an unknown that could be a rewrite) and variance that adds up across independent tasks.

### The planning fallacy

People systematically underestimate how long their own work will take, even when they know similar work has taken longer before. The causes are well documented: we imagine the smooth path, forget the interruptions, and ignore the base rate.

Countermeasures:

- **Use reference class forecasting.** How long did similar work actually take, historically? Start there, then adjust for differences.
- **Track estimates against actuals.** Without data, you have no base rate. A simple log of estimate, actual, and what differed is enough.
- **Include the overhead.** Reviews, meetings, waiting for access, deployment, and bug fixing are part of the work, not interruptions to it.
- **Estimate the integration.** The last 20%—wiring, testing, fixing, deploying—is routinely underestimated.
- **Separate uncertainty from padding.** A range communicates uncertainty; a hidden buffer communicates nothing and gets consumed anyway.

### Communicating estimates

- **State the unit and the confidence.** "Five days" is ambiguous; "three to seven days, 80% confidence" is not.
- **State the assumptions.** The estimate is conditional; the conditions are the useful part.
- **Update as you learn.** An estimate is a forecast, not a contract. When the assumptions change, the estimate changes.
- **Separate estimate from commitment.** A commitment includes a buffer for the organization's risk tolerance; an estimate does not. Both are legitimate, but conflating them is how trust is lost.

![Estimates become more accurate as a project progresses, if they are revised.](assets/estimate-accuracy-over-time.png)

## 21.5 When the plan meets reality

Plans fail for predictable reasons: unknown unknowns surface late, dependencies slip, people leave, priorities change. A plan that assumes none of this is a fantasy.

Practical responses:

- **Plan in short horizons.** Detailed plans for the next two weeks, coarser plans beyond. Re-plan at each horizon with what you now know.
- **Track leading indicators.** Work in progress, cycle time, blocked items, and defect rates predict delivery better than percent-complete.
- **Make scope the variable.** Fixed time and fixed quality with variable scope is usually the only sustainable combination.
- **Surface risk early.** A risk that is named in week one is a design problem; the same risk in week ten is a crisis.
- **Keep an options mindset.** Prefer decisions that preserve future choices when the future is uncertain.

![Even largely sequential activities overlap to some degree.](assets/overlapping-activities-sequential.png)

![On other projects, activities overlap for the whole project.](assets/overlapping-activities-concurrent.png)

## Summary

- Define the problem—who, current workaround, cost, desired outcome, measure—before choosing a solution.
- Treat requirements as a loop of elicit, model, prototype, refine; record assumptions and rank by value and cost.
- Architecture is the set of decisions that are expensive to reverse; it protects those decisions and keeps cheap ones cheap.
- Good architecture requires knowing scope, quality attributes, constraints, and context; without them it is speculation.
- Invest in reversibility where decisions are both likely to change and expensive to undo.
- Estimate in ranges with confidence and assumptions; decompose, use historical base rates, and include integration and overhead.
- Plan in short horizons, make scope the variable, and surface risk early.

## Exercises

1. **Problem statement.** Take a feature request and rewrite it as a problem statement with who, current workaround, cost, desired outcome, and measure. What solutions does the new statement suggest that the original did not?
2. **Assumption inventory.** List five assumptions behind a current requirement. For each, state how you would test it and what would change if it were false.
3. **Reversibility audit.** List five decisions in your system. Estimate the cost to reverse each and classify it as architectural or not. Which decision deserves more isolation than it has?
4. **Architecture record.** Write a one-page architecture record for a system you know: context, structure, three decisions with alternatives, constraints, and risks.
5. **Estimate a past project.** Estimate a completed project as if starting today, then compare with what actually happened. What did you forget: integration, reviews, waiting, defects?
6. **Three-point estimate.** Break a piece of work into five tasks and give optimistic, likely, and pessimistic days for each. Compute the PERT total and the standard deviation. Which task dominates the uncertainty?
7. **Reference class.** Find historical data for similar work in your organization. What is the base rate for "estimate × factor"? How does it compare with your own estimates?
8. **Commitment vs. estimate.** Describe a situation where an estimate was treated as a commitment. What would have been a better way to communicate the uncertainty?
