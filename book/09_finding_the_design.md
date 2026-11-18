# 9. Finding the Design: Iteration, Prototypes, and Alternatives

Design is not a single act of inspiration. It is a search: you generate candidate structures, test them against the problem, learn something, and try again. Experienced designers are not people who get the right answer on the first try; they are people who are willing to discard a first answer when a second one is better.

This chapter is about running that search deliberately. It covers design-it-twice, a set of decomposition heuristics, the difference between prototypes and tracer bullets, domain languages, reversibility, and how to record a decision so the next person can understand it.

## Learning objectives

- Treat design as iterative search rather than a phase or an event.
- Produce at least two genuinely different designs for a significant decision and compare them on explicit criteria.
- Apply a catalog of decomposition heuristics without treating any as a law.
- Distinguish a throwaway prototype from a tracer bullet.
- Use domain language and reversibility to keep options open.
- Record design decisions with context, alternatives, and consequences.

## 9.1 Design is a process, not an event

The traditional picture—requirements, then design, then code—suggests that design ends when construction begins. In practice, design continues as long as the system changes. The useful question is not "when is design done?" but "how do we keep the design process honest?"

Three habits help:

**Iterate at the right grain.** Sketch the big structure before writing detailed code, but do not try to specify every routine. Design the parts you understand; discover the rest through construction; revisit the structure when the discoveries contradict it.

**Make the design concrete.** A design that exists only in conversation is hard to evaluate. Write the interface, sketch the call sites, implement a spike, or draw the data flow. Concreteness exposes problems that abstraction hides.

**Seek disconfirming evidence.** The first design you think of will feel right because it is yours. Deliberately look for the case it handles badly, the requirement it will not accommodate, and the caller it makes awkward. That is the purpose of designing it twice.

![The Tacoma Narrows Bridge: a design problem with no stable, complete specification.](assets/tacoma-narrows-bridge.png)

## 9.2 Design it twice

For any significant decision—a module interface, a data model, a protocol, a persistence strategy—produce **two genuinely different designs**, then compare them.

"Genuinely different" is the hard part. Two variations of the same idea (a class with five methods vs. a class with six) do not count. Try different axes:

- **Different decomposition:** by entity vs. by operation; by layer vs. by feature; by data flow vs. by lifecycle.
- **Different representation:** normalized vs. denormalized; mutable vs. immutable; typed tree vs. flat table.
- **Different ownership:** a smart object vs. a service; a pull API vs. a push API; synchronous vs. asynchronous.
- **Different generality:** a specialized interface vs. a general primitive with policy above it.
- **Different boundary:** in-process vs. separate service; library vs. framework; one module vs. two.

Then compare on explicit criteria:

| Criterion | Question |
|-----------|----------|
| Depth | Does the design hide more than it exposes? |
| Common case | Is the most frequent use simple? |
| Change impact | If a likely requirement changes, how many modules change? |
| Information hiding | Does each module own a clear secret? |
| Testability | Can the behavior be tested without constructing the world? |
| Failure behavior | Are failure modes explicit and comprehensible? |
| Reversibility | How expensive is it to change this decision later? |
| Cognitive load | How much must a new developer learn to use it? |

The comparison often produces a third design that combines the strengths of both. That is not cheating; it is the point.

### A worked comparison

Suppose we are designing a discount engine for a store. The requirements: percentage discounts, fixed-amount discounts, and "buy one, get one" offers; rules can be combined; the engine must be testable.

**Design A: polymorphic rules.**

```typescript
interface Cart {
  readonly lines: readonly { readonly sku: string; readonly unitCents: number; readonly quantity: number }[];
}

interface DiscountRule {
  apply(cart: Cart): number; // discount in cents
}

class PercentageOff implements DiscountRule {
  constructor(private readonly percent: number) {}
  apply(cart: Cart): number {
    const subtotal = cart.lines.reduce((s, l) => s + l.unitCents * l.quantity, 0);
    return Math.round(subtotal * (this.percent / 100));
  }
}

class BuyOneGetOne implements DiscountRule {
  constructor(private readonly sku: string) {}
  apply(cart: Cart): number {
    const line = cart.lines.find((l) => l.sku === this.sku);
    if (!line) return 0;
    return Math.floor(line.quantity / 2) * line.unitCents;
  }
}
```

**Design B: data-driven rules.**

