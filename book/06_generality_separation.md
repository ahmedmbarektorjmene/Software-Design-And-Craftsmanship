# 6. Generality, Separation, and Composition

A design is a set of decisions about where to draw lines. The lines in the previous two chapters separated a module from its callers. The lines in this chapter run *through* the system: between the general mechanism and the special case, between the part that changes for one feature and the part that serves many, between two concepts that look similar and two that merely resemble each other.

Most design failures are line-placement failures. A special case leaks into a general mechanism; two concepts are merged because they share a shape; a layer exists only to forward calls; complexity is pushed outward instead of inward. This chapter is about placing the lines well.

## Learning objectives

- Decide how general an interface should be, and why "somewhat general-purpose" beats both narrow and universal.
- Separate general-purpose mechanism from special-purpose policy.
- Apply the "better together or better apart" tests to modules, classes, and methods.
- Recognize pass-through methods and evaluate decorators honestly.
- Pull complexity downward into the module that can best absorb it.
- Eliminate special cases by choosing better representations.

## 6.1 Somewhat general-purpose

An interface can be too specific or too general.

**Too specific:** it encodes the first use case, so every additional use requires a new method, a flag, or a cast. The editor API from Chapter 4 is an example: `backspace()`, `deleteWord()`, `moveCursorToLineStart()` are operations of one particular editor, not properties of text.

**Too general:** it tries to anticipate every possible use, so it becomes abstract, parameterized, and hard to understand. A `Storage<T>` interface with twelve optional hooks for consistency, encryption, compression, and migration may be able to do anything—and therefore tells a caller nothing about what it actually does.

The productive target is **somewhat general-purpose**: the interface should reflect the general problem behind the current need, not the current need alone. Ask:

1. **What is the simplest interface that covers all current uses?** Not the simplest for one use—the simplest for all known uses.
2. **How many situations will this operation be used in?** If the answer is one, a specialized method may be fine. If the answer is likely to grow, generalize now.
3. **Is the general version meaningfully simpler to use?** A general operation that forces callers to compute offsets and lengths may be worse than a specialized one for a common case.
4. **Does the general version hide more?** Generality is valuable when it hides a decision, not when it merely renames one.

The text buffer illustrates the payoff. A `delete(start, count)` primitive can implement backspace, delete-word, delete-line, and delete-selection. The editor's policy layer decides which range to delete; the buffer only knows how to delete. The buffer is general, but not universally abstract: it does not know about words, lines, or selections, because those are policy, not storage.

```typescript
export interface TextBuffer {
  readonly length: number;
  insert(position: number, text: string): void;
  delete(start: number, count: number): void;
  slice(start: number, end?: number): string;
}

// Policy lives above the buffer.
export function backspace(buffer: TextBuffer, cursor: number): number {
  if (cursor === 0) return 0;
  buffer.delete(cursor - 1, 1);
  return cursor - 1;
}

export function deleteWordBefore(buffer: TextBuffer, cursor: number): number {
  const before = buffer.slice(0, cursor);
  const match = /(\s*\S+)\s*$/.exec(before);
  const start = match ? cursor - match[1].length : 0;
  buffer.delete(start, cursor - start);
  return start;
}
```

The general primitive is reused; the special cases are small, testable functions. The alternative—putting `backspace` and `deleteWord` on the buffer—would force the buffer to know about cursor semantics and would make every new editing command a change to the storage module.

> **Generality is a bet on future use.** Make the bet when the evidence is decent: multiple current callers, a domain that is clearly wider than the first feature, or a primitive that obviously composes. Do not make it as an act of faith.

## 6.2 Push specialization up—or down

Once a general mechanism exists, special cases must live somewhere. There are two directions:

- **Upward:** policy, user intent, and feature-specific rules live in the layer that knows the feature. The editor knows what "delete word" means; the buffer does not.
- **Downward:** performance tricks, encoding details, and platform quirks live in the mechanism. The buffer knows how to store text efficiently; the editor does not.

The failure mode is a **special-general mixture**: special-purpose code embedded in a general mechanism, or general-purpose machinery embedded in a special case. Examples:

- A general HTTP client with a hard-coded retry rule for one endpoint.
- A general `Report` class with a branch for "the quarterly report."
- A feature-specific component that reimplements pagination, caching, and validation because the shared versions were inconvenient.

The test is simple: **can I describe what this module does without naming a particular feature?** If not, it is probably special-purpose and should not be the shared mechanism. Conversely, if a feature module contains generic infrastructure, that infrastructure should be extracted—not because duplication is always bad, but because the next feature will need it and will copy it.

## 6.3 Eliminate special cases by changing the representation

Many special cases are artifacts of a poor representation. The classic example is a text editor's cursor and selection. A naive design has two modes:

```typescript
interface EditorState {
  cursor: number;
  selectionStart?: number;
  selectionEnd?: number;
}
```

Every operation must branch: if there is a selection, delete it; otherwise delete a character. If the selection is empty, is it a cursor or an empty selection? What happens when the cursor moves—does it collapse the selection? The special cases multiply.

A better representation treats a selection as a range with a length:

```typescript
interface Selection {
  readonly start: number;
  readonly length: number;
}

const collapsed = (position: number): Selection => ({ start: position, length: 0 });
```

A cursor is a selection of length zero. Deleting a selection of length zero deletes nothing (or one character, depending on policy); replacing a selection of length zero inserts text. The branches disappear, and the invariant "there is always exactly one selection" removes a whole class of states.

```typescript
interface TextBuffer {
  readonly length: number;
  insert(position: number, text: string): void;
  delete(start: number, count: number): void;
}
interface Selection { readonly start: number; readonly length: number }

function replaceSelection(buffer: TextBuffer, selection: Selection, text: string): Selection {
  buffer.delete(selection.start, selection.length);
  buffer.insert(selection.start, text);
  return { start: selection.start + text.length, length: 0 };
}
```

This is a general design move: **when a special case exists only because the data model has two shapes for one concept, unify the shapes.** Other examples:

- Representing "no discount" as a discount of zero rather than `null`.
- Representing "unbounded" as `Infinity` rather than a separate flag.
- Representing an empty collection as an empty array rather than `undefined`.
- Representing a one-shot operation as a list of one.

The move is not universal. Sometimes absence is meaningful and must be distinct from zero or empty (`null` vs. `0` for "unknown price"). The question is whether the special case carries information or only complicates the code.

## 6.4 Better together or better apart

When should two pieces of code be one, and when should they be separate? Four tests help.

**Bring together when information is shared.** If two functions both need the same non-trivial data or the same derived value, putting them together avoids passing the data around and keeps the invariant in one place.

**Bring together when it simplifies the interface.** If combining two operations removes a parameter, a mode, or a required call order, the combined version is deeper.

**Bring together to eliminate duplication.** If the same knowledge appears twice, one owner is better—provided it is genuinely the same knowledge (§5.7).

**Keep apart when the pieces serve different purposes.** A module that parses input and a module that renders output may share a data type, but they change for different reasons. Combining them creates a module with two unrelated reasons to change.

**Keep apart when they are used independently.** If most callers need only one part, combining forces them to depend on both.

**Keep apart when combining creates a dependency cycle or a large interface.** A module that knows about everything is easy to write and impossible to test.

A useful diagnostic is the **cohesion** of the resulting unit. Cohesion is the degree to which the parts of a module belong together:

| Cohesion | Meaning | Example |
|----------|---------|---------|
| Functional | All parts contribute to one well-defined task | `parseOrderLine` |
| Sequential | Output of one part is input to the next | `read → validate → normalize` |
| Communicational | Parts operate on the same data | `updateName`, `updateAddress` on one record |
| Temporal | Parts happen at the same time | `initialize`, `shutdown` |
| Logical | Parts are selected by a flag | `handle(kind: "a" \| "b")` |
| Coincidental | Parts have no meaningful relationship | `Utils` |

Functional cohesion is the target. Sequential and communicational cohesion are often acceptable. Temporal cohesion is a warning: an `init()` that does five unrelated things is hard to test and easy to break. Logical cohesion—one function that branches on a `kind` parameter to do unrelated work—is usually a sign that the function should be split or replaced by dispatch. Coincidental cohesion—a `Utils` module—is where code goes to become unownable.

![The same log statement repeated in several branches.](assets/duplicated-logging.jpg)

