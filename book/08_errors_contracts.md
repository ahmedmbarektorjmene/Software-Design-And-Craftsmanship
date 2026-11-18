# 8. Errors, Contracts, and Defensive Design

Every program has two behaviors: the one it was designed for, and the one it exhibits when the world does not cooperate. The second behavior is where most production incidents live. A missing file, a malformed request, a null from a database, a timeout, a programmer's off-by-one—each is a place where the clean flow of the design meets an inconvenient reality.

This chapter is about designing that meeting deliberately. It covers contracts, assertions, exceptions, result types, validation boundaries, resource ownership, and the oldest argument in error handling: should you prevent errors, detect them, or make them impossible?

## Learning objectives

- Classify failures and choose a response appropriate to each class.
- Specify preconditions, postconditions, and invariants as part of an interface.
- Use assertions for programmer errors and validation for external input.
- Compare exceptions, result types, and defined-out errors, including their costs.
- Apply fail-fast and barricade principles without hiding legitimate failures.
- Manage resources deterministically across success and failure paths.
- Explain the major positions in the error-handling debate and the conditions under which each applies.

## 8.1 A taxonomy of failure

Error handling goes wrong when one mechanism is used for every kind of failure. A useful first step is to classify:

| Class | Example | Who can fix it? | Default response |
|-------|---------|-----------------|------------------|
| Programmer error | Index out of bounds, impossible state, broken invariant | Developer | Assert / fail fast; fix the code |
| Expected domain failure | Insufficient funds, invalid coupon, duplicate email | Caller or user | Explicit result, typed error |
| Environmental failure | Network timeout, disk full, service unavailable | Operations / infrastructure, sometimes retry | Retry, fallback, surface with context |
| Unrecoverable corruption | Invariant broken in production, inconsistent ledger | Incident response | Stop, preserve evidence, do not continue |
| User input error | Malformed form field | User | Validate at boundary, return actionable message |

The classification is not always obvious. A "file not found" can be expected (the user asked to open a path) or environmental (a mount disappeared). The question to ask is: **who has enough context to decide what to do?** If the caller can decide, expose the failure. If the module can decide better, handle it there. If nobody can decide, fail loudly.

## 8.2 Contracts

A **contract** specifies what a caller must provide and what the operation guarantees:

- **Precondition:** what must be true before the call.
- **Postcondition:** what will be true after the call, assuming the precondition held.
- **Invariant:** what remains true throughout the object's lifetime.

```typescript
interface Money { format(): string }

interface Account {
  /**
   * Withdraws `amount` from the account.
   *
   * Precondition: amount > 0 and amount <= balance.
   * Postcondition: balance decreases by amount; a transaction is recorded.
   * Invariant: balance >= 0 at all times.
   *
   * @throws RangeError if amount <= 0
   * @throws InsufficientFundsError if amount > balance
   */
  withdraw(amount: Money): void;
}
```

The contract is part of the interface. It tells callers what they are responsible for and what they may rely on. Without it, every caller must read the implementation, and every implementation change risks breaking an unstated assumption.

Contracts can be enforced at different strengths:

- **Documented only.** Cheap, but relies on discipline.
- **Checked at runtime.** Assertions or explicit validation; catches violations during development and at boundaries.
- **Checked by the type system.** The strongest option when the constraint can be expressed in types (non-empty arrays, branded IDs, discriminated unions).
- **Checked by tests.** Properties and examples that exercise the contract.

Most production systems use a combination. The key is to be explicit about which constraints are guaranteed, which are checked, and which are merely hoped for.

## 8.3 Assertions: for programmer errors

An assertion states something that must be true if the code is correct. It is not a user-input check, and it is not a recovery mechanism.

```typescript
function assert(condition: unknown, message: string): asserts condition {
  if (!condition) {
    throw new Error(`Assertion failed: ${message}`);
  }
}

function average(values: readonly number[]): number {
  assert(values.length > 0, "average requires at least one value");
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}
```

`average([])` is a programmer error: the caller violated the function's contract. An assertion documents that and fails immediately, at the point of the mistake, instead of returning `NaN` and letting it propagate into a report, a database, or a payment.

Assertions are valuable when:

- the condition is expensive to check in production but cheap in development;
- the failure indicates a bug, not a valid runtime condition;
- continuing would produce corrupt or misleading results;
- the invariant is subtle and easy to break during maintenance.

They are harmful when:

