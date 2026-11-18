# 20. Concurrency, Events, and Data-Driven Design

Most systems are concurrent whether or not their authors intended it. A web server handles many requests at once; a UI responds while a fetch is in flight; a batch job writes to a database while another reads. Concurrency is not an advanced feature bolted on at the end; it is a property of the environment the code runs in.

This chapter is about designing for that environment: making time and ordering explicit, keeping shared state contained, and choosing between the major coordination styles—shared memory, message passing, events, and data-driven dispatch.

## Learning objectives

- Recognize temporal coupling and explain why it is a design problem.
- Choose between shared-state and message-passing designs.
- Use async/await without losing error handling or ordering guarantees.
- Design with events and streams while controlling their hidden coupling.
- Model stateful behavior with explicit state machines and tables.
- Structure data-driven systems around pipelines, blackboards, and declarative rules.
- Bound concurrency and reason about backpressure.

## 20.1 Temporal coupling

**Temporal coupling** is a dependency on *when* something happens. Code is temporally coupled when it only works if operations occur in a particular order, or at a particular time, without that requirement being visible in the interface.

```typescript
declare function writeFile(path: string, contents: string): void;

class ReportGenerator {
  #rows: string[] = [];
  #rendered = "";

  load(rows: readonly string[]): void {
    this.#rows = [...rows];
  }

  render(): void {
    this.#rendered = this.#rows.join("\n");
  }

  save(path: string): void {
    // Silently saves whatever was last rendered, which may be stale or empty.
    writeFile(path, this.#rendered);
  }
}
```

Nothing in `save` says it must be called after `render`, which must be called after `load`. A caller who calls `save` first gets an empty file; a caller who calls `load` after `render` saves stale data. The class is a state machine with undocumented states.

There are two ways to fix it:

**Make the sequence a value.** Return the rendered report from `render`, and pass it to `save`. Now the dependency is a data dependency, checked by the compiler.

```typescript
declare function writeFile(path: string, contents: string): void;

interface Report {
  readonly body: string;
}

function renderReport(rows: readonly string[]): Report {
  return { body: rows.join("\n") };
}

function saveReport(report: Report, path: string): void {
  writeFile(path, report.body);
}
```

**Make the sequence explicit in the type.** If the steps must be separate, model the states so that calling them out of order is a compile error or an immediate failure.

The first fix is usually better: a pure function followed by a side effect has no hidden state and no ordering hazard.

## 20.2 Shared state

Shared mutable state is the classic source of concurrency defects: two operations read a value, both compute a new value from the old one, and one update is lost.

In JavaScript, the event loop means that *synchronous* code does not interleave. But `await` yields control: between `await` points, another task can run and mutate the same object.

```typescript
class Counter {
  #value = 0;

  async increment(): Promise<number> {
    const current = this.#value;      // read
    await Promise.resolve();          // yield: another task may run here
    this.#value = current + 1;        // write based on a stale read
    return this.#value;
  }
}
```

Two concurrent calls to `increment` can both read `0`, both write `1`, and the counter ends at 1 instead of 2. The `await` is the window; without it, the operation would be atomic with respect to other tasks.

Defenses, in order of preference:

**Avoid shared mutable state.** Pass values; return new values. A pure function cannot race with itself.

**Confine the state.** Give each task its own copy and merge results at the end. This is the map-reduce shape.

**Serialize access.** Use a lock, a mutex, or a queue so that only one operation touches the state at a time.

```typescript
class Mutex {
  #tail: Promise<void> = Promise.resolve();

  async runExclusive<T>(work: () => Promise<T> | T): Promise<T> {
    const previous = this.#tail;
    let release!: () => void;
    this.#tail = new Promise<void>((resolve) => {
      release = resolve;
    });
    await previous;
    try {
      return await work();
    } finally {
      release();
    }
  }
}

class SafeCounter {
  readonly #mutex = new Mutex();
  #value = 0;

  increment(): Promise<number> {
    return this.#mutex.runExclusive(() => ++this.#value);
  }
}
```

The mutex chains promises: each caller waits for the previous one to finish. The `finally` guarantees release even if the work throws. This is a small, correct primitive; prefer it to ad-hoc flags.

**Use atomic operations provided by the platform.** Some runtimes offer atomic counters or compare-and-swap. In JavaScript, the main thread is single-threaded; shared memory requires `SharedArrayBuffer` and `Atomics`, which are appropriate only for worker-based parallelism.

