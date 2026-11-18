# 5. Information Hiding, Leakage, and Coupling

A module boundary is a promise: *you can use this without knowing how it works.* Most design problems are broken promises. The implementation detail you promised to hide shows up in a caller's assumptions; the format you promised to own is parsed in three other places; the decision you promised to encapsulate is duplicated in a configuration file.

This chapter is about keeping the promise. It covers what to hide, how hiding fails, and how to reason about the dependencies that remain.

## Learning objectives

- Apply the information-hiding criterion: hide the decisions most likely to change.
- Recognize information leakage and explain why it defeats modularity.
- Identify temporal decomposition and restructure code around knowledge rather than execution order.
- Detect overexposure and design interfaces around the common case.
- Distinguish necessary coupling from accidental coupling, and use orthogonality as a test.
- Apply DRY to knowledge rather than to textual similarity.
- Recognize when hiding has gone too far.

## 5.1 Hide the decisions that are likely to change

The classic criterion for decomposition is not "one module per step in the workflow" and not "one class per noun in the requirements." It is:

> **Hide the design decisions that are most likely to change, so that when they change, only one module is affected.**

Typical decisions worth hiding:

- the on-disk or on-wire representation of data;
- the choice of database, protocol, or third-party service;
- algorithms and data structures;
- caching and invalidation policy;
- authentication and authorization mechanics;
- error representation and retry policy;
- threading and scheduling model;
- default values and configuration precedence.

A useful design habit is to ask, for every module: **what secret does this module own?** If the answer is "nothing," the module is probably a pass-through. If the answer is "several unrelated secrets," the module probably has more than one reason to change.

```typescript
// A module that owns the wire format of an order line.
// Callers know only "encode/decode an OrderLine".
export interface OrderLine {
  sku: string;
  quantity: number;
}

export function encodeOrderLine(line: OrderLine): string {
  return `${encodeURIComponent(line.sku)}|${line.quantity}`;
}

export function decodeOrderLine(text: string): OrderLine {
  const [rawSku, rawQuantity] = text.split("|");
  const quantity = Number(rawQuantity);
  if (!rawSku || !Number.isInteger(quantity) || quantity < 0) {
    throw new Error(`Malformed order line: ${text}`);
  }
  return { sku: decodeURIComponent(rawSku), quantity };
}
```

The separator, escaping rule, and validation live in one place. If the format changes to JSON, only this module changes. That is information hiding in its most concrete form: a decision with a single home.

## 5.2 Information leakage

**Information leakage** occurs when a design decision is reflected in more than one module. It is the characteristic failure of modular design, and it is often invisible in code review because each individual file looks reasonable.

```typescript
export interface OrderLine {
  sku: string;
  quantity: number;
}

// writer.ts
export function writeLine(line: OrderLine): string {
  return `${encodeURIComponent(line.sku)}|${line.quantity}`;
}

// reader.ts
export function readLine(text: string): OrderLine {
  const [sku, quantity] = text.split("|");
  return { sku: decodeURIComponent(sku), quantity: Number(quantity) };
}
```

Two modules now know the format. Change the separator, add a field, or switch to JSON, and both must change in sync. Worse, the knowledge is *implicit*: nothing in either signature says "these two functions share a format." A new developer can change one and not the other, and the tests may still pass if they only exercise one direction.

Leakage has several common shapes:

- **Format leakage.** Reader and writer both encode the same layout (as above).
- **Schema leakage.** The same data shape is redeclared in the API layer, the UI, and the database layer, with manual conversions.
- **Policy leakage.** A business rule (tax rate, discount threshold, retry limit) appears in several modules.
- **Mechanism leakage.** Callers must know that a function uses a particular cache, transaction, or thread, and must call it in a particular order.
- **Temporal leakage.** The order of operations is encoded in the structure of shared state (see §5.3).

The antidote is not "add an abstraction layer" in the abstract. It is to find the decision and give it exactly one owner. Sometimes that owner is a function; sometimes a type; sometimes a module; sometimes a configuration file. The form matters less than the singularity.

> **Leakage is about knowledge, not lines of code.** Two functions can share a format without sharing a line of code. The question is: how many places must change if the format changes?