- they check user input (use validation and return a useful error instead);
- they duplicate a check that is already enforced by types and cannot fail;
- they are used for control flow;
- they are left in hot paths where the cost is measurable and the condition is already guaranteed.

Development and production can differ. A common pattern is to keep assertions in development and testing, and remove or downgrade them in production, where the cost or the risk of crashing may be unacceptable. The choice depends on the domain: a payment ledger should probably fail hard; a video game may prefer to degrade gracefully.

![A bridge that sank because an uncovered flotation tank filled with water.](assets/interstate-90-bridge.png)

## 8.4 Validation at the boundary

External input is untrusted until proven otherwise: HTTP bodies, environment variables, files, messages, third-party APIs, and user input. The **barricade** principle says: validate at the boundary, convert to a trusted internal type, and let the interior assume validity.

```typescript
interface UserInput {
  readonly email: string;
  readonly age: number;
}

function parseUser(input: unknown): UserInput {
  if (typeof input !== "object" || input === null) {
    throw new TypeError("user must be an object");
  }
  const record = input as Record<string, unknown>;
  const email = record.email;
  const age = record.age;
  if (typeof email !== "string" || !email.includes("@")) {
    throw new TypeError("email must be a valid address");
  }
  if (typeof age !== "number" || !Number.isInteger(age) || age < 0) {
    throw new TypeError("age must be a non-negative integer");
  }
  return { email, age };
}
```

After `parseUser`, the rest of the system can rely on `UserInput`. The validation code is ugly, explicit, and concentrated in one place—which is exactly what you want. The alternative, scattering `if (input.email)` checks through the domain, spreads distrust everywhere and still misses cases.

In TypeScript, the boundary is also where `unknown` belongs. `unknown` forces narrowing; `any` lets invalid data flow inward with no evidence. A schema library can generate the parser, but the design principle is the same: **parse, don't validate**—turn untrusted data into a typed value once, at the edge.

![Separating code that handles dirty data from code that handles clean data.](assets/dirty-and-clean-data.png)

## 8.5 Exceptions

Exceptions are the default failure mechanism in TypeScript and JavaScript. They have real advantages:

- They separate the happy path from error handling.
- They propagate automatically, so intermediate layers need not know about failures they cannot handle.
- They carry stack traces and context.

And real costs:

- They are invisible in a function's type signature.
- They can be caught too broadly, hiding bugs.
- They make control flow harder to follow.
- They interact badly with resource cleanup if not handled carefully.
- They encourage "throw something and let someone else deal" rather than designing a response.

```typescript
interface Money { format(): string; subtract(other: Money): Money; readonly minorUnits: number }
interface Account { readonly balance: Money; debit(amount: Money): void }

class InsufficientFundsError extends Error {
  constructor(readonly shortfall: Money) {
    super(`Insufficient funds: short by ${shortfall.format()}`);
    this.name = "InsufficientFundsError";
  }
}

function withdraw(account: Account, amount: Money): void {
  if (amount.minorUnits <= 0) throw new RangeError("amount must be positive");
  if (account.balance.minorUnits < amount.minorUnits) {
    throw new InsufficientFundsError(amount.subtract(account.balance));
  }
  account.debit(amount);
}
```

Guidelines:

- **Throw for exceptional conditions, not ordinary branching.** A missing optional field is not exceptional; a violated invariant is.
- **Use specific error classes** so callers can distinguish failures without parsing messages.
- **Never swallow.** An empty `catch` is a bug with a silent mode. If you log and continue, say why and what state you are in.
- **Clean up with `finally`.** Resources must be released on every path.
- **Do not use exceptions for expected control flow** in hot paths or in APIs where callers routinely need the failure value.
- **Preserve context.** Wrap errors with the operation and inputs that failed, while keeping the cause.

```typescript
interface Invoice { readonly id: string }
declare function saveInvoice(invoice: Invoice): Promise<void>;
const invoice: Invoice = { id: "inv_1007" };

try {
  await saveInvoice(invoice);
} catch (error) {
  throw new Error(`Failed to save invoice ${invoice.id}`, { cause: error });
}
```

The `cause` option preserves the original error for logs and debugging while adding the context a caller needs.

![Exception handling repeated in every handler.](assets/duplicated-exception-handling.jpg){width=92%}

![Exception handling aggregated in one dispatcher.](assets/aggregated-exception-handling.jpg){width=90%}

## 8.6 Result types

A result type makes failure explicit in the return type:

