# 7. Interfaces, Types, and Object Design

Types are the cheapest design tool we have. A type can make an invalid state unrepresentable, document a boundary, and turn a runtime bug into a compile-time error. It can also lie, over-constrain, and multiply until the type system becomes a second program that nobody can read.

This chapter is about designing the data and the objects that carry it: abstract data types, class interfaces, construction and invariants, inheritance versus composition, and the small decisions—getters, setters, enums, unions—that shape how a codebase feels to work in.

## Learning objectives

- Design an abstract data type from its operations and invariants, not from its fields.
- Write class interfaces that are consistent, complete, minimal, and honest about failure.
- Enforce invariants at construction and preserve them through mutation.
- Choose between inheritance, composition, and interface implementation with clear criteria.
- Evaluate getters, setters, and Tell-Don't-Ask against real constraints.
- Model alternatives with discriminated unions and exhaustive checks.
- Organize modules so dependencies point in a sensible direction.

## 7.1 Abstract data types

An **abstract data type (ADT)** is a set of values together with the operations allowed on them, described independently of any representation. A stack is a collection with `push`, `pop`, and `isEmpty`; the fact that it might be implemented with an array or a linked list is not part of the type.

Designing an ADT means answering three questions:

1. **What are the values?** What states are valid?
2. **What operations are allowed?** What can a client do, and what does each operation guarantee?
3. **What are the invariants?** What is always true of a valid value?

For a `Money` type:

- Values: an integer number of minor units and a currency.
- Operations: add, subtract, multiply by a scalar, compare, format.
- Invariants: the amount is an integer; the currency is a supported ISO code; addition requires matching currencies.

```typescript
export type Currency = "USD" | "EUR" | "JPY";

export class Money {
  readonly #minorUnits: number;
  readonly #currency: Currency;

  private constructor(minorUnits: number, currency: Currency) {
    if (!Number.isSafeInteger(minorUnits)) {
      throw new RangeError(`Amount must be a safe integer: ${minorUnits}`);
    }
    this.#minorUnits = minorUnits;
    this.#currency = currency;
  }

  static of(minorUnits: number, currency: Currency): Money {
    return new Money(minorUnits, currency);
  }

  static dollars(amount: number): Money {
    return new Money(Math.round(amount * 100), "USD");
  }

  get currency(): Currency {
    return this.#currency;
  }

  get minorUnits(): number {
    return this.#minorUnits;
  }

  add(other: Money): Money {
    this.#requireSameCurrency(other);
    return new Money(this.#minorUnits + other.#minorUnits, this.#currency);
  }

  subtract(other: Money): Money {
    this.#requireSameCurrency(other);
    return new Money(this.#minorUnits - other.#minorUnits, this.#currency);
  }

  multiply(factor: number): Money {
    if (!Number.isFinite(factor)) throw new RangeError("factor must be finite");
    return new Money(Math.round(this.#minorUnits * factor), this.#currency);
  }

  #requireSameCurrency(other: Money): void {
    if (this.#currency !== other.#currency) {
      throw new Error(`Currency mismatch: ${this.#currency} vs ${other.#currency}`);
    }
  }

  format(locale = "en-US"): string {
    return new Intl.NumberFormat(locale, {
      style: "currency",
      currency: this.#currency,
    }).format(this.#minorUnits / 100);
  }
}
```

Several design decisions are embedded here:

- **The constructor is private.** Callers go through named factories, so the representation can change and invalid values cannot be constructed casually.
- **The representation is integer minor units.** Floating-point currency is a classic source of errors; the type makes the safer representation the only one.
- **Currency is part of the value.** Adding dollars to euros is prevented by the type's invariant, not by a convention.
- **The getters expose facts, not mutable state.** `currency` and `minorUnits` are read-only. There is no `setAmount`.
- **Formatting is a method, but it delegates to a locale-aware formatter.** Presentation policy is not baked into arithmetic.

The public interface is small, and every operation preserves the invariants. That is what an ADT buys: a client can reason about `Money` without knowing how it stores anything.

## 7.2 What makes a class interface good

A class interface is the set of public operations and the contract each one obeys. Good interfaces share several properties:

**Consistent abstraction.** Every method should operate at the same level. A `Money` class with `add`, `subtract`, and `writeToDatabase` mixes arithmetic with persistence; the abstraction is inconsistent.

**Complete.** The interface should let callers do everything they legitimately need. A collection with `add` but no `remove` forces callers to reach into internals.

**Minimal.** It should not expose operations that callers do not need. Every public method is a commitment. A method that exists "just in case" is a maintenance liability.

**Clear.** Names and types should make the common case obvious; the contract should state units, ranges, ownership, and failure behavior.

**Honest about failure.** If an operation can fail, the interface should say so—through a return type, a documented error, or a thrown exception. Silent failure is a design defect.

**Hard to misuse.** Prefer designs where the wrong call does not compile or throws immediately, rather than producing a subtly wrong result.

A useful review question: **can a new team member use this class correctly after reading only its public declarations and documentation?** If not, the interface is incomplete or the documentation is.

## 7.3 Construction and invariants

An object should be valid the moment it is constructed. Constructors that leave fields unset, or that require a subsequent `init()` call, create a window in which the object violates its own invariants.

```typescript
// Fragile: between the constructor and init(), the object is invalid.
class Connection {
  #socket: WebSocket | undefined;
  constructor(private readonly url: string) {}
  init(): void {
    this.#socket = new WebSocket(this.url);
  }
  send(message: string): void {
    this.#socket!.send(message); // non-null assertion hides the risk
  }
}
```

The `!` is a confession: the type system knows the object can be incomplete. Better:

```typescript
class Connection {
  readonly #socket: WebSocket;
  private constructor(socket: WebSocket) {
    this.#socket = socket;
  }
  static async open(url: string): Promise<Connection> {
    const socket = new WebSocket(url);
    await new Promise<void>((resolve, reject) => {
      socket.addEventListener("open", () => resolve(), { once: true });
      socket.addEventListener("error", () => reject(new Error(`Cannot connect to ${url}`)), { once: true });
    });
    return new Connection(socket);
  }
  send(message: string): void {
    this.#socket.send(message);
  }
}
```

Now a `Connection` is always connected. The asynchronous work lives in a static factory, and the type reflects reality.

For objects with many optional parameters, a **builder** or an options object with defaults keeps the call site readable. The options object should be validated once, at the boundary, and converted into a fully initialized object.

```typescript
interface RetryPolicy {
  readonly attempts: number;
  readonly baseDelayMs: number;
  readonly maxDelayMs: number;
}

