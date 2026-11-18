# 16. Testing as a Design Activity

Tests are usually described as verification: they check that the code does what it should. That is true, and it is the least interesting thing about them. Good tests also *design* the code. They force interfaces to be usable, dependencies to be explicit, and behavior to be observable. A codebase that is hard to test is usually hard to use.

This chapter is about testing as both a quality practice and a design instrument: how to choose cases, how to structure tests, when to write them first, and where the limits of measurement lie.

## Learning objectives

- Explain how testability constrains design, and use that constraint deliberately.
- Design test cases using equivalence partitions, boundary values, and data-flow reasoning.
- Structure tests so their intent and failure messages are clear.
- Compare test-first development, test-after, and exploratory testing, and state the costs of each.
- Choose test doubles at the right seam.
- Use property-based tests for invariants that examples cannot cover.
- Interpret coverage honestly and know what it cannot tell you.
- Write tests for existing code without rewriting it first.

## 16.1 Why developers test

There are several distinct reasons, and conflating them produces bad test suites:

- **To find defects.** A test that exercises a risky path and fails is doing its job.
- **To prevent regressions.** A test that pins down existing behavior so a change cannot silently break it.
- **To document behavior.** A test shows how an API is meant to be used, better than prose.
- **To design.** Writing the test first forces the interface to be callable and the dependencies to be injectable.
- **To enable change.** A safety net makes refactoring economical.

A suite optimized only for "finding defects" tends to be exploratory and transient. A suite optimized only for "documenting behavior" tends to be exhaustive and slow. Most production suites are mostly regression tests, with a smaller number of design and documentation tests.

The design effect is the one most often ignored. If a function needs a database, a clock, and a network to test, its design has coupled policy to infrastructure. That is not a testing problem; it is a design problem that testing revealed. The remedy is a seam: a parameter, an interface, or a boundary where a deterministic substitute can be supplied.

```typescript
interface Session {
  readonly token: string;
  readonly userId: string;
  readonly createdAt: Date;
  readonly expiresAt: Date;
}

// Hard to test: the clock and the ID generator are baked in.
export function createSession(userId: string): Session {
  return {
    token: Math.random().toString(36).slice(2),
    userId,
    createdAt: new Date(),
    expiresAt: new Date(Date.now() + 3_600_000),
  };
}
```

```typescript
interface Session {
  readonly token: string;
  readonly userId: string;
  readonly createdAt: Date;
  readonly expiresAt: Date;
}

// Testable by design: the varying inputs are parameters.
export interface SessionDeps {
  readonly now: () => Date;
  readonly newToken: () => string;
}

export function createSession(
  userId: string,
  deps: SessionDeps,
): Session {
  const now = deps.now();
  return {
    token: deps.newToken(),
    userId,
    createdAt: now,
    expiresAt: new Date(now.getTime() + 3_600_000),
  };
}
```

The second version is not more complex in any meaningful sense; it has made its dependencies visible. The test can supply a fixed clock and a counter, and assert exact values.

![Developer testing takes a smaller share of total effort as projects grow.](assets/developer-testing-effort.png)

![Construction errors fall as a share of all errors as projects grow, but remain significant.](assets/defects-by-origin.png)

## 16.2 Designing test cases

A test suite is only as good as its cases. Four complementary techniques cover most situations.

### Equivalence partitioning

Divide the input space into classes that should behave the same way, and test one representative from each class. For a function that validates an age, the classes might be: negative, zero, 1–17, 18–120, and above 120. Testing three values from the middle of a class tells you little that one did not.

### Boundary values

Defects cluster at the edges of ranges. For each boundary, test the value at the boundary, just inside, and just outside. If a function accepts 1–100, test 0, 1, 100, and 101. If a string must be 1–255 characters, test 0, 1, 255, and 256.

### Data-flow reasoning

Trace each variable from definition to use. Ask:

- Is it defined on every path before use? (The classic uninitialized-variable bug.)
- Is it redefined before its previous value is used? (A dead assignment.)
- Is it used after being freed or cleared?
- Does a loop update the variables that control its termination?

### Bad data and good data

Most test suites over-test the happy path. Deliberately test:

- empty collections and empty strings;
- `undefined` and `null` where they are possible;
- malformed input (wrong type, missing field, too long);
- values at the extremes of the numeric range;
- duplicate keys, unsorted input, unexpected ordering;
- concurrent or interleaved operations;
- failure of every external dependency.

