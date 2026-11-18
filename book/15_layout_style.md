# 15. Layout, Style, and Obvious Code

Most of the code a program contains is not clever. It is ordinary: assignments, checks, loops, calls. The difference between a codebase that is pleasant to work in and one that is exhausting has less to do with advanced techniques than with whether ordinary code is *obvious*.

Obviousness is not a property of a single line. It emerges from layout, naming, consistency, and the absence of surprises. This chapter is about building it deliberately.

## Learning objectives

- Explain what layout communicates and why consistency matters more than any particular style.
- Format code so that structure is visible at a glance.
- Apply tests of obviousness to ordinary code.
- Distinguish simplicity from cleverness, and recognize the cost of each clever trick.
- Use whitespace, grouping, and ordering to express relationships.
- Automate style so that humans can review substance.

## 15.1 What layout is for

Layout is visual structure. It shows which lines belong together, which are subordinate, where a block begins and ends, and what the eye should see first.

A reader parses code in two passes. The first is **visual**: shapes, indentation, blank lines, alignment. The second is **semantic**: names, types, control flow. Good layout makes the first pass do useful work, so the second can focus on meaning. Bad layout forces the reader to reconstruct structure from syntax, which is slow and error-prone.

This is why the specific style matters less than consistency. Any reasonable style becomes invisible after a week. An inconsistent style never does: every file becomes a small puzzle, and the reader must decide anew whether this project uses two-space indentation, where braces go, and whether blank lines separate clauses or paragraphs.

> **Consistency is the only style rule that matters at scale.** Pick a style, encode it in a formatter, and stop discussing it in review.

## 15.2 The mechanics

A formatter handles the mechanical decisions. The choices worth making deliberately are about *grouping*.

**Blank lines separate ideas.** A blank line between two statements says "these are different thoughts." No blank line says "these belong together." Use blank lines:

- between logical sections of a function;
- between declarations and the code that uses them;
- between members of a class when they serve different purposes;
- around multi-line constructs (a nested function, a long object literal) so they do not blend into their surroundings.

Do not use blank lines:

- inside a tight sequence that forms one idea;
- to compensate for a function that should be split;
- in patterns that make related lines look unrelated.

```typescript
interface OrderLine { readonly unitCents: number; readonly quantity: number }
interface Customer { readonly isActive: boolean }
interface Order {
  readonly id: string;
  readonly lines: readonly OrderLine[];
  readonly taxRate: number;
  readonly customer: Customer;
}
interface Inventory { reserve(lines: readonly OrderLine[]): void }
interface Receipt { readonly orderId: string; readonly chargedCents: number }

// Grouped by idea: validate, compute, persist.
export function placeOrder(order: Order, inventory: Inventory): Receipt {
  if (order.lines.length === 0) throw new Error("Order has no lines");
  if (!order.customer.isActive) throw new Error("Customer is inactive");

  const totalCents = order.lines.reduce(
    (sum, line) => sum + line.unitCents * line.quantity,
    0,
  );
  const taxedCents = Math.round(totalCents * (1 + order.taxRate));

  inventory.reserve(order.lines);
  return { orderId: order.id, chargedCents: taxedCents };
}
```

```typescript
interface OrderLine { readonly unitCents: number; readonly quantity: number }
interface Customer { readonly isActive: boolean }
interface Order {
  readonly id: string;
  readonly lines: readonly OrderLine[];
  readonly taxRate: number;
  readonly customer: Customer;
}
interface Inventory { reserve(lines: readonly OrderLine[]): void }
interface Receipt { readonly orderId: string; readonly chargedCents: number }

// Ungrouped: every line looks equally related to every other.
export function placeOrder(order: Order, inventory: Inventory): Receipt {
  if (order.lines.length === 0) throw new Error("Order has no lines");
  const totalCents = order.lines.reduce((sum, line) => sum + line.unitCents * line.quantity, 0);
  if (!order.customer.isActive) throw new Error("Customer is inactive");
  const taxedCents = Math.round(totalCents * (1 + order.taxRate));
  inventory.reserve(order.lines);
  return { orderId: order.id, chargedCents: taxedCents };
}
```

The second version is not wrong; it is harder to scan. The validation, the arithmetic, and the side effect are interleaved, so the reader must classify each line.

**Line length** should keep a line readable without horizontal scrolling. A common limit is 80–120 characters. Long lines are usually a symptom: either an expression is too dense, or names are too long, or a call has too many arguments. Wrapping is a mitigation, not a fix.

**Indentation** should reflect nesting exactly. A block that is visually flat but logically nested is a bug waiting to happen; a block that is visually nested but logically flat wastes the reader's attention.