## 20.3 Message passing

An alternative to shared memory is **message passing**: components own their state and communicate by sending immutable messages. No component can reach into another's data, so there is no data race—only ordering and delivery concerns.

```typescript
type Command =
  | { readonly kind: "increment"; readonly by: number }
  | { readonly kind: "reset" }
  | { readonly kind: "snapshot"; readonly replyTo: (value: number) => void };

class CounterActor {
  #value = 0;
  readonly #queue: Command[] = [];
  #draining = false;

  send(command: Command): void {
    this.#queue.push(command);
    void this.#drain();
  }

  async #drain(): Promise<void> {
    if (this.#draining) return;
    this.#draining = true;
    try {
      while (this.#queue.length > 0) {
        const command = this.#queue.shift();
        if (command) await this.#handle(command);
      }
    } finally {
      this.#draining = false;
    }
  }

  async #handle(command: Command): Promise<void> {
    switch (command.kind) {
      case "increment":
        this.#value += command.by;
        return;
      case "reset":
        this.#value = 0;
        return;
      case "snapshot":
        command.replyTo(this.#value);
        return;
    }
  }
}
```

The actor processes one message at a time, so its state never races. Callers cannot read `#value` directly; they ask for a snapshot. The trade is asynchrony: every interaction becomes a message, and the design must handle ordering, backpressure, and failure of the recipient.

**When message passing is worth it:**

- the state is genuinely owned by one component;
- the components are distributed or may become so;
- the coordination is naturally event-like;
- isolation is more valuable than synchronous simplicity.

**When it is overkill:**

- a single-process program with simple shared data;
- interactions that need immediate, synchronous answers;
- small teams where the message protocol would be more code than the logic.

## 20.4 Async/await

`async`/`await` makes asynchronous code read like synchronous code. That is its strength and its trap: it hides the points where control can interleave and where errors can occur.

Rules that prevent most async defects:

**Await every promise you depend on.** An unawaited promise is a floating operation: its failure is unhandled, its completion unordered, and its errors invisible.

```typescript
interface Item { readonly id: string }
declare function save(item: Item): Promise<void>;

// Bug: the write may not finish, and its rejection is unhandled.
function saveAll(items: readonly Item[]): void {
  for (const item of items) {
    save(item);
  }
}

// Correct: the caller can await completion and observe failure.
async function saveAllCorrectly(items: readonly Item[]): Promise<void> {
  for (const item of items) {
    await save(item);
  }
}
```

**Know the difference between sequential and concurrent.** `await` in a loop is sequential; `Promise.all` is concurrent. Sequential is correct when each step depends on the previous one or when the target cannot handle concurrency. Concurrent is faster but changes failure behavior: one rejection does not cancel the others, and a partial success is possible.

```typescript
// Concurrent with a limit: at most `limit` operations in flight.
async function mapLimit<T, R>(
  items: readonly T[],
  limit: number,
  work: (item: T) => Promise<R>,
): Promise<R[]> {
  const results: R[] = new Array(items.length);
  let next = 0;

  async function worker(): Promise<void> {
    while (next < items.length) {
      const index = next++;
      results[index] = await work(items[index] as T);
    }
  }

  const workers = Array.from({ length: Math.min(limit, items.length) }, () => worker());
  await Promise.all(workers);
  return results;
}
```

The bounded version prevents overwhelming a downstream service with a thousand simultaneous requests. Unbounded `Promise.all` over a large collection is a common cause of connection-pool exhaustion and rate-limit bans.

**Do not mix callbacks and promises carelessly.** A callback invoked inside a promise executor that never settles creates a hang; a promise returned from a callback that nobody awaits creates a floating failure.

**Handle rejections.** `Promise.all` rejects on the first failure but does not cancel the rest. Use `Promise.allSettled` when you need every outcome, and `AbortController` to cancel work that is no longer needed.

**Beware ordering assumptions.** Two `await`s on independent promises do not preserve the order in which their side effects complete. If order matters, await sequentially or sequence explicitly.

## 20.5 Events and streams

An **event** is a notification that something happened. A **stream** is a sequence of events over time. Both invert control: instead of calling a function, a component subscribes and reacts.

