# 4. Deep Modules and Good Abstractions

The central act of software design is decomposition: dividing a problem into pieces that can be understood and changed independently. But decomposition is not enough. You can divide a system into a hundred pieces and make it harder to understand, because every boundary is also a place where knowledge must cross, and every crossing is a chance for that knowledge to leak.

This chapter is about what makes a module a good piece: an interface that hides more than it reveals, and an implementation that provides real capability behind it.

## Learning objectives

- Explain why modularity is a strategy for managing dependencies rather than an end in itself.
- Distinguish the formal and informal parts of an interface.
- Define module depth and use it to evaluate a design.
- Recognize shallow modules and classitis.
- Design an interface around the common case while keeping uncommon cases possible.
- Explain why a simple interface matters more than a simple implementation.

## 4.1 Why modules at all

A module is a unit of code with an interface and an implementation: a function, a class, a package, a service. Modular design works because it allows a developer to understand one part of a system without understanding all of it. That is the whole benefit, and every rule in this chapter follows from it.

For that benefit to be real, the module must **hide** something. If using a module requires understanding its internals, the module has not reduced the amount a developer must know; it has merely moved the knowledge behind a door and left the door open.

This gives a first test for any boundary:

> **Does the interface tell me everything I need to use the module, and nothing I do not need to know?**

A boundary that fails the first half is under-specified: callers guess, and their guesses become implicit dependencies. A boundary that fails the second half is leaky: callers must understand implementation details, so changes propagate.

![Design at several levels: system, subsystems, and classes.](assets/levels-of-design.png)

![A system decomposed into six subsystems.](assets/subsystems.png)

![A billing system expressed as four cooperating objects.](assets/billing-system-objects.png)

## 4.2 What is in an interface?

Most programmers think of an interface as a set of signatures. That is only the formal part.

**Formal interface:** names, parameter types, return types, visibility, generics, thrown errors (in languages that declare them).

**Informal interface:** everything a caller must know to use the module correctly:

- preconditions and postconditions;
- units, ranges, and formats;
- invariants that hold before and after each call;
- ownership and lifetime of resources;
- side effects and ordering constraints;
- performance characteristics;
- error behavior;
- thread-safety and concurrency assumptions.

The informal interface is often larger than the formal one, and it is where most complexity lives. A method with a beautiful signature can still be a bad interface if its contract is a paragraph of exceptions and special cases.

```typescript
/**
 * A mutable sequence of Unicode text.
 *
 * Positions are UTF-16 code-unit offsets in the range [0, length].
 * `insert` at `length` appends. `delete` removes `count` code units,
 * clamped to the end of the buffer. All methods are synchronous and
 * not safe for concurrent use from multiple workers.
 */
export interface TextBuffer {
  readonly length: number;
  insert(position: number, text: string): void;
  delete(start: number, count: number): void;
  slice(start: number, end?: number): string;
  toString(): string;
}
```

The comment is part of the interface. It tells a caller what the types cannot: clamping behavior, offset units, mutation, and concurrency. Without it, the interface is formally complete and practically ambiguous.

> **Design the contract, not just the signature.** If you cannot describe the contract in a few precise sentences, the module probably has too many responsibilities or too many special cases.

## 4.3 Abstraction

An **abstraction** is a simplified view of an entity that omits details irrelevant to a particular purpose. A `TextBuffer` is an abstraction over memory layout and Unicode encoding. A `Map` is an abstraction over hashing and collision resolution. A `Clock` is an abstraction over the system time source.

Abstraction is not the same as encapsulation. Encapsulation is a mechanism (hiding state behind an interface); abstraction is a *choice about which details matter*. You can encapsulate a bad abstraction perfectly and still be confused. Good abstractions share three properties:

1. **They have a clear purpose.** You can say what the abstraction is *for* in one sentence.
2. **They omit details that do not matter to that purpose.** A `TextBuffer` for an editor should not expose its internal line index.
3. **They are stable relative to the details they hide.** The interface should change less often than the implementation.

