# Preface

This book is about the part of programming that does not fit in a language reference: how to decide what a system should look like, how to keep it understandable as it grows, and how to work in a way that leaves the code better than you found it.

It is organized by subject rather than by technique or by tool. Each chapter takes one recurring problem—complexity, module boundaries, naming, errors, testing, concurrency, estimation—and works through the principles, the trade-offs, and the places where experienced practitioners legitimately disagree. The aim is not to hand you rules. Rules fail at the edges, and most of the interesting work happens at the edges. The aim is to give you enough understanding of the forces that you can make a defensible decision in a situation no rule anticipated.

Three convictions run through the book.

**Design is continuous.** The split between "design" and "coding" is a convenience for planning, not a description of the work. Structure is decided in small increments every day: where a function goes, what a type allows, which module owns a decision. A team that treats design as a phase tends to stop designing when the phase ends.

**Complexity is the constraint.** Features, deadlines, and technologies come and go; the thing that determines whether a system can keep changing is how much a person must know to make a safe change. Almost every principle in this book is a way of reducing that burden or of keeping it from growing.

**Judgment beats doctrine.** Test-first development, small functions, comments, inheritance, up-front design, and quality thresholds all have passionate advocates and real counterexamples. This book presents the positions and the conditions under which each is strongest, rather than declaring a winner. Where the field disagrees, the disagreement is information.

The code is TypeScript, chosen because its type system can express design intent—unions, readonly data, exhaustive checks—without hiding the runtime behavior. The examples are small, self-contained, and compiled under strict settings. They are meant to be read closely, not copied blindly: the point is the shape of the decision, not the particular syntax.

# How to Read This Book

The chapters are in a deliberate order. Part I establishes the vocabulary: what craftsmanship means here, what complexity is, and why strategic investment pays. Part II is about drawing boundaries: modules, information hiding, generality, interfaces, errors, and the process of finding a design. Part III is about constructing code inside those boundaries: naming, comments, routines, control flow, data, and layout. Part IV covers verification and evolution: testing, debugging, refactoring, performance, concurrency. Part V widens the frame to projects and people: requirements and estimation, tooling, teams, and professional practice. Part VI is a field guide to judgment, including where experts disagree.

You do not have to read it straight through. Three paths work well:

- **New to professional programming:** read Parts I and III first, then testing and refactoring (16–18), then requirements (21) and craftsmanship (24).
- **Experienced developer:** read complexity and strategic programming (2–3), the module chapters (4–9), then testing, performance, concurrency, and judgment (16, 19–20, 25).
- **Tech lead or architect:** read the module and error chapters (4–9), then architecture and estimation (21), teams (23), and judgment (25), with the review questions in Chapter 25 as a working checklist.

Each chapter opens with a scenario, states its learning objectives, develops one subject, and ends with a summary and exercises. The exercises are the point. Reading about design changes what you notice; doing the exercises changes what you can do.

Cross-references are to chapter numbers. When a concept is introduced elsewhere, the first mention points to it; later mentions assume you have read it or can return to it.

# A Note on the TypeScript Examples

Every code example is TypeScript 5.9 or later, compiled with `strict` enabled and targeting ES2022. The examples follow a few conventions:

- **No `any` without a stated reason.** Values of unknown shape are typed `unknown` and narrowed.
- **External dependencies are declared, not imported.** A snippet that needs a clock, a database, or a network declares a minimal interface, so the seam that makes the code testable is visible.
- **Units live in names.** `timeoutMs`, `amountCents`, `weightKg`. The type is `number`; the name says which number.
- **Unions model alternatives.** String-literal unions and discriminated unions replace booleans and magic strings wherever the set of possibilities is closed.
- **Switches are exhaustive.** A `never` assignment in the default branch turns a missing case into a compile error.
- **Readonly is the default.** Interfaces use `readonly` properties and `readonly T[]` arrays unless mutation is the point.

Some snippets are fragments rather than complete programs: they show an interface, a function, or a before/after pair. Where a fragment would not compile alone, a declaration or a minimal type is included so that it does. The examples are checked as a set; if you retype one, expect to supply the surrounding declarations.

Performance numbers, library behaviors, and language features are described as of the mid-2020s. Treat specific figures as orders of magnitude, and verify current behavior against your own toolchain.

---
