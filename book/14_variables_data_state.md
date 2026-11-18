# 14. Variables, Data, and State

Data outlives code. Functions are rewritten, frameworks are replaced, modules are split and merged, but the shape of the data—what a record means, which values are legal, how long a value lives—tends to persist. That is why data design deserves more care than it usually gets.

This chapter is about the state a program carries: where variables live, how they are initialized, when they are immutable, what the primitive types do not tell you, and how to make illegal values hard to create.

## Learning objectives

- Choose variable scope and lifetime deliberately.
- Initialize every variable at its point of declaration, and explain why.
- Use immutability and `const` as defaults, and know when mutation is justified.
- Recognize the costs of global and shared mutable state.
- Avoid the classic traps of numeric, string, and boolean primitives.
- Handle text as Unicode rather than as an array of characters.
- Replace magic values with named, typed constants.
- Reason about binding time: when a value becomes fixed.

## 14.1 Scope and lifetime

A variable's **scope** is the region of code where its name is visible. Its **lifetime** is the period during which its value exists. Good design keeps both as small as possible.

Small scope has three benefits:

- **Fewer interactions.** A variable visible in one function cannot be corrupted by another.
- **Easier naming.** In a five-line block, `total` is unambiguous; at module scope, it invites collisions.
- **Easier deletion.** When the block disappears, so does the variable and every reference to it.

TypeScript gives several scopes: module, function, block (`let`/`const`), and class field. The default should be the innermost scope that works. A variable declared at module scope *because it was convenient* is a variable every future function can reach.

```typescript
// Scope wider than necessary: `runningTotal` is visible to every function in the module.
let runningTotal = 0;

export function addLine(amountCents: number): void {
  runningTotal += amountCents;
}

export function resetTotal(): void {
  runningTotal = 0;
}

export function reportTotal(): number {
  return runningTotal;
}
```

```typescript
// Scope limited to the object that owns the state.
export class InvoiceTotal {
  #cents = 0;

  add(amountCents: number): void {
    this.#cents += amountCents;
  }

  reset(): void {
    this.#cents = 0;
  }

  get value(): number {
    return this.#cents;
  }
}
```

The class version makes the state an explicit dependency. Two invoices can exist at once; tests can create one per case; there is no hidden channel between functions.

**Lifetime** is subtler than scope. A module-level cache lives as long as the process; a closure variable lives as long as the closure; a `WeakMap` key lives until it is collected. Long lifetimes create the conditions for stale data and memory leaks. Ask of every long-lived variable: *who clears this, and when?* If the answer is "nobody," it is a latent bug.

![Variable lifetime: long-lived, short-lived, and spanning a loop.](assets/variable-live-time.png)

## 14.2 Initialization

Initialize variables where they are declared. A variable that exists before it has a meaningful value is a trap: it invites reads before writes, and it forces the reader to scan for the assignment.

```typescript
interface Customer { readonly isMember: boolean }
declare const customer: Customer;

// Uninitialized: the reader must find the assignment.
let discountCentsBefore: number;
if (customer.isMember) {
  discountCentsBefore = 500;
} else {
  discountCentsBefore = 0;
}

// Initialized from an expression: the value is defined once.
const discountCentsAfter = customer.isMember ? 500 : 0;
```

Guidelines:

- **Prefer `const`.** If a value never changes after initialization, `const` documents that and prevents accidental reassignment.
- **Initialize at declaration.** If the value depends on a condition, use a conditional expression or an immediately invoked function rather than a declaration-then-assignment pair.
- **Avoid sentinel initial values.** `let total = -1` to mean "not computed" is a hidden state machine; use a union type or a separate `computed` flag.
- **Do not reuse a variable for a second purpose.** Reassignment with a new meaning (`total` becomes `discountedTotal`) forces the reader to track the change.

```typescript
declare function findUserId(email: string): string | undefined;
declare const email: string;

// A sentinel value standing in for "no result".
let userId = ""; // empty string means "not found"?
const found = findUserId(email);
if (found !== undefined) userId = found;
if (userId === "") { /* ... */ }
```

```typescript
// Absence is explicit in the type.
declare function findUserId(email: string): string | undefined;
declare const email: string;

const userId: string | undefined = findUserId(email);
if (userId === undefined) { /* ... */ }
```

The second version makes the "not found" case impossible to ignore. In TypeScript, `undefined` is part of the type; an empty string is a legal string that happens to be special only by convention.

## 14.3 Immutability

Mutable state is the root of a large share of bugs: a value changes when a caller did not expect it, a function mutates its argument, a shared object is updated from two places. Immutability removes whole categories of failure.

