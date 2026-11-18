# 13. Control Flow

Control flow is where a program's logic becomes visible. A reader should be able to trace the path from input to output without holding a mental stack of negations, nested conditions, and loop indices. When control flow is clear, correctness is easier to argue and bugs are easier to find. When it is tangled, every change is a gamble.

This chapter covers the construction-level decisions that shape control flow: ordering, conditionals, loops, nesting, early exits, recursion, and the use of tables and dispatch.

## Learning objectives

- Organize straight-line code around explicit dependencies.
- Write conditionals that make the nominal path clear and handle errors deliberately.
- Design loops with obvious boundaries, invariants, and termination.
- Reduce deep nesting with guard clauses, extraction, and dispatch.
- Decide when recursion is appropriate and when it is a liability.
- Recognize control-flow complexity and measure it without worshipping the metric.

## 13.1 Straight-line code

Straight-line code has no branches or loops. Its main design issue is **ordering**: some statements depend on others, and the reader must see those dependencies.

```typescript
interface Line { readonly amountCents: number }
const lines: readonly Line[] = [{ amountCents: 1_250 }, { amountCents: 800 }];
const taxRate = 0.2;

const subtotal = lines.reduce((sum, line) => sum + line.amountCents, 0);
const tax = Math.round(subtotal * taxRate);
const total = subtotal + tax;

// The dependency is obvious: total uses tax, tax uses subtotal.
```

Guidelines:

- **Put related statements together.** Do not interleave the computation of `total` with unrelated setup.
- **Make dependencies visible.** Use names that show the relationship (`subtotal`, `tax`, `total`) and avoid reusing a variable for a different meaning.
- **Use housekeeping variables when they clarify.** A well-named intermediate (`shippingCents`, `discountCents`) is better than a single dense expression.
- **Avoid long sequences of mutations to the same variable.** They force the reader to simulate the state.

A sequence with unclear dependencies is a bug waiting to happen:

```typescript
interface Line { readonly amountCents: number }
const lines: readonly Line[] = [{ amountCents: 1_250 }, { amountCents: 800 }];
const taxRate = 0.2;
const discountCents = 500;

let total = 0;
for (const line of lines) total += line.amountCents;
total = total * (1 + taxRate);
total = total - discountCents;
total = Math.max(0, total);
```

This is not wrong, but each line mutates the same variable and the reader must track its meaning at every step. Named intermediates make the calculation self-explanatory:

```typescript
interface Line { readonly amountCents: number }
const lines: readonly Line[] = [{ amountCents: 1_250 }, { amountCents: 800 }];
const taxRate = 0.2;
const discountCents = 500;

const subtotalCents = lines.reduce((sum, line) => sum + line.amountCents, 0);
const taxCents = Math.round(subtotalCents * taxRate);
const discountedCents = Math.max(0, subtotalCents + taxCents - discountCents);
```

## 13.2 Conditionals

### Order the branches for the reader

For a simple `if/else`, decide whether the nominal case or the exceptional case should come first.

```typescript
interface Order { readonly isPaid: boolean }
interface User { readonly isActive: boolean }

declare function ship(order: Order): void;
declare function activeView(user: User): string;
declare function inactiveView(user: User): string;

function shipOrder(order: Order): void {
  // Error first: the happy path is unindented and easy to scan.
  if (!order.isPaid) {
    throw new Error("Order is not paid");
  }
  ship(order);
}

function view(user: User): string {
  // Nominal first: the common case reads first, the fallback follows.
  if (user.isActive) {
    return activeView(user);
  }
  return inactiveView(user);
}
```

Both are valid. The principle is to make the **common path** clear and to avoid forcing the reader through a negated condition to reach it. If the error case is rare and short, handling it first with a guard clause often reads better.

### Keep conditions simple

Boolean expressions become unreadable when they combine several negations and precedence rules:

```typescript
interface User {
  readonly role: "admin" | "member";
  readonly isActive: boolean;
  readonly isSuspended: boolean;
}

function hasUnrestrictedAccess(user: User): boolean {
  return !(user.role !== "admin" && !user.isActive) || user.isSuspended;
}
```

Extract named booleans or a predicate:

```typescript
interface User {
  readonly role: "admin" | "member";
  readonly isActive: boolean;
  readonly isSuspended: boolean;
}

function canAccess(user: User): boolean {
  const permitted = user.role === "admin" || user.isActive;
  return permitted && !user.isSuspended;
}
```