**Alignment** is controversial. Aligning similar declarations can make a table visually clear:

```typescript
const subtotalCents = 12_500;
const taxCents      = 2_500;
const shippingCents = 500;
```

But alignment breaks when a name changes length, and it can imply a relationship that does not exist. Prefer alignment only for genuine tabular data (test tables, constant maps), and let the formatter handle the rest.

## 15.3 Ordering

Within a file or a class, order conveys importance and dependency.

Useful conventions:

- **Public before private.** A reader should see the interface before the implementation.
- **High-level before low-level.** Put the main flow first, then the helpers it calls, so the file reads top-down.
- **Constants before use.** A reader should know the policy before seeing where it applies.
- **Related things together.** Field declarations, then constructor, then public methods, then private helpers.
- **Imports grouped and sorted.** Standard library, third-party, local. A stable order makes diffs readable.

```typescript
interface Order { readonly subtotalCents: number; readonly discountCents: number }
interface Money {
  subtract(other: Money): Money;
}
interface PriceLookup { priceOf(sku: string): Money }
declare function money(cents: number): Money;

// A file that reads top-down: the exported behavior first, helpers after.
export function quote(order: Order, prices: PriceLookup): Money {
  const subtotal = subtotalOf(order);
  const discount = discountFor(order);
  return subtotal.subtract(discount);
}

function subtotalOf(order: Order): Money { return money(order.subtotalCents); }
function discountFor(order: Order): Money { return money(order.discountCents); }
```

The reader who only wants to know what `quote` does can stop after ten lines. The reader who needs details continues downward, in the order the calls appear.

![Well-organized code: the boxes around related sections do not overlap.](assets/organized-code-blocks.png)

![Poorly organized code: related sections overlap.](assets/disorganized-code-blocks.png)

## 15.4 Tests of obviousness

Obvious code passes a set of simple tests:

**Can you tell what it does without running it?** If understanding requires stepping through a debugger or evaluating an expression in a REPL, the code is not obvious.

**Does it do what it looks like it does?** A function named `validate` that also writes to the database fails this test. So does an `if` condition with a side effect.

**Is there exactly one reasonable interpretation?** Ambiguity is a design smell. `process(data, false)` has at least two plausible readings; `retry({ maxAttempts: 3 })` has one.

**Can you find all the places that matter?** If changing a constant requires a global search, or if a value is computed in three places, the code is not obvious about its dependencies.

**Would a new team member be surprised?** Surprise is the most reliable signal. If a competent developer says "wait, why does it do that?", the code has failed, even if it is correct.

> **Obviousness is a property of the reader's model, not the writer's.** The writer knows why every line is there. The test is whether someone else can reconstruct that why from the code and its comments.

## 15.5 Simplicity versus cleverness

Clever code is code that demonstrates the author's skill. Simple code is code that does not require the reader to have that skill.

```typescript
interface Item { readonly category: string; readonly id: string }
declare const items: readonly Item[];

// Clever: a one-liner that requires parsing three language features.
const grouped = items.reduce<Record<string, Item[]>>((acc, item) => (
  (acc[item.category] ??= []).push(item), acc
), {});
```

```typescript
interface Item { readonly category: string; readonly id: string }
declare const items: readonly Item[];

// Simple: the intent is visible at a glance.
function groupByCategory(items: readonly Item[]): Map<string, Item[]> {
  const groups = new Map<string, Item[]>();
  for (const item of items) {
    const group = groups.get(item.category) ?? [];
    group.push(item);
    groups.set(item.category, group);
  }
  return groups;
}
```

The second version is longer and less "elegant." It is also trivially correct, easy to extend, and readable by anyone who knows a `for` loop. The first requires the reader to parse the comma operator, logical assignment, and a cast—all at once.

Cleverness is not always wrong. There are places where a dense expression is the clearest way to say a mathematical fact:

```typescript
declare const dx: number;
declare const dy: number;

const distance = Math.hypot(dx, dy);
```

The line is "clever" only if the reader does not know `Math.hypot`. Familiarity makes concision readable; novelty makes it costly. The question is always: **is this compression familiar to the reader, or does it require decoding?**

Guidelines for choosing simple over clever:

- Prefer a named intermediate over a nested expression.
- Prefer a loop over a clever `reduce` when the loop is clearer.
- Prefer an explicit condition over a bit trick unless the bit trick is the domain.
- Prefer readability at the call site over brevity at the definition.
- Do not optimize for the writer's typing time; optimize for the reader's comprehension time.

## 15.6 Comments in layout