```typescript
function assertEqual<T>(actual: T, expected: T, label: string): void {
  if (!Object.is(actual, expected)) {
    throw new Error(`${label}: expected ${String(expected)}, got ${String(actual)}`);
  }
}

interface Range { readonly start: number; readonly end: number }

// Returns the overlap of two half-open ranges [start, end).
function overlap(a: Range, b: Range): Range | undefined {
  const start = Math.max(a.start, b.start);
  const end = Math.min(a.end, b.end);
  return start < end ? { start, end } : undefined;
}

// Boundary and partition cases.
assertEqual(overlap({ start: 0, end: 10 }, { start: 5, end: 15 }), { start: 5, end: 10 }, "partial overlap");
assertEqual(overlap({ start: 0, end: 10 }, { start: 0, end: 10 }), { start: 0, end: 10 }, "identical");
assertEqual(overlap({ start: 0, end: 10 }, { start: 10, end: 20 }), undefined, "touching, no overlap");
assertEqual(overlap({ start: 0, end: 10 }, { start: 2, end: 3 }), { start: 2, end: 3 }, "contained");
assertEqual(overlap({ start: 5, end: 5 }, { start: 0, end: 10 }), undefined, "empty range");
```

The "touching" case is the boundary that most implementations get wrong: two half-open ranges that meet at a point do not overlap.

## 16.3 Structure and naming

A test should say three things: **what is being tested**, **under what conditions**, and **what is expected**. The name and structure should make a failure diagnosable without reading the body.

```typescript
// Minimal assertion helper (defined in full in the previous example).
function assertEqual<T>(actual: T, expected: T, label?: string): void {
  if (!Object.is(actual, expected)) {
    throw new Error(`${label ?? "value"}: expected ${String(expected)}, got ${String(actual)}`);
  }
}

interface Charge { id: string; cents: number; refundedCents: number }
declare function refund(charge: Charge, cents: number): void;

// A clear test: the failure message names the case.
function testRefundRejectsAmountAboveCharge(): void {
  const charge = { id: "ch_1", cents: 5_000, refundedCents: 0 };
  try {
    refund(charge, 6_000);
    throw new Error("expected refund to throw");
  } catch (error) {
    if (!(error instanceof RangeError)) throw error;
    assertEqual(charge.refundedCents, 0, "no partial refund on rejection");
  }
}
```

Guidelines:

- **One behavior per test.** A test that asserts five unrelated things fails for five possible reasons and diagnoses none of them.
- **Arrange, act, assert.** Keep the three phases visually distinct; the act should be one or two lines.
- **Name the condition and the expectation.** `rejectsRefundAboveCharge`, not `testRefund2`.
- **Prefer explicit literals to shared fixtures.** A test that depends on a fixture defined elsewhere is hard to read in isolation.
- **Make failures informative.** An assertion message should include the actual and expected values and the case.
- **No logic in tests.** A test with `if` and loops is a program with its own bugs. If a matrix of cases is needed, generate the tests from a table.

```typescript
// Minimal assertion helper (defined in full in the previous example).
function assertEqual<T>(actual: T, expected: T, label?: string): void {
  if (!Object.is(actual, expected)) {
    throw new Error(`${label ?? "value"}: expected ${String(expected)}, got ${String(actual)}`);
  }
}

declare function graphemeCount(text: string): number;

const cases: readonly { readonly input: string; readonly expected: number }[] = [
  { input: "", expected: 0 },
  { input: "a", expected: 1 },
  { input: "abc", expected: 3 },
  { input: "\u{1F468}\u{200D}\u{1F469}\u{200D}\u{1F467}\u{200D}\u{1F466}", expected: 1 },
];

for (const { input, expected } of cases) {
  assertEqual(graphemeCount(input), expected, `graphemeCount(${JSON.stringify(input)})`);
}
```

The table form keeps the cases readable and the loop is trivial enough to audit.

## 16.4 Test-first development

**Test-first development (TDD)** is the practice of writing a failing test before the code that makes it pass, in short cycles:

1. **Red.** Write a test for the smallest next behavior and watch it fail for the expected reason.
2. **Green.** Write the simplest code that passes.
3. **Refactor.** Improve the design with the test as a safety net.