Use immutability as the default:

```typescript
interface Order {
  readonly id: string;
  readonly lines: readonly OrderLine[];
}

interface OrderLine {
  readonly sku: string;
  readonly quantity: number;
}

// A "change" returns a new order rather than mutating the old one.
function withQuantity(order: Order, sku: string, quantity: number): Order {
  return {
    ...order,
    lines: order.lines.map((line) =>
      line.sku === sku ? { ...line, quantity } : line,
    ),
  };
}
```

`readonly` on properties and `readonly T[]` on arrays prevent accidental mutation at compile time. They are shallow: `readonly` does not make nested objects immutable, and it is erased at runtime. For deep guarantees, use a library, `Object.freeze` at boundaries, or a persistent data structure.

Mutation is justified when:

- **The data structure is large and copying is expensive.** A 100,000-element buffer updated in a loop should be mutated in place, with clear ownership.
- **The state is inherently sequential.** A state machine's current state, a cursor, a builder under construction.
- **The mutation is local and encapsulated.** A class may mutate its private fields freely; the outside world sees only method calls.
- **The language or framework expects it.** Some APIs require in-place updates.

The rule is not "never mutate" but "**make mutation visible and owned**." A function that mutates its argument should say so in its name and its documentation; a class that mutates its own state should be the only one allowed to.

## 14.4 Global and shared state

A **global** is any state reachable from everywhere: a module-level variable, a singleton, a mutable static field, an environment variable read at arbitrary points, a global cache.

Globals are attractive because they avoid passing parameters. They are dangerous because:

- **Hidden coupling.** Any function can read or write the global; the dependency does not appear in any signature.
- **Order dependence.** Behavior depends on what ran before.
- **Test interference.** Tests share the global and must reset it, or leak state into each other.
- **Concurrency hazards.** Two threads or requests can interleave writes.
- **Lifetime confusion.** The global outlives the request, the test, or the user session that set it.

```typescript
// Global mutable configuration: every consumer is implicitly coupled.
export let config = { retries: 3, timeoutMs: 5_000 };

export function setConfig(next: typeof config): void {
  config = next;
}

export function fetchWithRetry(url: string): Promise<Response> {
  // reads the global at call time
  return fetch(url, { signal: AbortSignal.timeout(config.timeoutMs) });
}
```

```typescript
// Explicit dependency: the consumer declares what it needs.
export interface HttpClientConfig {
  readonly retries: number;
  readonly timeoutMs: number;
}

export function createFetcher(config: HttpClientConfig) {
  return (url: string): Promise<Response> =>
    fetch(url, { signal: AbortSignal.timeout(config.timeoutMs) });
}
```

The second version can be tested with any timeout, used with two configurations in one process, and understood without searching for who last called `setConfig`.

Some globals are acceptable:

- **True constants** (`const MAX_RETRIES = 3`) that never change.
- **Process-wide infrastructure** created once at startup (a logger, a database pool) and passed explicitly thereafter. Environment variables read once and validated at startup are a form of this.
- **Platform globals** (`Math`, `JSON`) that are stateless.

The test is not "is it at module scope?" but "**can two instances of this behavior coexist?**" If not, the global is a hidden singleton, and the design has quietly assumed there is only one of everything.

## 14.5 Primitive types and their traps

Primitives are convenient and dangerously permissive. A `number` can be a price, an ID, a duration, a count, or a percentage; the type system will not stop you from adding a price to a duration.

**Numeric traps:**

- **Floating-point money.** `0.1 + 0.2 !== 0.3`. Use integer minor units or a decimal library.
- **Integer overflow.** JavaScript numbers are doubles; integers are exact only up to 2^53 − 1. Use `bigint` for larger values.
- **`NaN` propagation.** `NaN !== NaN`, and any arithmetic with `NaN` yields `NaN`. Validate at boundaries.
- **Unit confusion.** Milliseconds vs. seconds, cents vs. dollars, kilograms vs. pounds. Encode units in names and types.
- **Off-by-one in ranges.** Decide once whether an interval is inclusive or exclusive, and apply it consistently.

**String traps:**

- **Strings as enums.** `status: string` accepts `"Actve"`. Use literal unions.
- **Strings as IDs.** Two different ID types are interchangeable unless branded.
- **Strings as structured data.** Parsing `"a,b,c"` by hand invites quoting and escaping bugs.
- **Encoding confusion.** UTF-8 bytes, UTF-16 code units, and Unicode code points are different things.

**Boolean traps:**