function retryPolicy(options: Partial<RetryPolicy> = {}): RetryPolicy {
  const attempts = options.attempts ?? 3;
  const baseDelayMs = options.baseDelayMs ?? 100;
  const maxDelayMs = options.maxDelayMs ?? 5_000;
  if (attempts < 1) throw new RangeError("attempts must be >= 1");
  if (baseDelayMs < 0 || maxDelayMs < baseDelayMs) throw new RangeError("invalid delay bounds");
  return { attempts, baseDelayMs, maxDelayMs };
}
```

## 7.4 Inheritance and composition

Inheritance comes in two forms, with very different consequences.

**Interface inheritance** (implementing a contract) is usually safe. A class promises to satisfy an interface; callers depend on the contract, not the implementation. In TypeScript, `implements` checks the shape at compile time and erases at runtime.

**Implementation inheritance** (extending a class) couples the subclass to the parent's implementation. The subclass inherits fields, protected methods, initialization order, and every assumption the parent makes. Changes to the parent can break subclasses in ways the type checker cannot see. This is the **fragile base class** problem.

```typescript
class Report {
  protected rows: string[] = [];
  addRow(row: string): void {
    this.rows.push(row);
  }
  render(): string {
    return this.rows.join("\n");
  }
}

class CsvReport extends Report {
  override render(): string {
    return this.rows.map((row) => row.split(",").join(";")).join("\n");
  }
}
```

`CsvReport` depends on `rows` being an array of strings in a particular order. If `Report` changes to stream rows, or to store them in a map, `CsvReport` breaks. The parent cannot be changed without considering every subclass.

Composition avoids this:

```typescript
interface RowSource {
  rows(): readonly string[];
}