The claimed benefits are real: the interface is designed from the caller's perspective, coverage of new code is high by construction, and the test fails first, which proves it can fail.

The critiques are also real, and worth taking seriously:

- **Not all design benefits from tests first.** Exploratory work, UI layout, and algorithm discovery often need code before tests; writing tests against a design you have not found yet can lock in a bad interface.
- **The cycle can produce myopic designs.** A sequence of small tests can lead to a pile of small functions that no one designed as a whole.
- **Test-first is not a substitute for test design.** You can write a hundred tests of the happy path first and still miss every boundary.
- **The "simplest code that passes" can be terrible code** if the refactor step is skipped. TDD without refactoring is just tests.
- **Some teams report that it slows initial progress** and requires discipline to sustain; the payoff is in the change phase, not the first day.

A defensible position: **use test-first where the behavior is well understood and the interface matters** (parsers, business rules, APIs), and **use test-after or test-alongside where the design is being discovered** (prototypes, UI, performance work), then backfill regression tests. The important invariant is not the order; it is that the behavior ends up covered and the tests are meaningful.

## 16.5 Test doubles

A **test double** stands in for a real dependency. The common kinds:

| Double | Purpose | Risk |
|--------|---------|------|
| Stub | Returns canned values | Tests behavior against assumptions, not reality |
| Fake | A working lightweight implementation (in-memory repository) | Diverges from the real implementation over time |
| Spy | Records calls for later assertion | Couples tests to implementation details |
| Mock | Pre-programmed expectations | Brittle; fails on harmless refactors |

The design question is **where to put the seam**. The best doubles replace things that are slow, nondeterministic, or external: clocks, randomness, networks, file systems, payment providers. The worst doubles replace your own domain objects, because then the test verifies the mock rather than the behavior.

```typescript
interface User { readonly id: string; readonly email: string }

// A fake at a genuine boundary: an in-memory repository.
interface UserRepository {
  findById(id: string): Promise<User | undefined>;
  save(user: User): Promise<void>;
}

class InMemoryUserRepository implements UserRepository {
  readonly #users = new Map<string, User>();

  async findById(id: string): Promise<User | undefined> {
    return this.#users.get(id);
  }

  async save(user: User): Promise<void> {
    this.#users.set(user.id, user);
  }
}
```

The fake implements the same contract as the real repository, so tests can exercise real domain logic. It is not a mock with expectations; it is a simple, deterministic implementation.

Prefer, in order: **real object** if it is fast and deterministic, then **fake**, then **stub**, then **mock**. The further down the list, the more the test knows about implementation rather than behavior.

## 16.6 Property-based testing

Example-based tests check specific inputs. **Property-based tests** state a property that must hold for all inputs and let a generator search for counterexamples.

```typescript
interface Rng {
  nextInt(min: number, max: number): number;
}

function runProperty<T>(
  generate: (rng: Rng) => T,
  property: (value: T) => boolean,
  trials: number,
  rng: Rng,
): void {
  for (let i = 0; i < trials; i++) {
    const value = generate(rng);
    if (!property(value)) {
      throw new Error(`Property failed for ${JSON.stringify(value)}`);
    }
  }
}
```

Useful properties for common data structures:

- **Round trip:** `decode(encode(x)) === x` for all valid `x`.
- **Invariant:** sorting a list produces a permutation with non-decreasing order.
- **Idempotence:** `normalize(normalize(x)) === normalize(x)`.
- **Equivalence:** a fast implementation agrees with a slow reference on all inputs.
- **Monotonicity:** increasing an input never decreases the output.

The payoff is the counterexample: a property test often finds the empty list, the negative number, or the Unicode edge case that the example tests forgot. The cost is setup (generators, shrinking) and occasional flakiness if generators are poorly chosen. Even a hand-rolled property loop over random inputs is better than no property tests at all.

## 16.7 Coverage and its limits

**Coverage** measures which lines, branches, or paths a test suite executes. It is a useful diagnostic and a poor target.

What coverage tells you:

- Which code has never been run by any test.
- Which branches (else paths, switch cases) are untested.
- Whether a new module was added without tests.

What it does not tell you:

- Whether the assertions are meaningful. A test can execute every line and assert nothing.
- Whether the *combinations* of conditions are covered. Full branch coverage can miss interactions between two conditionals.
- Whether the tests would catch a regression. Coverage is about execution, not detection.
- Whether the behavior is correct. Coverage says "this ran," not "this is right."

