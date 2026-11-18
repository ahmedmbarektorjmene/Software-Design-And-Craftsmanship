# 18. Refactoring and the Care of Existing Code

Every system that survives is changed. The first version is written for the requirements of its first month; the tenth version must serve requirements nobody imagined. Between those points, the code either evolves or rots.

Refactoring is the disciplined practice of evolving structure without changing behavior. It is not rewriting, and it is not "cleaning up." It is a sequence of small, reversible transformations, each verified by tests, each leaving the system working.

## Learning objectives

- Explain why code decays even when no one makes a mistake.
- Recognize the smells that indicate structural problems.
- Apply a small set of high-leverage refactorings.
- Refactor safely with tests, small steps, and version control.
- Compare refactoring with rewriting and know when each is appropriate.
- Keep comments, tests, and surrounding code consistent through a change.
- Care for legacy code without demanding a rewrite as the price of progress.

## 18.1 Why code decays

Code does not decay because programmers are careless. It decays because the world changes and the code is asked to do things it was not designed for.

- **Requirements change.** A single-tenant system becomes multi-tenant; a batch job becomes a service; a local cache becomes a distributed one.
- **Knowledge changes.** The team learns the domain better, and the original abstractions no longer match.
- **People change.** The author leaves; the next reader cannot see the assumptions that were never written down.
- **Dependencies change.** A library's API shifts, a platform deprecates a feature.
- **Scale changes.** A design that works for a thousand records fails at a million.

None of these is a defect in the original code. Each is a mismatch between the code's implicit assumptions and the current world. Refactoring is how the code's structure catches up with its reality.

The alternative is **accretion**: each change is patched onto the existing structure, with a flag here and a special case there. The system keeps working, and each change becomes more expensive than the last. Eventually, the cost of a change exceeds the cost of a rewrite—or, more often, the organization simply stops changing the system and works around it.

## 18.2 Smells

A **code smell** is a surface symptom of a structural problem. It is not a bug; the code may be correct. It is a signal to look deeper.

| Smell | Symptom | Likely cause |
|-------|---------|--------------|
| Long function | More than a screen, many locals | Several responsibilities |
| Large class | Many fields and methods, low cohesion | Multiple abstractions merged |
| Long parameter list | Five or more parameters | Missing concept or object |
| Divergent change | One class changes for unrelated reasons | Mixed responsibilities |
| Shotgun surgery | One change touches many files | Knowledge scattered |
| Feature envy | A method uses another object's data more than its own | Behavior in the wrong place |
| Data clumps | The same group of variables travels together | Missing type |
| Primitive obsession | Strings and numbers where a type belongs | No domain types |
| Switch on type | A `switch` that grows with every new case | Missing polymorphism or dispatch |
| Duplicated code | The same logic in several places | Knowledge without an owner |
| Speculative generality | Hooks and parameters nobody uses | Anticipated change that never came |
| Comments explaining code | A comment that translates the implementation | Names or structure are unclear |
| Dead code | Unreachable branches, unused exports | Change without cleanup |
| Temporary field | A field set only in some operations | Object used as a record, not a type |

Smells cluster. A long function with a long parameter list and duplicated blocks usually has all three problems at once, and fixing one exposes the others.

> **Smells are heuristics, not laws.** Each one has legitimate exceptions. The question is always "what is the cost here, and what would removing it buy?"

## 18.3 A small set of high-leverage refactorings

Most refactoring value comes from a handful of transformations. Learn these well rather than memorizing a catalog.

### Extract function

Move a coherent block into a named function. The name replaces the block, and the block's details move out of the caller's view.

```typescript
interface Line { readonly unitCents: number; readonly quantity: number }

// Before: the caller must read the arithmetic to know what it is.
function invoiceTotal(lines: readonly Line[], taxRate: number): number {
  let subtotal = 0;
  for (const line of lines) {
    subtotal += line.unitCents * line.quantity;
  }
  const tax = Math.round(subtotal * taxRate);
  return subtotal + tax;
}
```

```typescript
interface Line { readonly unitCents: number; readonly quantity: number }

// After: the calculation is named and testable on its own.
function subtotalCents(lines: readonly Line[]): number {
  return lines.reduce((sum, line) => sum + line.unitCents * line.quantity, 0);
}

function invoiceTotal(lines: readonly Line[], taxRate: number): number {
  const subtotal = subtotalCents(lines);
  return subtotal + Math.round(subtotal * taxRate);
}
```

Extract when the block has a nameable purpose, when it is duplicated, or when it needs its own test. Do not extract merely to shorten a function; a one-use extraction with a vague name adds indirection without clarity.

### Inline

The inverse: replace a call with the body when the function adds no meaning, or when the abstraction has become wrong.

```typescript
interface Line { readonly unitCents: number; readonly quantity: number }

function subtotalCents(lines: readonly Line[]): number {
  return lines.reduce((sum, line) => sum + line.unitCents * line.quantity, 0);
}

// Before: a pass-through with a misleading name.
function processLines(lines: readonly Line[]): number {
  return subtotalCents(lines);
}
```