class CsvRenderer {
  constructor(private readonly source: RowSource) {}
  render(): string {
    return this.source.rows().map((row) => row.split(",").join(";")).join("\n");
  }
}
```

`CsvRenderer` depends only on `RowSource`, a narrow contract. It can be tested with a stub, combined with any row source, and changed without touching the source.

Use inheritance when:

- the relationship is genuinely **is-a**, and every instance of the subtype is substitutable for the supertype;
- the parent is designed for extension (documented hooks, stable invariants);
- the hierarchy is shallow and unlikely to grow;
- the shared behavior is more than a single method.

Use composition when:

- the relationship is **has-a** or **uses-a**;
- behavior should be combinable at runtime;
- the parent's implementation is an incidental detail;
- you want to avoid protected state and initialization-order coupling.

In TypeScript, mixins and multiple `implements` can share behavior without a deep hierarchy, but they add their own complexity. Prefer the simplest mechanism that expresses the relationship.

## 7.5 Getters, setters, and Tell-Don't-Ask

A getter/setter pair that merely exposes a field is a public field with extra ceremony:

```typescript
class Account {
  #balanceCents = 0;
  get balanceCents(): number { return this.#balanceCents; }
  set balanceCents(value: number) { this.#balanceCents = value; }
}
```

The setter allows any value, including negative balances, without validation. The getter invites callers to compute their own rules. The class has become a data bag with methods.

There are three positions worth distinguishing:

- **Avoid mechanical accessors.** Exposing implementation data violates information hiding and adds shallow interface surface. A class should offer behavior, not a window into its fields.
- **Use accessors at boundaries.** Serialization, frameworks, debugging, and gradual migration sometimes require reading state. A getter is preferable to a public field because it preserves the ability to change the representation later, and a setter can validate.
- **Tell, don't ask.** Prefer asking an object to perform an operation over extracting its state, deciding outside, and writing it back.

```typescript
class Account {
  #balanceCents = 0;

  get balanceCents(): number { return this.#balanceCents; }
  set balanceCents(value: number) { this.#balanceCents = value; }

  withdraw(amountCents: number): void {
    if (amountCents <= 0) throw new RangeError("amount must be positive");
    if (amountCents > this.#balanceCents) throw new Error("insufficient funds");
    this.#balanceCents -= amountCents;
  }
}

const account = new Account();
account.balanceCents = 5_000;
const amountCents = 1_000;

// Ask: the caller owns the rule, and can bypass the invariant.
if (account.balanceCents >= amountCents) {
  account.balanceCents -= amountCents;
}

// Tell: the object owns the invariant.
account.withdraw(amountCents);
```

The second version can enforce sufficient funds, prevent negative balances, record a transaction, and change its representation without affecting callers.

Computed properties are a legitimate use of getters: `get isEmpty(): boolean { return this.#items.length === 0; }` expresses a derived fact and keeps the representation private. Validation in a setter is legitimate when the setter is the public API for a mutable field. What is not legitimate is a getter/setter pair that exists only because "fields should be private."

## 7.6 Modeling alternatives

String literals, enums, and discriminated unions model a fixed set of alternatives. Prefer them to booleans and magic strings.

```typescript
type OrderStatus = "draft" | "placed" | "paid" | "shipped" | "cancelled";

interface Order {
  readonly id: string;
  readonly status: OrderStatus;
}

function isTerminal(status: OrderStatus): boolean {
  switch (status) {
    case "shipped":
    case "cancelled":
      return true;
    case "draft":
    case "placed":
    case "paid":
      return false;
    default: {
      const exhaustive: never = status;
      return exhaustive;
    }
  }
}
```

The `never` check makes the compiler complain when a new status is added and a branch is missing. That is a small piece of type-level design that prevents a real class of bugs.

A **discriminated union** goes further: each alternative carries its own data.

```typescript
type Payment =
  | { kind: "card"; last4: string; authorization: string }
  | { kind: "bank"; iban: string; reference: string }
  | { kind: "cash"; receivedCents: number };

function describe(payment: Payment): string {
  switch (payment.kind) {
    case "card": return `card ending ${payment.last4}`;
    case "bank": return `bank transfer ${payment.reference}`;
    case "cash": return `cash ${payment.receivedCents}`;
  }
}
```

A caller cannot read `last4` without first narrowing to `kind: "card"`. Invalid combinations are unrepresentable. This is usually better than a single interface with optional fields, where every consumer must guess which fields are present.

Enums (`enum Color { Red, Green }`) are also an option in TypeScript, but string-literal unions are often preferable: they serialize naturally, produce readable values, and avoid the runtime object that numeric enums emit. Use `const enum` cautiously; it is erased at compile time and can break across module boundaries.

## 7.7 Modules and dependency direction

At the package level, the same principles apply:

- **Expose a deliberate public API.** A package entry point is an interface. Deep imports into internal files make every file a public API.
- **Point dependencies inward.** Domain logic should not depend on UI, database, or HTTP frameworks. Adapters depend on the domain; the domain depends on abstractions it owns.
- **Avoid cycles.** A cycle between modules means they are one module with an artificial boundary.
- **Keep shared utilities small and owned.** A `utils` package that everything depends on becomes a coupling hub and a dumping ground.

```typescript
// domain/pricing.ts — knows nothing about HTTP or the database.
interface Money { multiply(factor: number): Money }

export interface PriceLookup {
  priceOf(sku: string): Promise<Money>;
}

export async function quote(
  sku: string,
  quantity: number,
  prices: PriceLookup,
): Promise<Money> {
  if (!Number.isInteger(quantity) || quantity < 1) {
    throw new RangeError("quantity must be a positive integer");
  }
  return (await prices.priceOf(sku)).multiply(quantity);
}
```

The domain defines the `PriceLookup` interface; the infrastructure implements it. Dependencies point toward the domain, and the domain can be tested without a database.

## 7.8 TypeScript notes

- **`interface` vs. `type`.** Both describe object shapes. Use `interface` for contracts that may be extended or implemented; use `type` for unions, intersections, and aliases. Consistency matters more than the choice.
- **Structural typing.** Types are compatible if their shapes match. This enables lightweight testing but weakens nominal distinctions; brands help where identity matters.
- **`readonly` is shallow.** `readonly items: Item[]` prevents reassigning `items` but not mutating the array. Use `readonly Item[]` or `ReadonlyArray<Item>` for element immutability.
- **`unknown` over `any`.** `unknown` forces narrowing before use; `any` disables checking. Reserve `any` for genuinely dynamic boundaries and isolate it.
- **`satisfies` preserves inference.** `const config = { ... } satisfies Config` checks the shape without widening the literal types.
- **Exhaustiveness.** A `never` check in the default branch turns missing cases into compile errors.

## Summary

- An ADT is defined by its values, operations, and invariants, not by its fields.
- A good class interface is consistent, complete, minimal, clear, honest about failure, and hard to misuse.
- Objects should be valid at construction; use private constructors and factories when initialization is complex.
- Interface inheritance is usually safe; implementation inheritance couples subclasses to parent internals. Prefer composition unless is-a is real and stable.
- Avoid mechanical getters and setters; expose behavior and computed facts, and use accessors deliberately at boundaries.
- Model alternatives with literal unions and discriminated unions; use exhaustive checks to keep them honest.
- Organize packages around a deliberate public API with dependencies pointing inward.

## Exercises

1. **ADT from operations.** Pick a domain concept (booking, subscription, inventory item). Write its values, operations, and invariants before writing any fields. Then implement the type and check that every operation preserves the invariants.
2. **Constructor audit.** Find a class with an `init()` method, optional fields, or non-null assertions. Redesign it so every instance is valid at construction.
3. **Inheritance review.** Find an inheritance hierarchy. For each subclass, state the is-a claim and whether the subclass is fully substitutable. Replace one subclass with composition and compare the two designs.
4. **Accessor decision.** Find a getter/setter pair. What rule does the setter enforce? What would a behavior-oriented method look like? Rewrite one call site in Tell-Don't-Ask style.
5. **Union modeling.** Find a type with several optional fields that are valid only in certain combinations. Replace it with a discriminated union and add an exhaustive handler.
6. **Dependency direction.** Draw the dependencies among five packages in your system. Identify any cycle or domain-to-infrastructure dependency. Propose an interface that would reverse the arrow.