Comments are part of layout when they act as headings or annotations. A short comment can group a long function into readable sections:

```typescript
interface Invoice {
  readonly status: "open" | "closed";
  readonly balanceCents: number;
}
interface Payment { readonly receivedAt: Date; readonly cents: number }
interface Settlement { readonly remainingCents: number }
declare function allocate(
  payments: readonly Payment[],
  balanceCents: number,
): Settlement;

export function settleInvoice(invoice: Invoice, payments: readonly Payment[]): Settlement {
  // Validation
  if (invoice.status !== "open") throw new Error("Invoice is not open");
  if (payments.length === 0) throw new Error("No payments to settle");

  // Allocation: oldest payment first.
  const sorted = [...payments].sort((a, b) => a.receivedAt.getTime() - b.receivedAt.getTime());
  const applied = allocate(sorted, invoice.balanceCents);

  // Postconditions
  if (applied.remainingCents < 0) throw new Error("Over-allocated");
  return applied;
}
```

Section comments are useful when a function has several distinct phases. They are a warning when they appear in every function: if every ten lines need a heading, the function probably wants to be several functions.

Comments used as alignment—trailing comments in a column—are fragile. They break when the code changes, and they often restate the line. Prefer a comment on its own line above the thing it explains.

## 15.7 Tooling

Formatting is a solved problem; treat it that way.

- **Use a formatter** (Prettier or equivalent) with a committed configuration. Run it on save and in CI.
- **Use a linter** for rules that a formatter cannot express: unused variables, floating promises, unsafe `any`, inconsistent imports.
- **Do not debate style in review.** If a style question recurs, encode the answer in the tool configuration and move on.
- **Keep diffs clean.** Format-on-save plus a stable configuration means a diff contains changes in behavior, not changes in whitespace.
- **Format before refactoring, not during.** A commit that both reformats and changes logic is unreviewable.

Tooling frees review attention for the questions that matter: Is the design right? Is the contract clear? Are the edge cases handled? Is the test meaningful? Those questions cannot be automated.

A caution: tools enforce *syntax*, not *taste*. A formatter will happily produce beautifully formatted code with terrible names and four hundred lines of nesting. Style is necessary, not sufficient.

## 15.8 Style as a social artifact

A codebase's style is a set of conventions a team agrees to follow so that individuals do not have to negotiate every line. That makes style a social artifact as much as a technical one.

Practical consequences:

- **New code should match the surrounding code**, even if you would have chosen differently. Consistency beats personal preference.
- **Changing a convention is a project-level decision**, not a drive-by edit. If the team wants to switch from four spaces to two, that is one commit that touches everything, reviewed as a formatting change.
- **Style guides should explain why**, briefly, so that the rules can be applied to cases the guide does not cover.
- **Automation is a kindness.** A formatter removes a class of comments from review ("please add a space here") that no one enjoys writing or receiving.

The goal is not uniformity for its own sake. It is to make the codebase feel like one author wrote it, so that the reader's attention goes to the problem rather than to the idiosyncrasies of whoever touched the file last.

## Summary

- Layout communicates structure visually; consistency matters more than the specific style chosen.
- Use blank lines to separate ideas, indentation to show nesting, and ordering to show importance and dependency.
- Obvious code can be understood without running it, does what it looks like, has one reasonable interpretation, and does not surprise a competent reader.
- Prefer simple code to clever code: name intermediates, use explicit loops when they are clearer, and optimize for comprehension rather than typing.
- Section comments help long functions; if every function needs headings, split it.
- Automate formatting and linting so review can focus on design, contracts, and tests.
- Style is a team convention; new code should match its surroundings, and changes to convention are project decisions.

## Exercises

1. **Regroup a function.** Take a function you wrote recently and insert blank lines at the boundaries between ideas. Does the grouping reveal that the function should be split?
2. **Obviousness audit.** Pick a module you have never read. For each function, answer the five tests in §15.4 without running the code. Where did you have to guess?
3. **De-clever.** Find a dense expression (a chained `reduce`, a nested ternary, a bit trick). Rewrite it as named steps or a loop. Measure the line-count change against the readability change.
4. **Ordering review.** Open a file and check whether it reads top-down: public API, then main flow, then helpers. If not, reorder it. Did anything become clearer?
5. **Diff hygiene.** Find a recent commit that mixed formatting and behavior. Split it conceptually: which lines were style, which were substance? What would have made review easier?
6. **Convention proposal.** Write a short style guide for a TypeScript project: formatting (delegated to a tool), ordering, blank-line use, comment placement, and one rule about simplicity. Include a rationale for each.