After inlining, callers call `subtotalCents` directly. The indirection disappears and the name tells the truth.

### Replace conditional with dispatch

When a conditional selects behavior by type or kind and grows with each new case, replace it with a table or polymorphic dispatch.

```typescript
interface Message { readonly body: string }
type Channel = "email" | "sms" | "push";
declare function sendEmail(message: Message): void;
declare function sendSms(message: Message): void;
declare function sendPush(message: Message): void;

// Before: every new channel edits two places.
function send(channel: "email" | "sms" | "push", message: Message): void {
  switch (channel) {
    case "email": return sendEmail(message);
    case "sms": return sendSms(message);
    case "push": return sendPush(message);
  }
}
```

```typescript
interface Message { readonly body: string }
type Channel = "email" | "sms" | "push";
declare function sendEmail(message: Message): void;
declare function sendSms(message: Message): void;
declare function sendPush(message: Message): void;

// After: adding a channel is one entry.
type Sender = (message: Message) => void;

const senders: Record<Channel, Sender> = {
  email: sendEmail,
  sms: sendSms,
  push: sendPush,
};

function send(channel: Channel, message: Message): void {
  senders[channel](message);
}
```

The table makes the policy visible and localizes the change. It is the right move when the set of cases is open or large; a `switch` with exhaustive checking is often better when the set is closed and small.

### Introduce a parameter object

When several parameters always travel together, they are a missing concept.

```typescript
interface Job { readonly id: string }

// Before: the same three values in every signature.
declare function schedule(job: Job, runAt: Date, retries: number, timeoutMs: number): void;
declare function cancel(job: Job, runAt: Date, retries: number): void;
```

```typescript
interface Job { readonly id: string }

// After: one concept, one type.
interface Schedule {
  readonly job: Job;
  readonly runAt: Date;
  readonly retries: number;
  readonly timeoutMs: number;
}

declare function schedule(schedule: Schedule): void;
declare function cancel(schedule: Pick<Schedule, "job" | "runAt" | "retries">): void;
```

### Move

Move a function or field to the object whose data it uses. **Feature envy** is the signal: a method that keeps reaching into another object should probably live there.

### Rename

Renaming is the cheapest refactoring and the most underused. A name that no longer matches the concept costs every future reader. Rename as soon as the mismatch is understood; the compiler and tests will find the call sites.

### Separate query from modifier

A function that both returns a value and changes state is hard to reason about (Chapter 12). Split it into a query and a command, or make the mutation explicit in the name.

## 18.4 Safety

Refactoring changes structure without changing behavior. Safety means being able to prove that claim—or at least to detect when it is false.

**Tests first.** A refactoring without tests is a rewrite with optimism. If the code has no tests, write characterization tests (Chapter 16) before changing structure.

**Small steps.** Each transformation should be small enough to verify by inspection and fast enough to run the suite after. A refactoring that takes a day has no safe checkpoint.

**One kind of change at a time.** Do not reformat and restructure in the same commit. Do not rename and change behavior. Mixed commits cannot be reviewed or reverted cleanly.

**Version control as a safety net.** Commit before a refactoring, commit after each verified step. A clean working tree means any step can be abandoned without losing unrelated work.

**Behavior-preserving discipline.** When a refactoring reveals a bug, note it and keep the behavior. Fix the bug in a separate, tested change. Mixing the two makes it impossible to tell which change altered behavior.

**Automated refactorings when available.** Rename, extract, move, and inline are mechanical; IDE support reduces the risk of missed call sites.

```typescript
// A refactoring checkpoint: the public behavior is pinned by tests.
interface PriceRule { apply(cents: number): number }

function applyRules(cents: number, rules: readonly PriceRule[]): number {
  return rules.reduce((value, rule) => rule.apply(value), cents);
}

// Refactor internals freely; the contract above is what the tests assert.
```

![Small changes tend to be more error-prone than larger ones.](assets/small-change-risk.png)

## 18.5 Refactoring versus rewriting

A rewrite is sometimes right, and it is chosen far more often than it should be.

**Arguments for rewriting:**

- The existing design is fundamentally wrong for the current requirements, not merely inconvenient.
- The technology is obsolete and unsupported.
- The code cannot be tested or understood at any reasonable cost.
- The system is small enough that a rewrite is cheaper than incremental change.

**Arguments against:**

- The existing code encodes years of bug fixes and edge cases that nobody remembers. A rewrite silently drops them.
- The rewrite always takes longer than estimated, and the old system must be maintained in parallel.
- The requirements will change during the rewrite, so the new system will be outdated on arrival.
- Big-bang cutovers concentrate risk into a single event.

The **strangler pattern** is the usual compromise: put a facade in front of the old system, route a slice of behavior to the new implementation, verify it in production, and grow the new system until the old one can be removed. It is slower per feature and far safer overall.