![An HTTP request: a wire format that a class should hide, not re-expose.](assets/http-request-format.jpg){width=55%}

## 5.3 Temporal decomposition

**Temporal decomposition** structures a system around the order in which operations happen: parse, then validate, then authenticate, then authorize, then handle, then respond. Each step becomes a module, and the modules communicate through a shared context object.

```typescript
interface RequestContext {
  raw?: string;
  parsed?: unknown;
  user?: { id: string };
  permissions?: string[];
  result?: unknown;
  error?: string;
}

function parse(ctx: RequestContext): void { /* sets ctx.parsed */ }
function authenticate(ctx: RequestContext): void { /* sets ctx.user */ }
function authorize(ctx: RequestContext): void { /* reads ctx.user, sets ctx.permissions */ }
function handle(ctx: RequestContext): void { /* reads ctx.parsed and ctx.permissions */ }
```

This looks modular—each step is a function—but the modules are not independent. Every step depends on the exact shape and timing of the context. `handle` cannot be understood without knowing what `parse` produces, what `authenticate` guarantees, and what `authorize` adds. The modules are coupled by a shared mutable record whose schema is defined nowhere.

The alternative is to decompose by **knowledge**, not by **sequence**:

```typescript
interface ParsedRequest {
  readonly method: string;
  readonly path: string;
  readonly body: unknown;
}

interface AuthenticatedUser {
  readonly id: string;
  readonly permissions: readonly string[];
}

function parseRequest(raw: string): ParsedRequest {
  const url = new URL(raw, "https://example.com");
  return { method: "GET", path: url.pathname, body: undefined };
}

function authenticate(request: ParsedRequest, token: string): AuthenticatedUser {
  if (!token) throw new Error("Missing token");
  return { id: "user-1", permissions: [] };
}

function handleRequest(request: ParsedRequest, user: AuthenticatedUser): unknown {
  return { path: request.path, userId: user.id };
}
```

Now each function has an explicit input and output. The pipeline still exists, but the *data flow* is visible in the types, and each stage can be tested in isolation. The sequence is a property of the caller, not of a hidden mutable context.

Temporal decomposition is not always wrong. Sometimes the steps genuinely share a resource (a transaction, a parsed stream) and a context object is the simplest way to carry it. The danger is letting execution order dictate module boundaries by default. Ask: **if the order changed, would these modules still make sense?** If not, they may be steps in a procedure rather than modules in a design.

## 5.4 Overexposure

An interface is **overexposed** when using the common case requires understanding rare options. The classic shape is a configuration object with a dozen required fields, most of which have obvious defaults:

```typescript
interface Logger { info(message: string): void }
interface HttpClient { get(path: string): Promise<Response> }

export interface HttpClientOptions {
  baseUrl: string;
  timeoutMs: number;
  retries: number;
  retryDelayMs: number;
  keepAlive: boolean;
  maxSockets: number;
  userAgent: string;
  logger: Logger;
  onRetry?: (attempt: number) => void;
}

export declare function createHttpClient(options: HttpClientOptions): HttpClient;
```

Every caller must now decide about sockets and retries, even if they only want to GET a URL. The interface has shifted complexity outward: the module author avoided choosing defaults, so every caller must choose them instead.

A deeper design provides a simple common case and a deliberate escape hatch:

```typescript
interface Logger { info(message: string): void }
interface HttpClient { get(path: string): Promise<Response> }
const silentLogger: Logger = { info() {} };

export interface HttpClientOptions {
  timeoutMs?: number;
  retries?: number;
  logger?: Logger;
}

export function createHttpClient(baseUrl: string, options: HttpClientOptions = {}): HttpClient {
  const timeoutMs = options.timeoutMs ?? 5_000;
  const retries = options.retries ?? 2;
  const logger = options.logger ?? silentLogger;
  return {
    async get(path: string): Promise<Response> {
      logger.info(`GET ${baseUrl}${path} (timeout ${timeoutMs}ms, retries ${retries})`);
      return fetch(`${baseUrl}${path}`);
    },
  };
}
```

Now the common call is `createHttpClient("https://api.example.com")`, and the rare caller can override what matters. The module owns the defaults—which is appropriate, because the module knows more about HTTP than most callers do.