The third property is the practical payoff. If an abstraction is well chosen, you can replace its implementation—a faster data structure, a different storage backend, a new algorithm—without changing its users. That is what makes performance work, testing, and platform migrations possible.

![Abstraction presents a simpler view of a complex concept.](assets/abstraction.png)

![Encapsulation hides the details behind that view.](assets/encapsulation.png)

![Programs are organized into levels of abstraction; good design lets most work stay near the top.](assets/levels-of-abstraction.png)

## 4.4 Deep modules

A module is **deep** when it provides a lot of functionality behind a simple interface. It is **shallow** when its interface is nearly as complex as its implementation—when using it requires almost as much knowledge as writing it would.

Depth is a ratio, not a size:

```
depth ≈ capability provided / complexity of the interface
```

A small function can be deep if it hides a tricky algorithm behind one clear call. A large class can be shallow if it exposes dozens of methods that callers must orchestrate in a particular order.

Consider a buffer designed around editor commands:

```typescript
// Shallow: the interface exposes the implementation's notion of editing operations.
export class EditorCommands {
  insertChar(c: string): void { /* ... */ }
  deleteChar(): void { /* ... */ }
  backspace(): void { /* ... */ }
  deleteWord(): void { /* ... */ }
  insertLineBreak(): void { /* ... */ }
  deleteLine(): void { /* ... */ }
  moveCursorLeft(): void { /* ... */ }
  moveCursorRight(): void { /* ... */ }
  moveCursorToLineStart(): void { /* ... */ }
  moveCursorToLineEnd(): void { /* ... */ }
  select(start: number, end: number): void { /* ... */ }
  replaceSelection(text: string): void { /* ... */ }
  // ... twenty more
}
```

Each method is trivial. The complexity has not disappeared; it has moved into the *relationships* between methods. A caller must know the state machine: what happens if you `deleteWord` at the start of a line, whether `moveCursorLeft` collapses a selection, whether `insertChar` replaces the selection, and so on. Every editor feature must understand this protocol.

Now a deeper interface:

```typescript
export interface TextBuffer {
  readonly length: number;
  insert(position: number, text: string): void;
  delete(start: number, count: number): void;
  slice(start: number, end?: number): string;
}

export class SimpleTextBuffer implements TextBuffer {
  #text = "";

  get length(): number {
    return this.#text.length;
  }

  insert(position: number, text: string): void {
    const p = clamp(position, 0, this.#text.length);
    this.#text = this.#text.slice(0, p) + text + this.#text.slice(p);
  }

  delete(start: number, count: number): void {
    const s = clamp(start, 0, this.#text.length);
    const e = clamp(s + count, s, this.#text.length);
    this.#text = this.#text.slice(0, s) + this.#text.slice(e);
  }

  slice(start: number, end: number = this.#text.length): string {
    return this.#text.slice(clamp(start, 0, this.#text.length), clamp(end, 0, this.#text.length));
  }

  toString(): string {
    return this.#text;
  }
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}
```

The second interface is smaller, but it is not less capable. Every editing operation can be built from four primitives: insert, delete, read, and length. The editor's cursor, selection, word boundaries, and undo policy live *above* the buffer, where they belong, because they are policies rather than storage. The buffer hides the storage decision, so it can later be replaced by a rope or a piece table without touching the editor's command layer.

This is the characteristic shape of a deep module: **a few general operations that compose**, rather than many special operations that must be orchestrated.

> **The interface should be general enough to cover the known uses, and no more.** The buffer does not need `undo()` or `save()`; those are different concerns. Generality is not the same as omniscience.

![A deep module offers more functionality behind a smaller interface.](assets/deep-vs-shallow-module.jpg){width=45%}

![A good class interface is the visible tip of a much larger implementation.](assets/interface-iceberg.png)

## 4.5 Shallow modules and classitis

A shallow module is not necessarily useless. A thin wrapper around a third-party API can be valuable: it isolates a dependency, normalizes errors, or provides a seam for testing. But shallow modules have a cost, and that cost is easy to miss because each one looks small.

