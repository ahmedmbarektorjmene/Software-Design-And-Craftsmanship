# 12. Routines and the Pseudocode Programming Process

Routines are the basic unit of intellectual manageability. A function with a precise name and a clear contract lets a reader treat a block of code as a single idea. A function with a vague name, seven parameters, and three responsibilities does the opposite: it forces the reader to hold the whole body in mind and to guess what the rest of the system expects.

This chapter is about designing routines well: what they are for, how to decide their boundaries, how to shape their interfaces, and how to build them with a process that keeps design and code aligned.

## Learning objectives

- Decide when a routine is justified, and which responsibility it should own.
- Classify cohesion and use it to diagnose a routine that does too much.
- Choose a routine length based on complexity rather than a line-count rule.
- Design parameter lists that are hard to misuse.
- Separate commands from queries and keep side effects honest.
- Apply the Pseudocode Programming Process to move from intent to code.
- Write routine interfaces that document their contracts.

## 12.1 Why routines exist

The most important reason to create a routine is **to make the program easier to understand**. Everything else is secondary:

- **Reduce complexity.** A well-named routine replaces a block of detail with one concept.
- **Avoid duplication.** One implementation of a rule is easier to change than five.
- **Name an intent.** `applyLateFee` says more than a loop with arithmetic.
- **Isolate change.** A routine gives a decision one home.
- **Enable testing.** A routine with a clear contract can be tested in isolation.
- **Enable reuse.** Code used in two places should usually live in one.
- **Improve correctness.** Small, focused routines are easier to reason about and review.

Saving space is a weak reason. Modern compilers inline small functions, and source size is rarely the constraint. Readability, reliability, and modifiability are better reasons.

A routine is justified when it has a **single, nameable purpose** and when naming that purpose helps a reader. It is not justified merely because a line is long or because a block "looks extractable." Extraction has a cost: a new name, a new interface, a jump in the reader's attention. The benefit must exceed that cost.

## 12.2 Cohesion

Cohesion is the degree to which the parts of a routine belong together. It is the best single diagnostic for whether a routine should be split.

| Cohesion | Description | Example |
|----------|-------------|---------|
| Functional | Every part contributes to one task | `calculateInvoiceTotal` |
| Sequential | Output of one step is input to the next | `parse → validate → normalize` |
| Communicational | Operations share the same data | `updateName` and `updateAddress` on one record |
| Temporal | Operations happen at the same time | `initialize` (open file, start timer, load config) |
| Logical | Operations are selected by a control flag | `handle(kind)` with unrelated branches |
| Coincidental | No meaningful relationship | `utils()` |

**Functional cohesion** is the target. A function that computes a total, validates an address, or formats a date has one job.

**Sequential cohesion** is often acceptable inside a routine, but it is a sign that the routine might be a pipeline of smaller steps. If each step is independently useful or testable, extract them.

**Communicational cohesion** groups operations that touch the same data but do different things. It is common in data-transfer objects and can be acceptable for simple accessors, but it often produces a "god object" if it grows.