```typescript
class Money {
  constructor(readonly cents: number, readonly currency: string) {}
  static of(cents: number, currency: string): Money { return new Money(cents, currency); }
}

interface Account {
  readonly balanceCents: number;
  debitCents(cents: number): void;
}

type Result<T, E> =
  | { readonly ok: true; readonly value: T }
  | { readonly ok: false; readonly error: E };

type WithdrawalError =
  | { kind: "invalid-amount" }
  | { kind: "insufficient-funds"; shortfallCents: number };

function withdraw(account: Account, cents: number): Result<Money, WithdrawalError> {
  if (!Number.isInteger(cents) || cents <= 0) {
    return { ok: false, error: { kind: "invalid-amount" } };
  }
  if (cents > account.balanceCents) {
    return {
      ok: false,
      error: { kind: "insufficient-funds", shortfallCents: cents - account.balanceCents },
    };
  }
  account.debitCents(cents);
  return { ok: true, value: Money.of(account.balanceCents, "USD") };
}
```

The caller must handle both branches; the compiler enforces it. Errors become data: they can be mapped, logged, tested, and returned over an API without exception plumbing.

The cost is verbosity. Every call site needs a branch, and composing result-returning functions requires helpers (`map`, `flatMap`, `unwrapOr`). In TypeScript, exceptions remain more ergonomic for truly exceptional conditions; result types shine for expected domain failures that callers routinely handle.

A practical split:

- **Result types** for domain operations whose failure is part of normal use (validation, payments, reservations).
- **Exceptions** for programming errors, infrastructure failures, and conditions the caller cannot meaningfully handle.
- **Assertions** for invariants that should never be violated.

## 8.7 Define errors out of existence

Some errors exist only because the API chose to define them. A powerful design move is to redefine the operation so the "error" becomes a normal, well-defined result.

```typescript
// Error: throws when the range is out of bounds.
function substring(text: string, start: number, end: number): string {
  if (start < 0 || end > text.length || start > end) {
    throw new RangeError("invalid range");
  }
  return text.slice(start, end);
}

// Defined: clamps the range and returns the overlap.
function substringClamped(text: string, start: number, end: number): string {
  const s = Math.max(0, Math.min(start, text.length));
  const e = Math.max(s, Math.min(end, text.length));
  return text.slice(s, e);
}
```

Other examples:

- **Delete a file that does not exist:** treat "already absent" as success (idempotent delete) when the caller's goal is "ensure absent."
- **Remove an item from a collection:** removing a missing item can be a no-op if the postcondition is "item is not present."
- **Set a property to its current value:** no-op rather than an error.
- **Look up a missing key with a default:** return the default instead of throwing, when a default is meaningful.

Defining errors out of existence simplifies callers and removes entire classes of failure. But it is not always appropriate:

- If the caller needs to know that something did not happen (a payment was not applied, a record was not found), collapsing the distinction loses information.
- If the "sensible default" is a policy decision the module has no right to make, the error should surface.
- If silently ignoring the condition could corrupt data or hide a bug, do not define it away.

The test: **does the caller's goal have a well-defined outcome for every input?** If yes, define it. If the caller must distinguish, keep the distinction.

## 8.8 Fail fast, but fail meaningfully

A program that continues after an unrecoverable error is a program that produces wrong results with confidence. Continuing with a corrupted data structure, a half-written file, or an inconsistent cache turns a local failure into a systemic one.

**Fail fast** means:

- detect the violation as close to its origin as possible;
- stop the operation (or the process) rather than continuing with invalid state;
- preserve enough evidence to diagnose the cause;
- do not catch an error you cannot handle.

This is not the same as crashing on every unexpected input. External input should be validated and rejected gracefully. Fail-fast applies to **internal invariants and unrecoverable states**—the situations where continuing would be a lie.

The practical rule:

| Situation | Response |
|-----------|----------|
| Invalid user input | Validate, return actionable error |
| Expected domain failure | Result type or typed exception, handled by caller |
| Transient environmental failure | Retry with backoff, circuit breaker, fallback |
| Programming error / broken invariant | Assert, log context, stop the operation |
| Corruption that cannot be repaired | Stop, preserve state, alert |

## 8.9 Resource ownership

Every resource—file handle, database transaction, lock, timer, subscription—must have a clear owner and a deterministic release path.

```typescript
interface Transaction {
  commit(): Promise<void>;
  rollback(): Promise<void>;
}
interface Database { begin(): Promise<Transaction> }

async function withTransaction<T>(
  db: Database,
  work: (tx: Transaction) => Promise<T>,
): Promise<T> {
  const tx = await db.begin();
  try {
    const result = await work(tx);
    await tx.commit();
    return result;
  } catch (error) {
    await tx.rollback();
    throw error;
  }
}
```