Overexposure is not only about options. It appears whenever an API forces callers to know about a feature they do not use: a `Result` type that requires handling five error variants for an operation that cannot fail, a builder that requires ten calls before the first useful one, a class whose constructor demands a dependency it only needs for one method.

The fix is usually to **make the common case the default path** and push uncommon configuration behind an optional, explicit mechanism. The limit is that defaults must be visible and overridable; hiding a decision that callers legitimately need is the opposite failure (§5.7).

## 5.5 Hiding inside a class

Information hiding is not only a module-level concern. It applies inside a class, between its public interface and its private state, and between methods.

```typescript
interface Money { cents: number; currency: "USD" }
interface InvoiceLine { amount: Money }

export class Invoice {
  readonly #lines: InvoiceLine[] = [];
  #taxRate: number;

  constructor(taxRate: number) {
    if (taxRate < 0 || taxRate > 1) throw new RangeError("taxRate must be in [0, 1]");
    this.#taxRate = taxRate;
  }

  addLine(line: InvoiceLine): void {
    this.#lines.push(line);
  }

  total(): Money {
    const subtotal = this.#lines.reduce((sum, line) => sum + line.amount.cents, 0);
    return { cents: Math.round(subtotal * (1 + this.#taxRate)), currency: "USD" };
  }

  lineCount(): number {
    return this.#lines.length;
  }
}
```

The class owns three secrets: the storage of lines, the tax calculation, and the rounding rule. Callers cannot mutate the array, cannot set an invalid tax rate, and cannot accidentally compute the total without tax. If the storage becomes a map or the rounding rule changes, only this class changes.

The failure mode is to expose the internals "for flexibility": a getter typed `get lines(): InvoiceLine[]` that returns the internal array. That lets a caller push a line without validation, or hold a reference that changes under them. If callers need to read the lines, return a readonly view instead: `get lines(): readonly InvoiceLine[] { return this.#lines; }`.

`readonly` in TypeScript is a compile-time restriction, not a runtime guarantee: a determined caller can cast it away. For most application code that is sufficient; for security boundaries, return a defensive copy or a frozen array.

## 5.6 Coupling and orthogonality

**Coupling** is the degree to which one module depends on another. Some coupling is necessary: a caller must know a function's name and contract. The problematic kinds are:

- **content coupling:** one module reaches into another's internals;
- **common coupling:** modules share global mutable state;
- **control coupling:** one module passes flags that tell another how to behave;
- **stamp coupling:** modules share a large data structure but use only part of it;
- **temporal coupling:** modules must be called in a particular order.

**Orthogonality** is the design goal that unrelated things do not affect each other. Two modules are orthogonal if changing one does not require changing the other. The test is practical:

> If I change the requirements behind module A, how many other modules must change?

A change that ripples through five modules indicates coupling, even if no types are shared. A change contained in one module indicates a clean seam.

Orthogonality is not the same as "no dependencies." A UI depends on a domain model; that dependency is fine if it is one-directional and expressed through a stable interface. The problem is *cycles*, *hidden channels*, and *shared mutable state*.

```typescript
// Coupled through shared mutable state: both functions depend on the same array.
const auditLog: string[] = [];

function recordLogin(userId: string): void {
  auditLog.push(`login:${userId}`);
}

function recordPurchase(userId: string, cents: number): void {
  auditLog.push(`purchase:${userId}:${cents}`);
}
```

Both functions now depend on the log's representation, ordering, and lifetime. Replace the array with a `Logger` interface:

```typescript
export interface Logger {
  info(message: string): void;
}

export function recordLogin(logger: Logger, userId: string): void {
  logger.info(`login:${userId}`);
}
```

The dependency is now explicit, narrow, and substitutable. The functions are orthogonal to the log's storage.

![Unrestricted communication between subsystems.](assets/unrestricted-subsystem-communication.png)

![A few communication rules simplify subsystem interactions.](assets/restricted-subsystem-communication.png)

## 5.7 DRY: duplication of knowledge

**Don't Repeat Yourself** is often summarized as "don't copy code." The stronger and more useful formulation is:

> Every piece of knowledge in a system should have a single, authoritative representation.

The unit is *knowledge*, not text. Two identical-looking blocks may represent different concepts that happen to coincide today; merging them creates a false coupling. Two very different-looking blocks may encode the same rule; leaving them separate creates duplication that will drift.

```typescript
// Duplicated knowledge: the same tax rule in two forms.
function totalForCart(subtotal: number): number {
  return subtotal * 1.2;
}

function totalForInvoice(subtotal: number): number {
  const tax = subtotal * 0.2;
  return subtotal + tax;
}
```

The expressions differ; the rule is the same. When the rate changes, both must change. Extract the rule:

```typescript
const TAX_RATE = 0.2;

function withTax(subtotal: number): number {
  return subtotal * (1 + TAX_RATE);
}
```

Conversely:

```typescript
interface User { firstName: string; lastName: string }
interface BillingAccount { firstName: string; lastName: string }

// False duplication: these look alike but answer different questions.
function userDisplayName(user: User): string {
  return `${user.firstName} ${user.lastName}`;
}

function billingAccountName(account: BillingAccount): string {
  return `${account.firstName} ${account.lastName}`;
}
```

Merging these into one function couples the display rules of a user profile and a billing statement. They may diverge—one may use a preferred name, the other a legal name. Sameness of shape is not sameness of knowledge.

The four common sources of duplication are:

1. **Imposed duplication.** The environment or framework forces two representations (e.g., a database schema and a TypeScript type). Contain it with generation or a single mapping layer.
2. **Inadvertent duplication.** Two developers solve the same problem differently. Find it in review and unify the concept.
3. **Impatient duplication.** Copy-paste because extraction is slower right now. The interest is paid on every future change.
4. **Interdeveloper duplication.** The same utility is written by different teams because no one knows it exists. A shared catalog and naming conventions help.

## 5.8 Taking hiding too far

Information hiding is not secrecy for its own sake. An interface that hides something callers legitimately need is **obscure**, not deep.

Signs that hiding has gone too far:

- Callers must use reflection, casts, or reach into private fields to do normal work.
- The module has no way to express a legitimate variation, so callers reimplement it.
- Error messages are generic because the module hides the context needed to diagnose failures.
- Configuration is impossible, so a fork of the module appears.
- Tests must mock internal collaborators because there is no seam at the boundary.

The criterion is not "hide as much as possible." It is **hide the decisions that callers should not have to make**, and expose the ones they must. A good interface is a carefully chosen boundary between ignorance and control.

## Summary

- Hide the design decisions most likely to change; a module should own a secret.
- Information leakage means one decision lives in several modules. It is about shared knowledge, not shared lines of code.
- Temporal decomposition structures code by execution order and couples modules through implicit shared state. Prefer explicit data flow.
- Overexposure forces the common case to understand rare options. Provide simple defaults and deliberate escape hatches.
- Coupling is necessary but should be narrow, explicit, and acyclic. Orthogonality asks whether unrelated changes affect each other.
- DRY applies to knowledge: one authoritative representation. Do not merge concepts merely because their code looks alike.
- Hiding can go too far; an interface must expose what callers legitimately need.

## Exercises

1. **Find the secret.** For five modules you use regularly, write one sentence: "This module owns the decision of ___." Which modules have no answer? What would you do about them?
2. **Leakage hunt.** Find a reader/writer pair, a schema duplicated across layers, or a business rule repeated in two places. Identify the decision, give it a single owner, and write the migration steps.
3. **Temporal refactor.** Take a pipeline built around a mutable context object. Redesign it as functions with explicit inputs and outputs. What information did the context hide that now becomes visible? Was any of it legitimately private?
4. **Overexposure audit.** Find an API with more than five required options. Write the three most common call sites. Redesign the API so those call sites are one line each, while preserving the ability to configure rare cases.
5. **Orthogonality test.** Choose two modules that you believe are independent. Imagine a significant requirement change in one. List every file that would need to change. Are the modules as orthogonal as you thought?
6. **DRY or coincidence?** Find two similar functions. For each, write the question it answers and the person who owns the answer. Decide whether they represent one piece of knowledge or two. Justify your decision.