A team that mandates 100% coverage gets tests that execute everything and assert little; a team that ignores coverage gets untested error paths. The useful practice is to look at **uncovered code and ask why**: is it dead, is it an error path that needs a test, or is it genuinely untestable because the design is wrong?

Mutation testing is a stronger, more expensive check: it introduces small faults and asks whether the suite catches them. If a mutant survives, the tests execute the code but do not constrain it. Mutation testing is worth running occasionally on critical modules, not as a gate on every commit.

## 16.8 Testing existing code

Legacy code—code without tests—is the normal condition of most systems. The goal is not to rewrite it; it is to create a safety net around the part you need to change.

1. **Find the seam.** Identify the smallest unit whose behavior you can observe without constructing the whole system. Often this means extracting a pure function or introducing an interface at an existing boundary.
2. **Write characterization tests.** These do not assert what the code *should* do; they assert what it *does*. Run the code, capture the output, and pin it. If the output looks wrong, note it—but the test's first job is to detect change.
3. **Refactor under the net.** With characterization tests in place, improve the structure. The tests tell you when behavior changes; if a change is intended, update the test deliberately.
4. **Add behavior tests.** Once the code is testable, write tests for the behavior you actually want, including cases the legacy code never handled.

```typescript
// Minimal assertion helper (defined in full in the previous example).
function assertEqual<T>(actual: T, expected: T, label?: string): void {
  if (!Object.is(actual, expected)) {
    throw new Error(`${label ?? "value"}: expected ${String(expected)}, got ${String(actual)}`);
  }
}

declare function legacyDiscount(cents: number): number;

// A characterization test: pin current behavior, including the odd bits.
function characterizeLegacyDiscount(): void {
  // Observed: the legacy code rounds down, not half-up.
  assertEqual(legacyDiscount(1_999), 199, "legacy rounds down");
  assertEqual(legacyDiscount(0), 0, "zero stays zero");
  // Observed: negative input returns the input unchanged (probably a bug).
  assertEqual(legacyDiscount(-100), -100, "negative passes through");
}
```

Pinning a bug is uncomfortable, and it is the right first move: the test documents reality, and changing reality becomes a deliberate act rather than an accident.

## Summary

- Tests verify behavior, prevent regressions, document usage, and shape design; a hard-to-test design is usually a badly coupled one.
- Choose cases with equivalence partitions, boundary values, data-flow reasoning, and deliberate bad data.
- Structure tests around one behavior, with clear names, explicit inputs, and informative failures.
- Test-first development has real benefits and real limits; the invariant is meaningful coverage, not the order of writing.
- Put test doubles at genuine boundaries: prefer real objects, then fakes, then stubs, then mocks.
- Property-based tests find the cases examples miss; state invariants, round trips, and equivalences.
- Coverage finds untested code; it does not prove correctness. Investigate uncovered code rather than chasing a number.
- Test legacy code by finding a seam, pinning current behavior, refactoring under the net, then specifying the behavior you want.

## Exercises

1. **Partition a function.** Pick a function with numeric or string input. List its equivalence classes and boundary values. Compare that list with the tests that exist. What is missing?
2. **Design for testability.** Find a function that constructs its own dependencies (clock, random, network). Introduce parameters for them and write a deterministic test.
3. **Bad-data pass.** Write five tests using only invalid or edge-case input for a module that currently has only happy-path tests. Did any fail?
4. **Double choice.** For three dependencies in a test, decide whether to use the real object, a fake, a stub, or a mock. Justify each with the risk it introduces.
5. **Property test.** Write a property for a function you own (round trip, idempotence, or equivalence with a slow reference). Run it against a few hundred generated inputs. What counterexample did it find?
6. **Coverage investigation.** Run coverage on a module. For each uncovered region, classify it as dead code, untested error path, or untestable-by-design. Fix one of each category.
7. **Characterize legacy.** Choose a legacy function with no tests. Write characterization tests for its current behavior, including any behavior that looks wrong. Then make one small refactor and confirm the tests still pass.
8. **TDD trial.** Implement a small, well-specified feature test-first for one hour. Note where the cycle helped and where it got in the way. Write down the conditions under which you would use it again.