The `try/finally` shape guarantees release on success and failure (with an explicit rollback in the catch). For synchronous resources, `finally` is enough:

```typescript
interface FileHandle { readAll(): string; close(): void }
declare function openFile(path: string): FileHandle;

function readConfig(path: string): string {
  const handle = openFile(path);
  try {
    return handle.readAll();
  } finally {
    handle.close();
  }
}
```

TypeScript 5.2+ supports explicit resource management with `using` and `Symbol.dispose`, which sugar the same pattern:

```typescript
class FileHandle {
  [Symbol.dispose](): void {
    this.close();
  }
  close(): void { /* ... */ }
  readAll(): string { return ""; }
}

function readConfigWithUsing(open: () => FileHandle): string {
  using handle = open();
  return handle.readAll();
}
```

Ownership rules worth writing down:

- The function that opens a resource closes it, unless the interface explicitly transfers ownership.
- Acquire in one order, release in reverse order.
- Do not return a resource from a function without documenting who closes it.
- For async code, `try/finally` still applies; `await` does not suspend cleanup.
- Locks must be released even if the protected work throws.

## 8.10 The three-way debate

Error handling is one of the places where experienced designers genuinely disagree, and the disagreement is instructive.

**Position 1: Define errors out of existence.** Redesign operations so that common failures become defined results. Fewer exceptions, simpler callers, fewer branches. Risk: hiding information the caller needs and making failures invisible.

**Position 2: Fail fast; dead programs tell no lies.** Do not continue with corrupt state. Assert invariants, crash on unrecoverable errors, and fix the bug rather than papering over it. Risk: treating expected domain failures as crashes, and producing brittle systems.

**Position 3: Defend and recover.** Validate at boundaries, handle expected errors, use exceptions or result codes, and keep the system running. Risk: error-handling code that dwarfs the happy path, swallowed errors, and inconsistent state.

These positions are not mutually exclusive; they apply to different classes of failure:

| Failure class | Define out | Fail fast | Defend/recover |
|---------------|-----------|-----------|----------------|
| Expected domain failure | Often | No | Yes, explicitly |
| Invalid external input | No | No | Yes, at boundary |
| Programmer error | No | Yes | Only in development |
| Transient environment failure | Sometimes (defaults) | No | Yes (retry/fallback) |
| Corruption / broken invariant | No | Yes | No |

The mature approach is to **name the class first**, then choose the mechanism. Most error-handling arguments are really arguments about classification: one designer is thinking of a missing optional value, another of a corrupted ledger. They are both right, about different rows of the table.

## Summary

- Classify failures before choosing a mechanism: programmer error, expected domain failure, environmental failure, corruption, and invalid input have different correct responses.
- Contracts (preconditions, postconditions, invariants) belong in the interface, not only in the implementation.
- Assertions check programmer assumptions; validation checks external input; do not confuse them.
- Exceptions are convenient but invisible in types; result types make expected failures explicit at the cost of verbosity.
- Defining errors out of existence simplifies callers when every input has a meaningful outcome; it is dangerous when the caller must distinguish outcomes.
- Fail fast on broken invariants and unrecoverable state; recover deliberately from expected and transient failures.
- Validate at boundaries, then trust internal data.
- Give every resource an owner and a deterministic release path.

## Exercises

1. **Classify your failures.** List ten error paths in a system you know. Classify each using the table in §8.1. How many are handled with a mechanism appropriate to their class? Which are mismatched?
2. **Write a contract.** Choose a public method and write its preconditions, postconditions, and invariants. Then check whether the implementation enforces them and whether the type system could enforce any of them.
3. **Assertion or validation?** Find three `if (...) throw` checks. For each, decide whether it is a programmer error (assertion) or external input (validation), and move it to the right layer.
4. **Define it away.** Take an API that throws for a common condition. Redesign one operation so the condition becomes a defined result. What information is lost? Is that acceptable?
5. **Result vs. exception.** Implement the same operation twice: once with a `Result` type and once with exceptions. Compare the call sites. Which is clearer for this domain, and why?
6. **Resource audit.** Find a resource that is acquired and released manually. Rewrite it with `try/finally` or `using`. What happens on the error path in the original?
7. **Error message quality.** Find a production error message that was unhelpful. Rewrite it to include the operation, the relevant input, and the next action. What context should be logged versus shown to the user?