```typescript
type Listener<T> = (event: T) => void;

class Emitter<T> {
  readonly #listeners = new Set<Listener<T>>();

  on(listener: Listener<T>): () => void {
    this.#listeners.add(listener);
    return () => this.#listeners.delete(listener);
  }

  emit(event: T): void {
    for (const listener of [...this.#listeners]) listener(event);
  }
}

interface OrderPlaced { readonly orderId: string; readonly totalCents: number }

const orderPlaced = new Emitter<OrderPlaced>();
const unsubscribe = orderPlaced.on((event) => console.log(event.orderId));

orderPlaced.emit({ orderId: "o_1", totalCents: 2_500 });
unsubscribe();
```

Events decouple the producer from the consumers: the producer does not know who listens or what they do. That is the benefit, and it is also the cost:

- **Hidden dependencies.** The producer cannot see its effects; changing an event's payload can break consumers silently.
- **Ordering.** Listeners are called in an unspecified order unless the emitter guarantees otherwise.
- **Error isolation.** One listener throwing can prevent others from running, or be swallowed.
- **Lifecycle.** Subscriptions must be removed, or they leak and fire on dead objects.
- **Debuggability.** Control flow is not visible in the call stack; a trace must be reconstructed from logs.

Event-driven design is appropriate when the producer genuinely should not know its consumers: UI events, domain events published to other modules, telemetry. It is inappropriate as a general decoupling mechanism inside a single module, where a direct call is clearer.

**Streams** add the dimension of time: buffering, backpressure, and composition. A pipeline of transformations over an asynchronous sequence is more expressive than a set of listeners, but it requires careful handling of completion, errors, and cancellation.

## 20.6 State machines

Many concurrency problems are really state problems. An object that behaves differently depending on its state, and rejects transitions that are not valid, is easier to reason about than a collection of booleans.

```typescript
type OrderState =
  | { readonly status: "draft" }
  | { readonly status: "placed"; readonly placedAt: Date }
  | { readonly status: "paid"; readonly placedAt: Date; readonly paidAt: Date }
  | { readonly status: "shipped"; readonly placedAt: Date; readonly paidAt: Date; readonly shippedAt: Date }
  | { readonly status: "cancelled"; readonly reason: string };

type OrderEvent =
  | { readonly kind: "place"; readonly at: Date }
  | { readonly kind: "pay"; readonly at: Date }
  | { readonly kind: "ship"; readonly at: Date }
  | { readonly kind: "cancel"; readonly reason: string };

function transition(state: OrderState, event: OrderEvent): OrderState {
  switch (state.status) {
    case "draft":
      if (event.kind === "place") return { status: "placed", placedAt: event.at };
      if (event.kind === "cancel") return { status: "cancelled", reason: event.reason };
      break;
    case "placed":
      if (event.kind === "pay") return { status: "paid", placedAt: state.placedAt, paidAt: event.at };
      if (event.kind === "cancel") return { status: "cancelled", reason: event.reason };
      break;
    case "paid":
      if (event.kind === "ship") {
        return {
          status: "shipped",
          placedAt: state.placedAt,
          paidAt: state.paidAt,
          shippedAt: event.at,
        };
      }
      break;
    case "shipped":
    case "cancelled":
      break;
  }
  throw new Error(`Invalid transition: ${state.status} + ${event.kind}`);
}
```

The state is a value, the transition is a pure function, and invalid transitions throw. The type carries the data that is valid in each state: a shipped order always has a paid date. This is far easier to test than an object with five mutable booleans, and it eliminates whole classes of "how did we get here?" bugs.

For large machines, a **transition table** is more compact and easier to inspect:

```typescript
const transitions: Record<string, Record<string, string>> = {
  draft: { place: "placed", cancel: "cancelled" },
  placed: { pay: "paid", cancel: "cancelled" },
  paid: { ship: "shipped" },
  shipped: {},
  cancelled: {},
};

function nextStatus(current: string, event: string): string | undefined {
  return transitions[current]?.[event];
}
```

Tables are excellent for auditing: a reviewer can see every legal transition at a glance. Code is better when transitions carry complex side effects or guards.

## 20.7 Pipelines and data-driven design

A **pipeline** is a sequence of stages, each transforming a stream of data. Pipelines are a good fit for concurrency because stages can run independently, with queues between them providing buffering and backpressure.