The cost is **interface surface**. Every method, parameter, and type is something a reader may have to learn. If a module's interface is almost as complex as its body, the module has added a name and a boundary without adding much abstraction. The reader now has two things to understand instead of one.

**Classitis** is the belief that more classes are better—that a design improves by splitting every concept into smaller and smaller types. The result is a swarm of anemic classes (`User`, `UserDTO`, `UserMapper`, `UserValidator`, `UserService`, `UserManager`, `UserHelper`) where the actual behavior is spread across the swarm. Understanding one operation requires visiting five files, and each class's interface is dominated by getters, setters, and conversion methods.

```typescript
// Classitis: four types and three services to represent one concept.
interface UserData { id: string; email: string; }
interface UserEntity { id: string; email: string; }
interface UserModel { id: string; email: string; }
interface UserResponse { id: string; email: string; }

class UserDataMapper {
  toEntity(data: UserData): UserEntity {
    return { id: data.id, email: data.email };
  }
}
class UserEntityMapper {
  toModel(entity: UserEntity): UserModel {
    return { id: entity.id, email: entity.email };
  }
}
class UserPresenter {
  toResponse(model: UserModel): UserResponse {
    return { id: model.id, email: model.email };
  }
}
```

Sometimes these layers are justified: a persistence boundary may need a distinct representation, an API boundary may need a stable wire format, and a domain model may need behavior that a DTO must not have. But when the layers exist only because "layered architecture" says so, they multiply the amount of code without hiding a decision. The test is not "is this layer a recognized pattern?" but "what does this layer hide, and would removing it force callers to know something they should not?"

## 4.6 Simple interface vs. simple implementation

Given a choice, prefer a simple interface over a simple implementation. This sounds obvious, but it cuts against a strong instinct: programmers like code that is easy to write. It is often easier to implement a module by exposing its internal steps than by designing a small set of operations that hide them.

The consequence of the instinct is a module that is easy for its author and hard for everyone else. Since a module is used far more often than it is written, the trade is usually bad.

```typescript
// Easy to implement, hard to use: the caller must know the parsing steps.
export function parseConfig(text: string): { key: string; value: string }[] {
  return text
    .split("\n")
    .filter((line) => line.includes("="))
    .map((line) => {
      const [key, value] = line.split("=");
      return { key: key.trim(), value: value.trim() };
    });
}

// The caller does this everywhere:
const entries = parseConfig("port=8080\nhost=localhost");
const port = entries.find((e) => e.key === "port")?.value;
const host = entries.find((e) => e.key === "host")?.value;
```

```typescript
// Harder to implement, easier to use: the caller asks a question.
export interface Config {
  get(key: string): string | undefined;
  getRequired(key: string): string;
  getNumber(key: string, fallback: number): number;
}

export function parseConfig(text: string): Config {
  const entries = new Map<string, string>();
  for (const line of text.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eq = trimmed.indexOf("=");
    if (eq < 0) throw new Error(`Invalid config line: ${line}`);
    entries.set(trimmed.slice(0, eq).trim(), trimmed.slice(eq + 1).trim());
  }
  return {
    get: (key) => entries.get(key),
    getRequired: (key) => {
      const value = entries.get(key);
      if (value === undefined) throw new Error(`Missing config key: ${key}`);
      return value;
    },
    getNumber: (key, fallback) => {
      const raw = entries.get(key);
      if (raw === undefined) return fallback;
      const parsed = Number(raw);
      if (!Number.isFinite(parsed)) throw new Error(`Config key ${key} is not a number: ${raw}`);
      return parsed;
    },
  };
}
```

The second version absorbs parsing details, validation, and the common "missing key" decision. Callers are simpler; the complexity lives where it can be tested once and changed once. The implementation is longer, but length is not the metric—**what callers must know** is.