- **Boolean parameters.** `send(email, true)` is unreadable; use an options object or two functions.
- **Booleans that need a third state.** `isLoading` plus `hasError` can both be true; a single discriminated union is clearer.
- **Negated booleans.** `isNotReady` invites double negations; name the positive condition.

```typescript
type JobId = string & { readonly __brand: "JobId" };

// Primitive soup: every parameter is a number or a string.
declare function schedulePrimitive(
  job: string,
  at: number,
  retries: number,
  timeout: number,
): void;

// Named, unit-bearing types.
interface ScheduleRequest {
  readonly jobId: JobId;
  readonly runAtEpochMs: number;
  readonly maxRetries: number;
  readonly timeoutMs: number;
}
declare function schedule(request: ScheduleRequest): void;
```

![The memory used by each primitive data type.](assets/data-type-memory.png)

![A picture of the pointer changes needed to relink a structure.](assets/relinking-pointers.png)

## 14.6 Strings and Unicode

A JavaScript string is a sequence of UTF-16 code units, not a sequence of characters. This matters the moment text is not ASCII.

```typescript
// U+1F468, ZWJ, U+1F469, ZWJ, U+1F467, ZWJ, U+1F466 — one family
const family = "\u{1F468}\u{200D}\u{1F469}\u{200D}\u{1F467}\u{200D}\u{1F466}";
console.log(family.length);        // 11 — UTF-16 code units, not people
console.log([...family].length);   // 7 — code points, still not grapheme clusters
```

Operations that assume one code unit per character break on emoji, combining accents, and many scripts:

- `text[i]` may split a surrogate pair.
- `text.slice(0, n)` may cut a character in half.
- `text.length` is not a user-visible character count.
- Reversing a string by code unit corrupts it.

For user-facing operations—truncation, cursor movement, counting characters—use `Intl.Segmenter` to work in grapheme clusters:

```typescript
const segmenter = new Intl.Segmenter("en", { granularity: "grapheme" });

function graphemeCount(text: string): number {
  let count = 0;
  for (const _ of segmenter.segment(text)) count++;
  return count;
}

function truncateGraphemes(text: string, max: number): string {
  const segments = [...segmenter.segment(text)];
  return segments.slice(0, max).map((s) => s.segment).join("");
}
```

For storage and comparison, normalize: two visually identical strings can have different code point sequences. `text.normalize("NFC")` is the usual choice for Western text; some scripts need different normalization forms, and identifiers need case-folding rules.

Other string guidelines:

- **Compare with a collator, not `<`.** `"é" < "z"` depends on locale and encoding; `Intl.Collator` implements locale-aware ordering.
- **Do not build SQL, HTML, or shell commands by concatenation.** Use the target's escaping mechanism or, better, a parameterized API.
- **Treat encoding at boundaries.** Decode bytes to text once, at the edge, and state the encoding.
- **Keep secrets out of strings that get logged.** Redact at the logging boundary, not at every call site.

## 14.7 Magic values

A **magic number** is a literal whose meaning is not apparent from context. Each literal below encodes a policy, and the code offers no help to a reader who needs to know what that policy is:

```typescript
interface User { readonly ageYears: number }
interface Order { readonly totalCents: number }
declare const user: User;
declare const order: Order;
declare const retries: number;

// Before: every literal hides a policy and a unit.
const eligibleBefore =
  user.ageYears >= 18 && order.totalCents > 5000 && retries < 3;

// After: each policy has a name and a unit.
const ADULT_AGE_YEARS = 18;
const FREE_SHIPPING_THRESHOLD_CENTS = 5_000;
const MAX_RETRY_ATTEMPTS = 3;

const eligibleAfter =
  user.ageYears >= ADULT_AGE_YEARS &&
  order.totalCents > FREE_SHIPPING_THRESHOLD_CENTS &&
  retries < MAX_RETRY_ATTEMPTS;
```

The names carry the unit and the policy. Not every literal needs a name: `0`, `1`, `-1` as loop bounds or array offsets are usually clear. The test is whether a reader would have to guess *why* the value is what it is.

Two refinements:

- **Name the concept, not the number.** `ADULT_AGE_YEARS` is better than `EIGHTEEN`.
- **Put policy in one place.** If the threshold governs several code paths, a single constant (or a configuration value) prevents drift.

## 14.8 Binding time

**Binding time** is when a value or decision becomes fixed. A number can be bound at:

- **coding time:** a literal in the source;
- **compile time:** a constant computed by the compiler;
- **startup time:** read from configuration or the environment;
- **runtime:** computed from data, or fetched from a service;
- **user time:** chosen by the end user in a settings screen.