```typescript
type Stage<A, B> = (input: AsyncIterable<A>) => AsyncIterable<B>;

async function* map<T, R>(input: AsyncIterable<T>, fn: (value: T) => R): AsyncIterable<R> {
  for await (const value of input) yield fn(value);
}

async function* filter<T>(input: AsyncIterable<T>, predicate: (value: T) => boolean): AsyncIterable<T> {
  for await (const value of input) {
    if (predicate(value)) yield value;
  }
}

async function* batch<T>(input: AsyncIterable<T>, size: number): AsyncIterable<T[]> {
  let buffer: T[] = [];
  for await (const value of input) {
    buffer.push(value);
    if (buffer.length >= size) {
      yield buffer;
      buffer = [];
    }
  }
  if (buffer.length > 0) yield buffer;
}
```

The `batch` stage is what makes a pipeline efficient: downstream work happens once per batch rather than once per item. The `async` iteration protocol also gives natural backpressure—the consumer pulls, so a slow stage slows the producer.

**Data-driven design** goes further: instead of encoding behavior in control flow, put it in data that a general engine interprets. Configuration tables, rule sets, and declarative schemas are all examples. Chapter 13's dispatch table is a small instance; a pricing engine driven by a table of rules is a larger one.

The trade is the same as with domain languages: data is easier to change, inspect, and validate than code, but a general engine can become an interpreter for a language nobody designed. Keep the data model small and the engine's semantics explicit.

![A message table: entries in no particular order, each with a message ID.](assets/message-table.png)

![Each message kind has its own format.](assets/message-formats.png)

![An indexed access table reaches entries through an intermediate index.](assets/indexed-access-table.png)

![A stair-step table categorizes entries by the step they reach.](assets/stair-step-table.png)

## 20.8 Blackboards

A **blackboard** is a shared data structure that several independent components read and write, coordinating indirectly through the data rather than through direct calls. Classic uses: constraint solvers, speech recognition pipelines, and some workflow engines.

The benefit is loose coupling: components can be added without changing the others. The costs are substantial:

- **Unpredictable control flow.** Who runs next depends on the state of the board, which any component can change.
- **Implicit dependencies.** Components depend on parts of the board they do not own.
- **Debugging difficulty.** There is no call stack connecting cause and effect.
- **Concurrency hazards.** The board is shared mutable state by definition.

Blackboards are appropriate when the problem is genuinely opportunistic—several specialists contributing partial solutions to an ill-structured problem. They are a poor default for ordinary business logic, where an explicit pipeline or state machine is far easier to follow.

## Summary

- Temporal coupling hides ordering requirements; fix it by returning values or by making states explicit in types.
- Shared mutable state races across `await` boundaries; avoid it, confine it, or serialize access with a mutex.
- Message passing removes data races by giving each component ownership of its state, at the cost of asynchrony and protocol design.
- Await every promise you depend on; distinguish sequential from concurrent execution; bound concurrency.
- Events decouple producers from consumers and hide dependencies; use them where the decoupling is real and document the protocol.
- State machines make stateful behavior explicit, testable, and exhaustive; use tables when the transition logic is simple.
- Pipelines and async iteration give natural backpressure; data-driven engines trade code for data and require disciplined semantics.
- Blackboards are for genuinely opportunistic problems; they are a poor default because control flow and dependencies become implicit.

## Exercises

1. **Temporal coupling hunt.** Find a class with methods that must be called in order. Redesign it so the sequence is either a returned value or an explicit state. Compare the call sites.
2. **Race reproduction.** Write a small program with an `await` between a read and a write to the same field, run two operations concurrently, and observe the lost update. Then fix it with a mutex.
3. **Mutex review.** Implement `runExclusive` and test it with an operation that throws. Does the mutex release? What happens to queued callers?
4. **Bounded concurrency.** Rewrite an unbounded `Promise.all` over a large collection using `mapLimit`. What limit would you choose, and how would you discover it?
5. **Event audit.** List the events in a system you know. For each, name the producer, the consumers, and what breaks if the payload changes. Which events would be clearer as direct calls?
6. **State machine.** Model a workflow you own as a union of states and a transition function. Which invalid transitions does the type system now prevent? Which still need runtime checks?
7. **Pipeline.** Build a three-stage async pipeline (read, transform, batch-write) over an async iterable. Where is backpressure applied, and what happens when the writer is slow?
8. **Blackboard decision.** Describe a problem that would genuinely benefit from a blackboard, and one that would not. What property distinguishes them?