There is a limit. A module that tries to anticipate every caller's needs becomes a configuration surface with a hundred options, which is its own kind of shallow interface. The goal is not to hide everything; it is to hide the things that callers should not have to decide.

## 4.7 A diagnostic: the interface-to-implementation ratio

When evaluating a module, ask four questions:

1. **What does a caller have to know that the types do not say?** If the answer is long, the contract is complex.
2. **How many distinct operations must a caller combine to accomplish a typical task?** If the answer is many, the module may be too low-level.
3. **If I replaced the implementation, how much of the interface would survive?** If little, the interface is leaking implementation.
4. **What does this module hide?** If the answer is "nothing," it is a pass-through, and it needs a justification.

These questions are qualitative, and that is appropriate. Depth is a judgment about how much knowledge a boundary removes from the reader's mind, not a number a tool can compute reliably. A module with ten methods can be deep if those methods cover a coherent, powerful abstraction; a module with one method can be shallow if that method merely forwards arguments.

## 4.8 Modules in TypeScript

TypeScript's type system gives module designers useful tools:

- **Interfaces describe contracts.** An `interface` can capture the formal shape of a module and be implemented by multiple backends (in-memory, HTTP, database).
- **`readonly` and `ReadonlyArray` express immutability** in the type system, preventing accidental mutation across a boundary.
- **Discriminated unions model alternatives** without exposing a class hierarchy.
- **Generics express reuse without duplication**, but over-general generics make interfaces harder to read. Prefer the simplest type that captures the constraint.
- **Module boundaries are files and packages.** A package's public entry point is its interface; everything not exported is implementation. Use `export type` and explicit public APIs; avoid deep imports into another package's internals.

TypeScript's structural typing means an interface can be satisfied by any object with the right shape. This is convenient for testing, but it also means a type name does not guarantee provenance. When provenance matters (an ID from one domain vs. another), a branded type can help:

```typescript
declare const brand: unique symbol;

export type UserId = string & { readonly [brand]: "UserId" };
export type OrderId = string & { readonly [brand]: "OrderId" };

export function asUserId(value: string): UserId {
  if (!value.startsWith("usr_")) throw new Error(`Invalid user id: ${value}`);
  return value as UserId;
}
```

Use this sparingly. Brands add friction; they are worth it where mixing two strings would be a real bug.

## Summary

- Modules exist to let developers understand one part of a system without understanding all of it; a module that does not hide something has not earned its boundary.
- An interface includes formal signatures and an informal contract: invariants, units, ownership, side effects, performance, errors, and concurrency assumptions.
- An abstraction is a deliberately incomplete view; good abstractions have a clear purpose, omit irrelevant detail, and remain stable as implementations change.
- Deep modules provide substantial capability behind a simple interface. Shallow modules add interface surface without removing knowledge.
- Classitis multiplies types and layers without hiding decisions. Judge a layer by what it hides, not by whether it has a familiar name.
- Prefer a simple interface to a simple implementation, but avoid replacing one complexity with an unbounded configuration surface.

## Exercises

1. **Interface inventory.** Choose a module you own. List its formal interface and its informal interface. Which informal items are documented? Which are only in someone's head? Pick one and document it.
2. **Depth assessment.** For three modules, answer the four diagnostic questions in §4.7. Rank them by depth. Does the ranking match how pleasant they are to use?
3. **Refactor a shallow API.** Take a class or module with many command-style methods. Design a smaller interface of general operations that can express the same behavior. Write the new interface and one adapter implementation.
4. **Classitis hunt.** Find a cluster of classes that exist mainly to convert one representation into another. For each class, write down what it hides. Remove or merge the ones that hide nothing.
5. **Common case first.** For an API you are designing, write the code for the three most common call sites using your current interface. Then redesign the interface so those call sites are as simple as possible without making rare cases impossible. Compare the two designs.
6. **Depth vs. size.** Find a small function that hides a difficult algorithm and a large class that exposes many trivial methods. Explain why one is deep and the other shallow, using the definition in this chapter rather than line counts.