```typescript
// A routing facade: new code handles what it can; the legacy path remains.
interface Handler { handle(request: Request): Promise<Response> }

class MigratingHandler implements Handler {
  constructor(
    private readonly next: Handler,
    private readonly legacy: Handler,
    private readonly isMigrated: (request: Request) => boolean,
  ) {}

  handle(request: Request): Promise<Response> {
    return this.isMigrated(request)
      ? this.next.handle(request)
      : this.legacy.handle(request);
  }
}
```

The facade makes the migration observable: you can measure how much traffic still takes the legacy path and turn the flag off if the new path misbehaves.

## 18.6 Consistency with existing code

When you change existing code, match its conventions even if you would choose differently in a new file. Consistency within a file and a module is worth more than your preference.

- **Follow the local naming and formatting.** If the file uses `PascalCase` for constants, do not introduce `UPPER_SNAKE` in one function.
- **Use the existing abstractions.** If the codebase has a `Clock` interface, do not call `Date.now()` directly in your new function.
- **Extend patterns rather than replacing them mid-file.** A module with two competing patterns is harder to read than one with a single imperfect pattern.
- **Leave the campsite cleaner, but in small ways.** Fix a misleading name, add a missing test, delete a dead branch—without turning a feature change into a refactoring project.

If the existing convention is actively harmful, propose a project-wide change rather than a local exception. Local exceptions accumulate into inconsistency.

## 18.7 Comments, tests, and documentation during refactoring

A refactoring changes structure, and structure is what comments and tests refer to.

- **Interface comments** should survive if the interface survived. If you changed the contract, update the comment in the same change.
- **Implementation comments** may become obsolete when the implementation moves. Move the comment with the code; delete it if the code no longer needs it.
- **Tests** should require no change for a behavior-preserving refactoring. If a test breaks, either the refactoring changed behavior or the test was coupled to structure. Both are worth knowing.
- **Documentation and diagrams** that name modules, classes, or files must be updated. A stale architecture diagram is worse than none.

A useful check: **after the refactoring, does the code read as if it had always been written that way?** If there are remnants—a comment referring to a function that no longer exists, a test named after an old class—the job is not finished.

## 18.8 Refactoring legacy code

Legacy code is code that is hard to change because it is hard to understand and has no tests. The response is not a rewrite; it is a sequence of small, safe improvements.

1. **Understand the slice you need.** You rarely need to understand the whole system. Map the code path for the change you must make.
2. **Find a seam.** Identify a place where behavior can be observed or substituted: a function boundary, an interface, a configuration point.
3. **Characterize.** Write tests that pin current behavior, including the odd parts.
4. **Break dependencies.** Introduce parameters, extract pure functions, wrap external calls behind interfaces.
5. **Improve names and structure** in the area you are touching.
6. **Repeat.** Each change makes the next one easier.

The **boy scout rule**—leave the code better than you found it—works when it is scoped: improve the code you are already changing, not the whole file. A thousand small improvements over a year outperform one heroic rewrite that never ships.

![Ideal code, adapters, and the messy reality they isolate.](assets/ideal-and-messy-code.png)

![Refactoring legacy code as you touch it, one increment at a time.](assets/incremental-legacy-refactoring.png)

## Summary

- Code decays because the world changes, not because programmers are careless; refactoring is how structure catches up.
- Smells are symptoms, not laws: long functions, large classes, data clumps, feature envy, and duplicated knowledge all point to structural problems.
- A few transformations—extract, inline, rename, move, parameter object, dispatch table—cover most of the value.
- Refactor safely: tests first, small steps, one kind of change per commit, version control as a net.
- Rewrite only when the design is fundamentally wrong; otherwise use the strangler pattern and migrate incrementally.
- Match existing conventions, and keep comments, tests, and documentation consistent with the new structure.
- Improve legacy code in the slice you are already changing.

## Exercises

1. **Smell inventory.** List five smells in a module you own. For each, write the structural problem it indicates and one refactoring that would address it. Which two would you do first, and why?
2. **Extract with a test.** Take a block inside a long function, extract it, and write a test for the extracted function. Did the extraction require any new parameters? What does that tell you about the block's dependencies?
3. **Replace a growing switch.** Find a `switch` or `if` chain that selects behavior by type. Replace it with a dispatch table or polymorphic handlers. How many places must change to add a case before and after?
4. **Parameter object.** Find a group of parameters that always travel together. Introduce a type and update the call sites. Did the new type acquire behavior of its own?
5. **Safe refactoring drill.** Pick a function with tests. Perform five small refactorings, committing after each and running the suite. Did any test break? What did that reveal?
6. **Rewrite analysis.** Choose a module someone has proposed rewriting. List what the existing code knows that is not written down: edge cases, workarounds, undocumented behavior. Estimate the cost of rediscovering it.
7. **Strangler plan.** For a legacy subsystem, design a facade and a migration order by which slice would you move first, how would you verify it, and how would you measure the remaining legacy traffic?
8. **Consistency audit.** Diff your last change against the surrounding code. Did you introduce a convention that exists nowhere else in the file? Align it or justify it.