Guidelines:

- Prefer positive conditions (`isActive` over `!isInactive`).
- Name complex subexpressions.
- Avoid side effects in conditions (`if (user = loadUser())` is a classic bug).
- Use parentheses when mixing `&&` and `||`.
- Remember short-circuit evaluation: `a && b()` does not call `b` if `a` is false; do not rely on it for required side effects.

### Braces and empty branches

Always use braces for multi-line bodies, and preferably for all bodies. A missing brace after a refactor is a classic defect. Avoid empty branches: `if (condition) { /* do nothing */ } else { ... }` is a sign that the condition should be inverted.

### Chains and switches

For multi-way decisions, order branches by frequency or logical progression, and make the default explicit.

```typescript
type OrderStatus = "draft" | "placed" | "paid" | "shipped" | "cancelled";

function shippingLabel(status: OrderStatus): string {
  switch (status) {
    case "draft":
      return "Draft";
    case "placed":
    case "paid":
      return "Processing";
    case "shipped":
      return "Shipped";
    case "cancelled":
      return "Cancelled";
    default: {
      const exhaustive: never = status;
      throw new Error(`Unhandled status: ${exhaustive}`);
    }
  }
}
```

The `never` check turns a missing case into a compile error when the union grows. That is control flow designed with the type system rather than against it.

When a switch selects behavior by type and grows frequently, consider polymorphic dispatch or a table (Chapter 20). A switch with twenty branches is a sign that the decision belongs somewhere else.

![Ordering boolean tests along a number line.](assets/number-line-ordering.png)

## 13.3 Loops

Loops concentrate several kinds of complexity: boundaries, indices, termination, and state.

### Choose the simplest loop

```typescript
interface Item { readonly id: string }
interface User { readonly id: string; readonly isActive: boolean }
declare function handleItem(item: Item): void;

// Counted loop: use when the index matters.
function counted(items: readonly Item[]): void {
  for (let i = 0; i < items.length; i++) {
    handleItem(items[i]);
  }
}

// Iteration: use when only the element matters.
function iterated(items: readonly Item[]): void {
  for (const item of items) {
    handleItem(item);
  }
}

// Functional: use when transforming a collection.
function activeUsers(users: readonly User[]): User[] {
  return users.filter((user) => user.isActive);
}
```

Prefer `for...of` over index loops when the index is not needed. Prefer `map`/`filter`/`reduce` when the operation is a transformation. Use a `while` loop when the termination condition is not a simple count.

### Boundaries and off-by-one errors

The most common loop defect is a boundary error:

```typescript
interface Item { readonly id: string }
declare function handleItem(item: Item): void;

function processAll(items: readonly Item[]): void {
  // Bug: reads one past the end.
  for (let i = 0; i <= items.length; i++) {
    handleItem(items[i]);
  }
}
```

Make the boundary explicit and test it:

- empty collection;
- one element;
- exactly at the boundary;
- one past the boundary.

For ranges, write the comparison in the direction that matches the language's convention (`i < length` for zero-based arrays). If the loop is more complex, write the invariant as a comment:

```typescript
interface Item { readonly id: string }
declare function handleItem(item: Item): void;

function processAllCorrectly(items: readonly Item[]): void {
  // Invariant: 0 <= i <= items.length; items[0..i) have been processed.
  for (let i = 0; i < items.length; i++) {
    handleItem(items[i]);
  }
}
```

### Termination

Every loop must terminate. For `for` loops over a finite collection, this is usually obvious. For `while` loops, identify the measure that decreases (or the condition that becomes false) and make it explicit.

```typescript
declare function shouldRetry(): boolean;

function retryLoop(): number {
  let attempt = 0;
  let done = false;
  // Potential infinite loop: `attempt` is not incremented on this path,
  // so a persistent retry signal never reaches the cap.
  while (!done) {
    if (shouldRetry()) {
      continue;
    }
    attempt++;
    done = attempt >= 3;
  }
  return attempt;
}
```

Guard clauses and explicit progress checks help. In retry loops, cap the attempts and use a backoff.

### Loop state

Keep loop state local and minimal. A loop that mutates three variables declared outside it is hard to reason about. If the loop needs a complex accumulator, extract the body into a function that returns the next state.

### Nested loops

Nested loops multiply complexity and often hide an algorithmic problem (O(n²) where a map would be O(n)). Before writing a nested loop, ask:

- Can one collection be indexed in a `Map` or `Set`?
- Can the inner loop be extracted into a function?
- Is the nesting expressing a join, a search, or a Cartesian product?

## 13.4 Taming nesting

Deep nesting is the most reliable predictor of unreadable control flow. Each level adds a condition the reader must hold.

```typescript
interface Customer { readonly isActive: boolean }
interface Payment { readonly isAuthorized: boolean }
interface Order {
  readonly items: readonly string[];
  readonly customer?: Customer;
  readonly payment?: Payment;
}
type Result = { readonly ok: true } | { readonly ok: false; readonly reason: string };
declare function fulfill(order: Order): Result;

function processOrder(order: Order): Result {
  if (order.items.length > 0) {
    if (order.customer) {
      if (order.customer.isActive) {
        if (order.payment) {
          if (order.payment.isAuthorized) {
            return fulfill(order);
          } else {
            return { ok: false, reason: "payment not authorized" };
          }
        } else {
          return { ok: false, reason: "no payment" };
        }
      } else {
        return { ok: false, reason: "inactive customer" };
      }
    } else {
      return { ok: false, reason: "no customer" };
    }
  } else {
    return { ok: false, reason: "empty order" };
  }
}
```

Refactor with **guard clauses**:

```typescript
interface Customer { readonly isActive: boolean }
interface Payment { readonly isAuthorized: boolean }
interface Order {
  readonly items: readonly string[];
  readonly customer?: Customer;
  readonly payment?: Payment;
}
type Result = { readonly ok: true } | { readonly ok: false; readonly reason: string };
declare function fulfill(order: Order): Result;

function processOrder(order: Order): Result {
  if (order.items.length === 0) return { ok: false, reason: "empty order" };
  if (!order.customer) return { ok: false, reason: "no customer" };
  if (!order.customer.isActive) return { ok: false, reason: "inactive customer" };
  if (!order.payment) return { ok: false, reason: "no payment" };
  if (!order.payment.isAuthorized) return { ok: false, reason: "payment not authorized" };
  return fulfill(order);
}
```

The happy path is now a single line at the end; the failure conditions are explicit and flat. This is one of the highest-leverage refactorings in everyday code.

Other techniques:

- **Invert the condition** to turn an `if/else` into a guard.
- **Extract the body** into a function with a meaningful name.
- **Use a dispatch table** for multi-way branching.
- **Use a state machine** when the nesting encodes states and transitions.

## 13.5 Early returns and multiple exits

Multiple returns are a matter of context. In a short function with guard clauses, they improve clarity. In a long function with cleanup code, they can skip necessary work. The rule is not "one exit" but "no hidden exits that skip obligations."

In TypeScript, `try/finally` makes early returns safe for resources:

```typescript
interface FileHandle {
  readLine(): string | undefined;
  close(): void;
}
declare function openFile(path: string): FileHandle;

function readFirstLine(path: string): string | undefined {
  const handle = openFile(path);
  try {
    const line = handle.readLine();
    if (line === undefined) return undefined;
    return line.trim();
  } finally {
    handle.close();
  }
}
```

For loops, `break` and `continue` are fine when they make the exit condition clearer. Labeled breaks are rare; if you need one, consider extracting the loop into a function.

## 13.6 Recursion

Recursion is appropriate when the data or the algorithm is naturally recursive:

- trees and graphs;
- divide-and-conquer algorithms;
- parsing nested structures;
- backtracking.

Every recursive function needs:

1. **A base case** that returns without recursing.
2. **Progress** toward the base case on every path.
3. **A stack-depth budget** or an iterative fallback for deep inputs.

```typescript
interface TreeNode {
  readonly value: number;
  readonly children: readonly TreeNode[];
}

function sumTree(node: TreeNode): number {
  return node.value + node.children.reduce((sum, child) => sum + sumTree(child), 0);
}
```

Recursion is a liability when the depth is unbounded (user-supplied JSON, linked lists of unknown length) or when the recursive call is not structurally simpler. Convert to an explicit stack when depth is a risk.

![Recursion as a tool for problems with the right shape.](assets/recursion.png)

## 13.7 Exceptions as control flow

Exceptions are for exceptional conditions, not for ordinary branching. Using them for control flow makes the normal path invisible and the cost unpredictable.