The later the binding, the more flexible the system—and the more it must handle missing, invalid, or changing values. The earlier the binding, the simpler and faster the code, but the more often it must be rebuilt or redeployed to change.

```typescript
// Bound at coding time: changing the rate requires a code change and deploy.
const TAX_RATE = 0.2;

// Bound at startup: change the environment, restart, no rebuild.
declare const env: Record<string, string | undefined>;
const taxRate = Number(env.TAX_RATE ?? "0.2");

// Bound at runtime per transaction: change in the data, no restart.
interface TaxPolicy { rateFor(region: string, at: Date): number }
```

Choose the latest binding time that the requirement actually needs. Binding early "just in case" adds configuration surface nobody uses; binding late when the value is genuinely constant adds lookup cost and failure modes for no benefit.

A useful discipline is to **bind once and pass explicitly**: read the environment at startup, validate it, and inject the result. That gives late binding without scattering environment reads through the code.

## 14.9 Making illegal states unrepresentable

The strongest data design removes invalid combinations from the type entirely.

```typescript
// Legal by type, invalid in practice: both fields can be set, or neither.
interface Payment {
  cardLast4?: string;
  bankIban?: string;
}
```

```typescript
// Each alternative carries exactly its own data.
type Payment =
  | { readonly kind: "card"; readonly last4: string }
  | { readonly kind: "bank"; readonly iban: string }
  | { readonly kind: "cash"; readonly receivedCents: number };
```

The second version cannot represent "card and bank at once" or "card with no number." Every consumer narrows on `kind` before reading a field, and the compiler checks the narrowing.

The same technique applies to:

- **Loading states:** `{ status: "idle" } | { status: "loading" } | { status: "ready"; data: T } | { status: "error"; error: E }`.
- **Optional configuration:** a union of `{ enabled: true; value: X }` and `{ enabled: false }` when `value` is meaningful only when enabled.
- **Identifiers:** branded types for IDs that must not be mixed.
- **Ranges:** a `PositiveInt` constructor that validates once, so every downstream function can assume positivity.

The cost is more types and more narrowing at boundaries. The benefit is that invalid states cannot travel through the system, so the failure is caught where it is created rather than three layers later.

![Sequential data: handled in a defined order.](assets/sequential-data.png)

![Selective data: one representation or another, never both.](assets/selective-data.png)

![Iterative data: a collection of repeated elements.](assets/iterative-data.png)

## Summary

- Keep scope and lifetime as small as possible; question every long-lived variable about who clears it.
- Initialize at declaration, prefer `const`, and avoid sentinel values in favor of explicit optionality.
- Immutability is the default; mutate only when ownership is clear, the operation is local, or the cost of copying is real.
- Globals hide dependencies and break isolation. Ask whether two instances of the behavior can coexist; if not, you have a hidden singleton.
- Primitives are permissive: encode units in names and types, use integer minor units for money, and avoid strings as enums or IDs.
- Strings are UTF-16 code units; use `Intl.Segmenter`, normalization, and collation for user-facing text.
- Name magic values after the policy they encode, with units.
- Choose a binding time that matches the requirement, then bind once and pass explicitly.
- Prefer types that make illegal states unrepresentable.

## Exercises

1. **Scope reduction.** Find a module-level `let` or a class field that is used by only one function. Move it into the smallest scope that works. What becomes easier to test?
2. **Initialization audit.** Find declarations separated from their first assignment. Rewrite each as a `const` initialized from an expression. Did any reveal a hidden state machine?
3. **Sentinel removal.** Find a value that uses `-1`, `""`, or `null` to mean "no result." Replace it with `undefined` or a union type. List the call sites that must now handle absence.
4. **Global inventory.** List every global your service reads or writes. For each, decide whether it is a true constant, startup infrastructure, or hidden shared state. Convert one into an explicit dependency.
5. **Unicode test.** Write a function that truncates a string to *n* user-perceived characters. Test it with emoji, combining accents, and a right-to-left script. What breaks with `slice(0, n)`?
6. **Magic-value pass.** Find ten numeric or string literals with policy meaning. Name them, add units, and move shared ones to a single module. Which ones were duplicated?
7. **Illegal states.** Find an interface with optional fields that are valid only in certain combinations. Rewrite it as a discriminated union. Add an exhaustive handler and count the branches that disappeared.
8. **Binding-time decision.** For three configuration values, decide whether each should be bound at coding, startup, or runtime. Justify with a concrete scenario in which the choice matters.