```typescript
interface Cart {
  readonly lines: readonly {
    readonly sku: string;
    readonly unitCents: number;
    readonly quantity: number;
  }[];
}

type DiscountSpec =
  | { readonly kind: "percentage"; readonly percent: number }
  | { readonly kind: "fixed"; readonly cents: number }
  | { readonly kind: "bogo"; readonly sku: string };

function applyDiscount(cart: Cart, spec: DiscountSpec): number {
  switch (spec.kind) {
    case "percentage": {
      const subtotal = cart.lines.reduce((s, l) => s + l.unitCents * l.quantity, 0);
      return Math.round(subtotal * (spec.percent / 100));
    }
    case "fixed":
      return Math.min(spec.cents, cart.lines.reduce((s, l) => s + l.unitCents * l.quantity, 0));
    case "bogo": {
      const line = cart.lines.find((l) => l.sku === spec.sku);
      return line ? Math.floor(line.quantity / 2) * line.unitCents : 0;
    }
  }
}
```

Comparison:

- **Design A** is open for new behavior without modifying existing code (add a class), but each rule is a type with a constructor, and composing rules requires a separate mechanism. It is a good fit if rules have complex internal state or many variations.
- **Design B** is easy to serialize, store in a database, and edit through an admin UI. Adding a rule kind requires changing the switch, and the compiler's exhaustiveness check makes that safe. It is a good fit if rules are configuration rather than code.
- **Depth:** B has a smaller interface (one function, one union) but a larger internal switch. A has a smaller *conceptual* surface per rule but more types.
- **Change impact:** if the business wants user-defined rules, B wins. If rules grow into algorithms with state and composition, A wins.

A reasonable synthesis: use data-driven specs at the boundary (they are configuration), and compile them into rule objects internally if the logic becomes complex. The comparison revealed the real question—*are discounts data or code?*—which neither design answered alone.