```typescript
interface Item { matches(query: string): boolean }

function findByThrowing(items: readonly Item[], query: string): Item | undefined {
  // Using an exception to exit a loop: obscure and slow.
  try {
    for (const item of items) {
      if (item.matches(query)) throw item;
    }
  } catch (found) {
    return found as Item;
  }
  return undefined;
}
```

Use `find` instead. Conversely, do not catch an exception merely to return a default when the operation has a natural "not found" result; use a result type or an optional value.

## 13.8 Control-flow complexity

Cyclomatic complexity counts the number of independent paths through a routine: one plus the number of decision points. It is a useful **testability** indicator—a routine with ten branches needs at least ten path tests—but a poor design target. Code can have low cyclomatic complexity and still be incomprehensible (dense expressions, poor names), or high complexity and be clear (a flat dispatch table).

Use it to ask:

- Which routines have the most paths, and are they tested?
- Are the paths genuinely necessary, or is the routine doing several jobs?
- Can a table or polymorphism replace a branch?

Do not use it to set a hard limit. Complexity is a property of the reader's experience, not a count of keywords.

## 13.9 A refactoring example

Consider a function that computes a shipping estimate with nested conditions:

```typescript
interface Order {
  readonly weightKg: number;
  readonly destination: "domestic" | "international";
  readonly expedited: boolean;
  readonly subtotalCents: number;
}

function shippingCents(order: Order): number {
  if (order.weightKg > 0) {
    if (order.destination === "domestic") {
      if (order.expedited) {
        return 1500 + Math.ceil(order.weightKg) * 200;
      } else {
        return 500 + Math.ceil(order.weightKg) * 100;
      }
    } else {
      if (order.expedited) {
        return 4000 + Math.ceil(order.weightKg) * 500;
      } else {
        return 2000 + Math.ceil(order.weightKg) * 300;
      }
    }
  } else {
    return 0;
  }
}
```

The nesting hides a simple table. Refactor:

```typescript
interface Order {
  readonly weightKg: number;
  readonly destination: "domestic" | "international";
  readonly expedited: boolean;
  readonly subtotalCents: number;
}

const RATES = {
  domestic: {
    standard: { base: 500, perKg: 100 },
    expedited: { base: 1500, perKg: 200 },
  },
  international: {
    standard: { base: 2000, perKg: 300 },
    expedited: { base: 4000, perKg: 500 },
  },
} as const;

function shippingCents(order: Order): number {
  if (order.weightKg <= 0) return 0;
  const rate = order.expedited
    ? RATES[order.destination].expedited
    : RATES[order.destination].standard;
  return rate.base + Math.ceil(order.weightKg) * rate.perKg;
}
```

The table makes the policy visible, removes the nesting, and makes adding a new destination or speed a data change rather than a control-flow change. The behavior is identical.

![A direct-access table maps an index straight to its entry.](assets/direct-access-table.png)

## Summary

- Straight-line code should make dependencies and intermediate values explicit.
- Conditionals should make the nominal path clear, use positive logic, and handle errors deliberately; exhaustive switches turn missing cases into compile errors.
- Loops need obvious boundaries, termination, and minimal state; test empty, single, boundary, and past-boundary cases.
- Guard clauses and extraction are the most effective ways to reduce nesting.
- Multiple returns are fine when they clarify and do not skip obligations; `try/finally` protects resources.
- Recursion suits recursive structures but needs a base case, progress, and a depth budget.
- Do not use exceptions for ordinary control flow.
- Cyclomatic complexity is a testability diagnostic, not a design target.

## Exercises

1. **Flatten a function.** Find a routine with three or more levels of nesting. Refactor it with guard clauses and extraction. Compare the number of paths and the readability.
2. **Boundary tests.** Take a loop you wrote recently. Write tests for empty, one element, the last element, and one past the end. Did any fail?
3. **Condition clarity.** Find a complex boolean expression. Extract named booleans and rewrite it. Does the meaning change? If so, the original was ambiguous.
4. **Table it.** Find a switch or if-chain that maps inputs to values. Replace it with a lookup table and measure the difference in lines and branches.
5. **Recursion budget.** Find a recursive function. Determine its maximum depth for realistic inputs. Would an explicit stack be safer? Rewrite one case iteratively.
6. **Complexity review.** Run a cyclomatic-complexity tool on a module. Pick the highest routine and decide whether to split it, table it, or leave it. Justify with cohesion and testability, not the number alone.