**Temporal cohesion** is the `init()` smell: unrelated setup steps bundled because they happen at startup. Such routines are hard to test (you must run all of it) and hard to change (every step sees every other step's state). Prefer explicit dependencies and separate setup functions.

**Logical cohesion** is a function that branches on a mode to do unrelated work:

```typescript
// Logical cohesion: unrelated operations selected by a string.
function process(entity: "user" | "order" | "invoice", data: unknown): void {
  switch (entity) {
    case "user": /* validate email, hash password, send welcome */ break;
    case "order": /* reserve stock, charge card, send receipt */ break;
    case "invoice": /* compute tax, render PDF, email customer */ break;
  }
}
```

The branches share only a name. Split them, or use polymorphic dispatch if the operations genuinely share a contract.

**Coincidental cohesion** is a `Utils` module: functions with no relationship beyond "we did not know where to put them." It is a sign that the design lacks a home for a concept.

> **Cohesion test:** can you describe what the routine does in one sentence, without "and" or "then"? If not, it probably has more than one responsibility.

## 12.3 Size

There is no correct line count. A 5-line function can be incomprehensible if it hides a dense regular expression; a 60-line function can be clear if it is a linear sequence of well-named steps. Length is a **symptom**, not a criterion.

The real criteria are:

- **Cohesion:** does the routine do one thing?
- **Nesting:** how many levels of conditionals and loops must the reader track?
- **Local state:** how many variables change across the body?
- **Abstraction level:** does every line operate at the same level of detail?
- **Nameability:** can the routine be named precisely?

A common guideline is to keep routines short enough to read without scrolling, and to extract when a block has a clear name and a stable interface. But applying a hard limit (for example, "no function over 20 lines") can produce shallow, fragmented code: a sequence of one-line functions that forces the reader to jump across the file to understand a single operation.

The opposite failure is the 300-line function with ten local variables and five levels of nesting. It is not complex because it is long; it is long because it is complex. Splitting it along cohesive seams usually helps; splitting it arbitrarily does not.

> **Depth over length.** A short function that merely forwards to another is shallow. A longer function that hides a coherent algorithm behind a clear name can be deep. Judge the interface and the cohesion, not the line count.

![Splitting a method by extracting a subtask or by dividing its responsibilities.](assets/splitting-a-method.jpg){width=95%}

## 12.4 Parameters

A parameter list is an interface. It should be short, ordered for readability, and hard to misuse.

**Keep the count low.** Seven parameters is already difficult to remember; more is a sign that the routine has too many responsibilities or that the data belongs in an object. A parameter object is often better:

```typescript
interface User { readonly id: string }
type Role = "admin" | "member";

// Too many positional parameters: easy to swap, hard to read.
declare function createUser(
  firstName: string,
  lastName: string,
  email: string,
  passwordHash: string,
  role: string,
  isActive: boolean,
  createdAt: Date,
): User;

// Named fields: self-documenting and extensible.
interface CreateUserInput {
  readonly firstName: string;
  readonly lastName: string;
  readonly email: string;
  readonly passwordHash: string;
  readonly role: Role;
  readonly isActive: boolean;
  readonly createdAt: Date;
}
declare function createUser(input: CreateUserInput): User;
```

**Avoid flag arguments.** A boolean parameter usually means the routine does two things:

```typescript
interface User { readonly id: string }
declare function sendEmail(user: User, urgent: boolean): void;
declare function sendWelcomeEmail(user: User): void;
declare function sendPasswordResetEmail(user: User): void;
const user: User = { id: "user-1" };

// What does `true` mean at the call site?
sendEmail(user, true);

// Clearer: two routines, or an options object with a named field.
sendWelcomeEmail(user);
sendPasswordResetEmail(user);
```

If a flag is genuinely a policy choice (e.g., `includeArchived`), name it in an options object: `listOrders({ includeArchived: true })`.

**Order parameters for readability.** Put the subject first, then the configuration: `transfer(from, to, amount)` reads better than `transfer(amount, from, to)`. Keep the order consistent across similar routines.

**Separate input from output.** Avoid routines that mutate several parameters and return a status code. If a routine must produce multiple values, return an object with named fields.

**Validate at the boundary, not in every routine.** A public routine should validate its inputs; internal routines can rely on the contract, enforced by types and assertions.

**Document units and constraints.** `timeoutMs`, `amountCents`, `retryCount`. The type tells you it is a number; the name tells you what kind.

## 12.5 Commands, queries, and honesty

A **query** returns information and has no observable side effects. A **command** changes state and may or may not return a result. Mixing the two makes code surprising:

```typescript
interface User { readonly id: string }
const cache = new Map<string, User>();
const database = { load(id: string): User { return { id }; } };
declare function touchLastAccess(id: string): void;

// Surprising: a getter that mutates.
function getUser(id: string): User {
  const user = cache.get(id);
  if (!user) {
    const loaded = database.load(id);
    cache.set(id, loaded); // side effect
    touchLastAccess(id);   // another side effect
    return loaded;
  }
  return user;
}
```

There is nothing wrong with caching, but the name `getUser` suggests a query. A caller may call it in a loop, in a render path, or in a test, without expecting writes. Either rename it to describe the effect (`loadUserAndTouch`) or separate the concerns.

Prefer **command-query separation**: a function either returns a value or changes state, not both. This is a guideline, not a law—pop operations and atomic increments legitimately do both—but violations should be deliberate and documented.

**Functions should return what their names promise.** A function named `validateEmail` should return a validation result, not send an email. A function named `save` should persist, not silently normalize and persist. Honest names are a form of contract.

## 12.6 The Pseudocode Programming Process

The **Pseudocode Programming Process (PPP)** is a way to design a routine before writing code:

1. **Design the routine.** Decide its purpose, name, parameters, return value, and error behavior.
2. **Write pseudocode.** Use plain language at the level of intent, not language syntax.
3. **Review the pseudocode.** Check the logic, edge cases, and data flow before translating.
4. **Write the code.** Translate each pseudocode line into one or a few lines of code.
5. **Review the code.** Check that it matches the pseudocode and the contract.
6. **Iterate.** If the code reveals a design problem, revise the pseudocode and repeat.

The pseudocode becomes the comments. This is the practical link between design and documentation: the comments are not an afterthought; they are the design, preserved.

### A worked example

Suppose we need a function that calculates a shipping cost.

```text
calculateShippingCost(order, destination, carrier):
    if order has no physical items:
        return 0

    weight = sum of physical item weights
    if weight <= 0:
        error "order has physical items but no weight"

    base = carrier.baseRate(destination.zone)
    perKg = carrier.perKgRate(destination.zone)
    cost = base + ceil(weight) * perKg

    if destination is remote:
        cost = cost * 1.5

    if order.subtotal >= freeShippingThreshold:
        cost = 0

    return round(cost)
```

The pseudocode exposes decisions that would otherwise be buried in code: free shipping overrides remote surcharge; weight is rounded up; an order with physical items but zero weight is an error. A reviewer can challenge these choices before they are encoded.

```typescript
interface ShippingItem {
  readonly weightKg: number;
  readonly isPhysical: boolean;
}

interface Order {
  readonly items: readonly ShippingItem[];
  readonly subtotalCents: number;
}

interface Destination {
  readonly zone: string;
  readonly isRemote: boolean;
}

interface Carrier {
  baseRate(zone: string): number;
  perKgRate(zone: string): number;
}

const FREE_SHIPPING_THRESHOLD_CENTS = 5_000;

export function calculateShippingCost(
  order: Order,
  destination: Destination,
  carrier: Carrier,
): number {
  const physicalItems = order.items.filter((item) => item.isPhysical);
  if (physicalItems.length === 0) return 0;

  const weightKg = physicalItems.reduce((sum, item) => sum + item.weightKg, 0);
  if (weightKg <= 0) {
    throw new Error("Order has physical items but no weight");
  }

  const base = carrier.baseRate(destination.zone);
  const perKg = carrier.perKgRate(destination.zone);
  let cost = base + Math.ceil(weightKg) * perKg;

  if (destination.isRemote) {
    cost *= 1.5;
  }

  if (order.subtotalCents >= FREE_SHIPPING_THRESHOLD_CENTS) {
    cost = 0;
  }

  return Math.round(cost);
}
```

The code matches the pseudocode line for line. The comments written during pseudocoding can remain as section comments if the logic is non-obvious; the function name and types carry the rest. The process caught the zero-weight case before it became a production bug.

### When to use PPP

PPP is most useful when:

- the routine has non-trivial logic or edge cases;
- the design is not obvious from the signature;
- you are likely to get lost in syntax;
- the routine will be reviewed or maintained by others.

It is overkill for a one-line getter. It is also not the only option: test-first development, stepwise refinement, and writing the interface comment first are compatible techniques. The common thread is **design before syntax**.

![The activities of class construction, in their usual order.](assets/class-construction-activities.png)

![The activities of routine construction.](assets/routine-construction-activities.png)

![Designing a routine: these steps need not happen in a fixed order.](assets/routine-design-steps.png)

## 12.7 Pure functions and the functional core

A **pure function** returns a value determined only by its arguments and has no observable side effects. Pure functions are easier to test, reason about, cache, and parallelize.

```typescript
// Pure: no I/O, no mutation, deterministic.
function applyDiscount(subtotalCents: number, percent: number): number {
  return Math.round(subtotalCents * (1 - percent / 100));
}
```

A useful architecture is the **functional core, imperative shell**:

- The core contains pure calculations and decisions: pricing, validation, state transitions.
- The shell contains I/O, time, randomness, and mutation: HTTP, database, clock, logging.
- The shell gathers inputs, calls the core, and applies the results.

```typescript
interface Subscription {
  readonly cancelled: boolean;
  readonly expiresAt: Date;
}

// Core: pure decision.
interface RenewalDecision {
  readonly shouldRenew: boolean;
  readonly amountCents: number;
  readonly reason: string;
}

function decideRenewal(
  subscription: Subscription,
  now: Date,
  priceCents: number,
): RenewalDecision {
  if (subscription.cancelled) {
    return { shouldRenew: false, amountCents: 0, reason: "cancelled" };
  }
  if (subscription.expiresAt > now) {
    return { shouldRenew: false, amountCents: 0, reason: "not expired" };
  }
  return { shouldRenew: true, amountCents: priceCents, reason: "expired" };
}
```

The pure core can be tested with plain values; the shell is thin and can be integration-tested. This separation is not always practical—some domains are inherently stateful—but it is a strong default for business logic.

## Summary

- Routines exist to make programs understandable; saving space is a minor reason.
- Functional cohesion is the target; temporal and logical cohesion are warnings, and coincidental cohesion is a design smell.
- Length is a symptom, not a criterion; judge cohesion, nesting, state, and abstraction level.
- Keep parameter lists short, named, and hard to misuse; avoid flag arguments and document units.
- Separate commands from queries and make side effects honest.
- PPP designs a routine in prose before code; the pseudocode becomes the comments and exposes edge cases early.
- Pure functions and a functional core make behavior testable and reasoning local.

## Exercises

1. **Cohesion audit.** Take three routines. Classify each by cohesion. For the weakest, propose a split along functional lines and write the new names.
2. **Parameter redesign.** Find a routine with five or more parameters. Rewrite it with a parameter object or by splitting it. Compare the call sites.
3. **Flag argument.** Find a boolean parameter that changes behavior. Replace it with two routines or a named option. Which call sites become clearer?
4. **PPP a routine.** Choose a routine with non-trivial branching. Write pseudocode at the level of intent, review it for edge cases, then implement from it. What did the pseudocode catch?
5. **Command or query?** Find a function that both returns a value and mutates state. Decide whether to split it or document the effect. Rewrite one call site to make the effect explicit.
6. **Pure core.** Extract a pure decision function from a routine that mixes calculation with I/O. Write tests for the pure function without mocks. What did the extraction reveal about the logic?