![One log statement, reached from every branch.](assets/consolidated-logging.jpg)

## 6.5 Pass-through methods and layers

A **pass-through method** does little except forward its arguments to another method with a similar signature:

```typescript
interface User { id: string; name: string }
interface UserRepository {
  getUser(id: string): Promise<User | undefined>;
  saveUser(user: User): Promise<void>;
}

class UserService {
  constructor(private readonly repository: UserRepository) {}

  getUser(id: string): Promise<User | undefined> {
    return this.repository.getUser(id);
  }

  saveUser(user: User): Promise<void> {
    return this.repository.saveUser(user);
  }
}
```

Each method adds a name to the interface and a frame to the call stack, but hides nothing. If `UserService` is a placeholder for future business logic, it may be justified as a seam; if it is there because "every repository needs a service," it is ceremony.

Pass-through methods are not always bad. They can:

- enforce a policy (authorization, validation, logging) that the inner layer must not know about;
- adapt an awkward third-party interface;
- provide a stable boundary while the implementation changes;
- make testing possible by introducing a seam.

The test is whether the method **adds a decision**. If it merely forwards, and no decision is planned, remove it. If it forwards today but will own a policy tomorrow, document that intention; otherwise the next developer will rightly delete it.

The same logic applies to layers. A layer is justified when it offers a **different abstraction**, not merely a different location. A "service" layer that mirrors the repository's methods, a "manager" that mirrors the service, and a "facade" that mirrors the manager form a stack of pass-throughs. Each layer makes the system look architectural while increasing the number of places a change must travel.

![Removing pass-through methods by letting callers invoke the inner object directly.](assets/pass-through-methods.jpg){width=80%}

![Ways to stop threading a variable through methods that do not use it.](assets/pass-through-variable.jpg){width=90%}

## 6.6 Decorators: useful, but not free

A decorator wraps an object to add behavior while preserving its interface:

```typescript
interface User { id: string }
interface Logger { info(message: string): void }
interface Repository {
  find(id: string): Promise<User | undefined>;
  save(user: User): Promise<void>;
}

class LoggingRepository implements Repository {
  constructor(private readonly inner: Repository, private readonly logger: Logger) {}

  async find(id: string): Promise<User | undefined> {
    this.logger.info(`find ${id}`);
    return this.inner.find(id);
  }

  async save(user: User): Promise<void> {
    this.logger.info(`save ${user.id}`);
    return this.inner.save(user);
  }
}
```

Decorators are a good fit for orthogonal concerns: logging, metrics, caching, retries, transactions. They preserve the interface and compose. But they have costs:

- **Identity and type confusion.** A decorated object is not the same object; `instanceof` checks and equality comparisons can break.
- **Interface duplication.** The decorator must implement every method, even those it does not change. If the interface is large, the decorator is mostly pass-through code.
- **Order sensitivity.** Logging inside retries produces different output from retries inside logging. The composition order becomes part of the design and must be documented.
- **Debugging indirection.** Stack traces and breakpoints cross more frames.

A decorator that adds no abstraction—one that forwards everything and changes nothing—is a pass-through with extra steps. Use decorators when the concern is genuinely orthogonal and the interface is small enough that duplication is manageable. Otherwise, consider handling the concern inside the implementation, or at a boundary where it can be applied once.

## 6.7 Pull complexity downward

When complexity must exist, put it where it can be handled best. Usually that is **inside the module**, not in its callers.

```typescript
// Complexity pushed outward: every caller must handle the default and the error.
function parsePort(raw: string | undefined): number {
  if (raw === undefined) return 8080;
  const port = Number(raw);
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    throw new Error(`Invalid port: ${raw}`);
  }
  return port;
}

// Callers repeat the default and the validation, or forget to.
const port = parsePort("8080");
```

The function is already doing the work; the problem is that callers must remember to call it, and the default is encoded in the function rather than in a configuration layer. A deeper design centralizes the whole decision:

```typescript
interface ServerConfig {
  readonly port: number;
  readonly host: string;
}

function parsePort(raw: string | undefined): number {
  if (raw === undefined) return 8080;
  const port = Number(raw);
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    throw new Error(`Invalid port: ${raw}`);
  }
  return port;
}

export function loadServerConfig(env: Record<string, string | undefined>): ServerConfig {
  const port = parsePort(env.PORT ?? "8080");
  const host = env.HOST ?? "127.0.0.1";
  return { port, host };
}
```

Now the caller asks for a config, not for individual variables. The default, validation, and precedence live in one place. Adding `HOST` does not change any call site.

The same principle applies to error handling. If a module can recover from a failure without the caller's help, it should; exposing the failure forces every caller to implement the same recovery. If the caller must decide (because the right action depends on context), expose it—but expose a decision, not a mechanism.

**Taking it too far:** pulling complexity down can produce a module that makes policy decisions it has no right to make. A library that silently retries a non-idempotent operation, or that swallows an error the caller needs for a transaction, has absorbed complexity by making the caller's decisions for it. The criterion is not "hide everything" but "hide what the module is best positioned to decide."

## 6.8 Composition over inheritance

Composition is often the cleaner way to reuse behavior: an object **has** a collaborator rather than **is** a specialization of a parent. Inheritance couples a subclass to the parent's implementation, exposes protected state, and makes behavior depend on a fragile hierarchy. Composition keeps the collaborator's interface explicit and substitutable.

```typescript
interface User { id: string; name: string }
interface UserRepository {
  find(id: string): Promise<User | undefined>;
  save(user: User): Promise<void>;
}

class DatabaseUserRepository implements UserRepository {
  async find(id: string): Promise<User | undefined> {
    // query the database
    return undefined;
  }
  async save(user: User): Promise<void> {
    // write to the database
  }
}

// Inheritance: the subclass inherits storage and policy it may not want.
class CachedUserRepository extends DatabaseUserRepository {
  readonly #cache = new Map<string, User>();
}

// Composition: the cache wraps any repository.
class CachingUserRepository implements UserRepository {
  constructor(
    private readonly inner: UserRepository,
    private readonly cache: Map<string, User>,
  ) {}
  async find(id: string): Promise<User | undefined> {
    return this.cache.get(id) ?? this.inner.find(id);
  }
  async save(user: User): Promise<void> {
    await this.inner.save(user);
    this.cache.set(user.id, user);
  }
}
```

Prefer composition unless there is a genuine is-a relationship with substitutability and a stable parent contract. Chapter 7 examines the trade-offs in detail, including the cases where inheritance is the right tool.

## Summary

- Aim for somewhat general-purpose interfaces: general enough to cover known and likely uses, specific enough to be understandable.
- Separate general mechanism from special-purpose policy, and push each piece to the layer that can own it.
- Many special cases disappear when the representation is unified (cursor as a zero-length selection, absence as a distinct value only when it carries meaning).
- Bring code together when it shares knowledge or simplifies an interface; keep it apart when purposes, usage, or change reasons differ.
- Pass-through methods and layers must add a decision or an abstraction; otherwise they are overhead.
- Decorators suit orthogonal concerns but duplicate interfaces and add indirection.
- Pull complexity downward when the module can decide better than its callers—but do not let it make policy decisions that belong to callers.
- Prefer composition to inheritance unless the is-a relationship is real and stable.

## Exercises

1. **Generalize an interface.** Take a module with several feature-specific methods. Identify the general primitives behind them, rewrite the interface, and reimplement three of the special cases as callers of the primitives.
2. **Special-general mixture.** Find a shared module containing a branch for one feature. Move the special case up or down, and explain which direction you chose and why.
3. **Unify a representation.** Find a type with two shapes for one concept (a nullable field, a mode flag, a special empty case). Redesign it as one shape and list the branches that disappear.
4. **Pass-through audit.** Identify a service/manager/facade layer. For each method, write the decision it makes. Remove the methods that add no decision; what breaks, and what does that reveal?
5. **Decorator review.** Find a wrapper class. Does it add an orthogonal concern? What is the composition order, and is it documented? Could the concern be handled at a boundary instead?
6. **Pull complexity down.** Find a function whose callers all repeat the same default or validation. Move the decision into the callee (or a configuration layer) and simplify the call sites.
7. **Cohesion check.** Classify three modules by the cohesion table. Which one would you split, and along which line?
