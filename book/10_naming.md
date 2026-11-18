# 10. Naming

A name is the smallest and most frequently used interface in a program. It is read every time the code is opened, every time a stack trace appears, every time an autocomplete list is consulted. A good name compresses a paragraph of explanation into a few words; a bad name forces the reader to reconstruct that paragraph from the implementation.

Naming is also a design diagnostic. When a precise name is hard to find, the concept is often muddled. The difficulty is information: it tells you that the thing being named has not yet been understood.

## Learning objectives

- Explain what a name must convey, and why naming is a design activity.
- Choose precise names that encode units, constraints, and roles.
- Apply naming conventions consistently across types, values, functions, and constants.
- Set name length by scope and importance rather than by habit.
- Use renaming as a refactoring tool and recognize names that signal design problems.
- Avoid TypeScript-specific naming traps.

## 10.1 What a name conveys

A name should answer the questions a reader will have at the point of use:

- **What is it?** A value, a function, a type, a module.
- **What is its purpose?** What it represents or what it does.
- **What are its units or format?** Milliseconds, cents, kilograms, UTF-16 code units.
- **What are its constraints?** Positive, non-empty, sorted, unique, normalized.
- **How does it relate to its neighbors?** Is `total` the same as `subtotal + tax`, or a different concept?

A name cannot answer all of these in every context, and it should not try. The art is to encode the facts that are **not obvious from the type and the surrounding code**. If the type is `number`, the unit is not obvious and belongs in the name. If the type is `UserId`, the role is already clear and the name can be shorter.

```typescript
// Vague: what is the number? What does the function do?
function processData(data: number[], value: number): number[] {
  return data.map((item) => item * value);
}

// Precise: unit, role, and operation are visible.
function scalePricesCents(pricesCents: readonly number[], factor: number): number[] {
  return pricesCents.map((cents) => Math.round(cents * factor));
}
```

The second version is longer, but it is shorter to *understand*. It tells the reader that the input is in cents, that the output is scaled and rounded, and that the operation is a price adjustment. The first version requires reading the body and guessing.

## 10.2 Precision

Precision is the most important naming property. A precise name distinguishes the thing from its neighbors and rules out plausible misinterpretations.

**Avoid vague nouns.** `data`, `info`, `item`, `object`, `record`, `entry`, `value`, `result`, `manager`, `handler`, `processor`, `service`, `util`, `helper`. These words are not forbidden, but they usually signal that the author has not decided what the thing is. `UserData` and `UserInfo` are indistinguishable; `UserProfile` and `UserCredentials` are not.

**Avoid vague verbs.** `handle`, `process`, `manage`, `do`, `perform`, `execute`, `run`. They describe activity without describing effect. `handleClick` might open a menu or submit a form; `submitOrder` does one thing.

**Encode units and formats when the type does not.** `timeoutMs`, `weightKg`, `priceCents`, `createdAtIso`, `pathFromRoot`. A `Date` object makes the format clear; a `number` or `string` does not.

**Distinguish similar concepts.** `count` (how many), `total` (sum), `size` (capacity or length), `length` (number of elements), `capacity` (maximum). Pick one meaning per word and use it consistently.

**Name booleans as predicates.** `isActive`, `hasAccess`, `canRetry`, `shouldNotify`. A boolean named `status` or `flag` forces the reader to discover what `true` means.

**Name functions by what they return or do.** A function that returns a value should be named for the value (`calculateTotal`, `findUser`); a function that mutates should be named for the effect (`applyDiscount`, `markShipped`). Avoid names that could be either (`update` is usually too vague).

**Avoid misleading names.** A `getUser` that creates a user on demand is lying. A `cache` that never evicts is not a cache. A name that is technically true but pragmatically misleading is worse than a vague one.

| Weak | Better | Why |
|------|--------|-----|
| `data` | `orderLines` | Names the content |
| `flag` | `isPublished` | Names the condition |
| `handleSubmit` | `submitOrder` | Names the effect |
| `timeout` | `timeoutMs` | Names the unit |
| `Manager` | `SubscriptionRenewer` | Names the responsibility |
| `getUser` (creates) | `getOrCreateUser` | Tells the truth |

## 10.3 Consistency

Consistency reduces cognitive load: the reader learns a vocabulary once and can apply it everywhere. Inconsistency forces re-learning at every site.

Rules worth enforcing:

- **Same concept, same word.** If a thing is a `Customer` in the domain, do not call it `Client` in one module, `Account` in another, and `Buyer` in a third—unless those are genuinely different concepts.
- **Different concept, different word.** Do not use `total` for both the pre-tax subtotal and the final amount. Do not use `id` for both a database key and a display identifier.
- **Consistent grammatical roles.** Types are nouns (`Invoice`), functions are verb phrases (`calculateTotal`), predicates are `is/has/can` questions.
- **Consistent affixes.** If `parseX` returns a value and `tryParseX` returns a result, apply the convention everywhere.
- **Consistent abbreviations.** If `config` is the standard short form, do not mix `cfg`, `conf`, and `configuration` in the same codebase.

A project glossary helps when the domain has many terms. It can be as small as a table in the repository: term, definition, example, and the code name. The glossary is also a design tool: if two teams define `Account` differently, the code will too.

## 10.4 Conventions

Conventions are not about taste; they are about reducing surprise. A typical TypeScript convention set:

| Kind | Convention | Example |
|------|------------|---------|
| Type, interface, class, enum | `PascalCase` | `Invoice`, `PaymentMethod` |
| Variable, parameter, function | `camelCase` | `invoiceTotal`, `calculateTax` |
| Constant (module-level, immutable) | `UPPER_SNAKE_CASE` | `MAX_RETRY_ATTEMPTS` |
| Private class field | `#camelCase` | `#balanceCents` |
| Boolean | `is/has/can/should` prefix | `isSettled`, `hasRefund` |
| Generic type parameter | Single capital or descriptive | `T`, `TResult`, `TError` |
| File | `kebab-case` or project standard | `invoice-repository.ts` |

The specific choices matter less than the consistency. A codebase that uses `PascalCase` for types and `camelCase` for values is easier to scan than one that mixes both arbitrarily.

Some conventions are actively harmful in TypeScript:

- **Hungarian notation for types** (`strName`, `iCount`) duplicates information the type system already provides and quickly becomes stale.
- **`I` prefixes for interfaces** (`IUser`) add noise; the language does not need the distinction, and the prefix often correlates with an anemic abstraction.
- **Encoding mutability or visibility in names** (`m_`, `s_`) is unnecessary with `#private` fields and modules.
- **Abbreviations that save three characters but cost a lookup** (`usr`, `acct`, `qty` are common enough in some domains, but `rcrd`, `prcs`, `cfg` often are not).

## 10.5 Length

Name length should be proportional to **scope** and **importance**:

- A loop index used in three lines can be `i`.
- A local variable in a twenty-line function can be short but descriptive (`total`, `user`).
- A parameter or field used across a class should be precise (`remainingBalanceCents`).
- A public API name is read by everyone and should be unambiguous, even if long.

The old advice to keep names under eight characters is obsolete. Modern editors autocomplete; readers do not. A long, precise name is better than a short, ambiguous one, provided it is not padded with noise.

**Avoid padding.** `numberOfItemsInTheCart` can be `itemCount` if the context is clear. `getUserByIdFromDatabase` can be `findUserById` if the repository is already the context. Extra words dilute the signal.

**Avoid cryptic brevity.** `calcTtl` might mean "calculate total" or "time to live." If a reader has to guess, the name is too short.

The right length is the shortest name that a competent reader, unfamiliar with this file, can understand without reading the body.

## 10.6 Renaming as a design tool

Renaming is cheap in a modern editor and expensive in a codebase without one. Do it often:

- When you understand a concept better, rename it to match.
- When a name turns out to be misleading, fix it before it spreads.
- When a function grows a second responsibility, rename it to reflect the new scope—or split it.

Renaming is also a **design probe**. If you cannot find a precise name, ask why:

- Does the function do more than one thing?
- Is the concept actually two concepts?
- Is the data structure carrying unrelated fields?
- Is the module's responsibility unclear?

A name that is hard to choose is a signal, not a failure of vocabulary. The red flag "hard to pick a name" usually means the design is not yet clear.

For public APIs, renaming has a cost. Deprecate the old name, provide an alias for a transition period, and document the migration. For internal code, rename aggressively; the compiler and tests will tell you what broke.

## 10.7 TypeScript-specific naming notes

- **Do not encode types in names** unless the type is genuinely ambiguous (`userId` is fine; `userIdString` is usually not).
- **Use `readonly` and types to express constraints** instead of names like `immutableItems` or `nonEmptyList`.
- **Name generic parameters meaningfully** when there is more than one: `TKey`, `TValue` beat `T`, `U` in a public API.
- **Name discriminated unions by the discriminant** (`kind`, `type`, `status`) and use the same discriminant name across the codebase.
- **Avoid names that shadow globals** (`name`, `status`, `location`, `event`, `history`) in browser code; shadowing makes debugging harder.
- **Use `is`/`asserts` naming for type guards** (`isUser`, `assertUser`) so the type-system effect is visible.

```typescript
interface User { readonly id: string; readonly email: string }

function isUser(value: unknown): value is User {
  if (typeof value !== "object" || value === null) return false;
  const record = value as Record<string, unknown>;
  return typeof record.id === "string" && typeof record.email === "string";
}

function assertUser(value: unknown): asserts value is User {
  if (!isUser(value)) throw new TypeError("Expected a User");
}
```

The names state the contract: `isUser` answers a question, `assertUser` narrows or throws.

## Summary

- A name is an interface; it should convey purpose, units, constraints, and role without requiring the implementation.
- Precision beats brevity: avoid vague nouns and verbs, encode units when the type does not, and distinguish similar concepts.
- Consistency is a multiplier: same concept same word, different concept different word, stable grammatical roles.
- Conventions reduce surprise; choose a set and apply it everywhere. Avoid type-encoding and Hungarian notation in TypeScript.
- Name length should scale with scope and importance, not with an arbitrary character limit.
- Rename freely; a hard-to-name concept often signals a design problem.

## Exercises

1. **Rename a function.** Find a function named with a vague verb (`handle`, `process`, `manage`). Read its body and write three candidate names. Choose one that states the effect and the unit or domain.
2. **Unit audit.** Find numeric variables and parameters whose unit is not in the name. Rename them to include the unit, and update the call sites. Did any ambiguity disappear?
3. **Consistency check.** Search your codebase for synonyms of one concept (customer, client, account, buyer). Count the occurrences. Pick one term, document the choice, and plan the rename.
4. **Boolean names.** Find five boolean variables or properties. Rename them as predicates. Which ones revealed a hidden third state (e.g., `isLoading` vs. `hasLoaded` vs. `hasError`)?
5. **Name as a probe.** Choose an entity whose name you have never liked. Try to name it precisely in one sentence. If you cannot, what does that reveal about its responsibilities?
6. **Convention proposal.** Write a one-page naming convention for a TypeScript project: types, values, constants, booleans, files, generics, and tests. Include three examples and three anti-examples.