![Polya's problem-solving heuristics, applied to design.](assets/polya-problem-solving.png)

## 9.3 Heuristics for decomposition

No heuristic decides a design, but a catalog of questions improves the search. These are the ones worth keeping in mind.

**Model the problem, not the solution.** Start from the entities and rules the domain experts talk about. If the code's vocabulary diverges from the domain's, every conversation requires translation.

**Find the real-world objects, then look for the concepts behind them.** A `Booking` may really be a `Reservation` with a lifecycle; a `Report` may be a query plus a renderer. The second abstraction often has better boundaries.

**Form consistent abstractions.** Every operation on a type should belong to the same level of abstraction. A `Customer` that can `validateTaxId`, `sendEmail`, and `renderHtml` has at least three abstractions inside it.

**Encapsulate what varies.** Identify the decisions likely to change (format, vendor, policy, algorithm) and give each a home.

**Hide secrets.** Ask what each module knows that others should not. If the answer is nothing, question the boundary.

**Prefer containment to inheritance** unless the is-a relationship is real and stable.

**Identify areas of change and isolate them.** A requirement that is likely to change deserves an interface, not a hard-coded branch.

**Keep coupling low and cohesion high.** A module should have one reason to change and few reasons to know about other modules.

**Design for testability.** If a design cannot be tested without a database, a network, and a clock, the design has coupled policy to infrastructure. Introduce seams.

**Iterate.** Sketch, critique, revise. The first design is a hypothesis, not a verdict.

**Avoid over-engineering.** A general mechanism nobody needs is complexity without leverage. Build for known requirements plus one step of likely growth, not for an imagined future system.

## 9.4 Prototypes and tracer bullets

Two practices are often confused because both produce early, incomplete software. They have different purposes.

A **prototype** is built to learn and then thrown away. It answers a question: Is this UI usable? Will this algorithm meet the latency budget? Does this architecture support the data model? Prototype code is deliberately disposable; keeping it is usually a mistake, because it was written for learning, not for production.

A **tracer bullet** is a thin, end-to-end slice through the real system. It is production-quality structure—interfaces, build, deployment, logging, tests—with minimal functionality. It answers a different question: Does the whole path work? It is meant to be extended, not discarded.

| | Prototype | Tracer bullet |
|---|-----------|---------------|
| Purpose | Learn / reduce uncertainty | Prove integration / establish structure |
| Scope | One risky aspect | Thin slice through all layers |
| Quality | Disposable | Production-quality skeleton |
| Outcome | Knowledge, then delete | Working path, then grow |
| Risk | Prototype becomes production | Slice is too thin to be useful |

Both are legitimate. The failure is to call a prototype a tracer bullet and ship it, or to build a tracer bullet so elaborate that it becomes a prototype with a deployment pipeline.

**When to prototype:** unfamiliar technology, uncertain UX, algorithmic risk, performance assumptions, a data model you cannot evaluate on paper.

**When to tracer-bullet:** a new system or a new integration where the end-to-end path is uncertain, a team that needs early feedback, a project where the architecture must be validated across layers.

## 9.5 Domain languages

A **domain language** expresses a solution in the vocabulary of the problem: a configuration format, a rule language, a query DSL, a small internal API that reads like the business rule.

```typescript
// A tiny internal DSL for pricing rules.
interface PricingCondition {
  customerType: "member" | "guest";
  minimumSpendCents: number;
}
interface PricingAction { percentageOff: number }

function definePricing(rule: { when: PricingCondition; then: PricingAction }) {
  return rule;
}

const rules = definePricing({
  when: { customerType: "member", minimumSpendCents: 5_000 },
  then: { percentageOff: 10 },
});
```

The benefit is a shorter distance between the requirement and the code. A domain expert can review the rule; a new developer can read it without decoding a pile of conditionals.

The costs are real:

- A language needs syntax, semantics, error handling, and documentation.
- A general language invites general-purpose programming, and soon you have written a bad interpreter.
- Tooling (validation, autocomplete, debugging) must be built or borrowed.

Start with the smallest thing that expresses the domain: a typed configuration object, a table, a small set of combinators. Build a parser only when the notation is genuinely more communicative than the data structure. A domain language is a design tool, not a status symbol.

## 9.6 Reversibility

Some decisions are cheap to change; others are expensive. **Reversibility** is the practice of keeping the expensive ones open as long as it is economical.

Techniques:

- Put a third-party dependency behind your own interface, so it can be replaced.
- Keep policy in configuration or data, not hard-coded in control flow.
- Separate the domain model from the persistence schema, with an explicit mapping.
- Avoid committing to a wire format before it is stable; version it.
- Design deployment so that the runtime can change (containers, feature flags, migration paths).

Reversibility has a price: indirection, abstraction layers, and configuration add complexity. The art is to make reversible the decisions that are **both likely to change and expensive to undo**, and to keep everything else simple. A blanket "abstract everything" policy is just another form of speculative generality.

## 9.7 Recording design decisions

A design that is not recorded is a design that will be re-litigated. A lightweight **decision record** captures:

- **Context:** the forces at play, the constraints, the requirements.
- **Decision:** what was chosen.
- **Alternatives:** what else was considered and why it was rejected.
- **Consequences:** what becomes easier, what becomes harder, what triggers a revisit.

```markdown
# Use integer minor units for money

Context: Prices and totals must be exact; floating-point rounding caused
mismatches between cart and invoice.

Decision: Represent money as integer minor units plus a currency code.

Alternatives: decimal library (heavier, still needs a currency type);
floating point with epsilon comparisons (rejected: rounding drift).

Consequences: All arithmetic must go through Money; formatting converts
at the boundary. Revisit if we support currencies with non-decimal minor
units, or if a decimal library becomes necessary for rates.
```

The record is short, and it answers the questions a future maintainer will ask: why is this like this, what else was considered, and when should we change it? It is also a defense against cargo cult: a decision with a recorded context is harder to copy blindly into a different context.

## 9.8 Design in a hurry

Design-it-twice sounds expensive. It usually is not, if it is scoped correctly:

- **Twenty minutes, two sketches.** For a module interface, sketch two versions on paper or in a scratch file. Compare the call sites.
- **One spike.** For an uncertain algorithm, write the smallest program that answers the question, then delete it.
- **Three call sites.** Before committing to an API, write the three most important call sites. If they are awkward, the API is wrong.
- **A design review.** Ask a colleague to use the interface without reading the implementation. Their questions are the missing documentation.

These are small investments with high returns because they happen before the design is encoded in dozens of call sites.

## Summary

- Design is an iterative search, not a phase; it continues as long as the system changes.
- Design a significant decision at least twice, on different axes, and compare on depth, common case, change impact, testability, failure behavior, and reversibility.
- Decomposition heuristics are questions, not laws: model the domain, encapsulate what varies, hide secrets, prefer containment, design for testability, avoid over-engineering.
- Prototypes are disposable learning artifacts; tracer bullets are thin production slices. Do not confuse them.
- Domain languages reduce the distance between problem and code but have real costs; start with the smallest notation that works.
- Keep expensive, likely-to-change decisions reversible.
- Record decisions with context, alternatives, and consequences.

## Exercises

1. **Design it twice.** Choose a module interface you are about to write. Produce two genuinely different designs (different decomposition or ownership, not different names). Compare them using the table in §9.2 and write a short recommendation.
2. **Three call sites.** Write the three most common call sites for an API you own. Then redesign the API to make them simpler. What did you have to give up?
3. **Prototype or tracer?** For a current uncertainty (performance, UX, integration), decide whether a prototype or a tracer bullet is appropriate. Define what you will learn and what you will do with the artifact afterward.
4. **Domain language test.** Take a complex configuration or rule set. Write it as a typed data structure that reads like the domain. Would a domain expert understand it? What would a real DSL add, and at what cost?
5. **Reversibility audit.** List three significant decisions in your system. For each, estimate the cost to reverse it. Which one deserves an abstraction layer, and which is fine as it is?
6. **Write a decision record.** Pick a design decision made in the last six months. Write the context, decision, alternatives, and consequences. What would a new team member learn that they cannot learn from the code?
