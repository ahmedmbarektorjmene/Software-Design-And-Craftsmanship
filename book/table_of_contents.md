# Contents

*Design, construction, and judgment in practice*

---

## Front Matter

- Preface
- How to Read This Book
- A Note on the TypeScript Examples

## Part I — Foundations of Design

**1. Software Craftsmanship and the Construction of Systems**  
What construction is; why it is the central activity; metaphors and their limits; the craft stance; the place of design.

**2. Complexity: The Primary Technical Imperative**  
A working definition; the three symptoms; the two causes; why complexity is incremental; essential vs. accidental complexity; measuring what can be measured.

**3. Strategic Programming and the Economics of Design**  
Tactical vs. strategic work; technical debt; the investment model; broken windows; good-enough software vs. design health; quality as an explicit target.

## Part II — Designing Modules

**4. Deep Modules and Good Abstractions**  
Modularity; interfaces, formal and informal; abstraction; depth and shallowness; classitis; worked examples in TypeScript.

**5. Information Hiding, Leakage, and Coupling**  
information hiding as a design criterion; information leakage; temporal decomposition; overexposure; coupling and orthogonality; duplication of knowledge; hiding inside a class; taking hiding too far.

**6. Generality, Separation, and Composition**  
Somewhat general-purpose modules; separating general from special; better together or better apart; pass-through methods; decorators; pulling complexity downward; configuration.

**7. Interfaces, Types, and Object Design**  
Abstract data types; designing class interfaces; constructors and invariants; inheritance and composition; getters, setters, and Tell-Don't-Ask; enums and unions; modules and packages.

**8. Errors, Contracts, and Defensive Design**  
A taxonomy of failure; design by contract; assertions; exceptions and result types; define errors out of existence; fail fast; barricades and boundaries; resource ownership; the three-way debate.

**9. Finding the Design: Iteration, Prototypes, and Alternatives**  
Design as a process; design it twice; heuristics for decomposition; prototypes vs. tracer bullets; domain languages; reversibility; recording decisions.

## Part III — Constructing Code

**10. Naming**  
Names as compression; precision; consistency; length and scope; conventions; renaming; names that reveal design problems.

**11. Comments and Documentation**  
The four excuses; what comments can say that code cannot; interface vs. implementation comments; comments-first; TSDoc; maintaining comments; the self-documenting-code debate.

**12. Routines and the Pseudocode Programming Process**  
Why routines exist; cohesion; size; parameters; command-query separation; PPP; structured programming; functional style in TypeScript.

**13. Control Flow**  
Ordering dependencies; conditionals; loops; nesting; early exits; recursion; exceptions as control flow; table-driven dispatch; complexity of control flow.

**14. Variables, Data, and State**  
Scope and lifetime; initialization; immutability; globals; primitive types and their traps; strings and Unicode; enums and discriminated unions; magic numbers; binding time.

**15. Layout, Style, and Obvious Code**  
What layout is for; consistency; formatting as communication; obviousness tests; simplicity vs. cleverness; comments in layout; tooling.

## Part IV — Verification and Evolution

**16. Testing as a Design Activity**  
Why developers test; test-case design (basis, boundary, data flow, bad/good data); TDD and its critics; property-based testing; coverage and its limits; test doubles; regression suites; testing legacy code.

**17. Debugging**  
The scientific method; reproducing; locating; understanding; fixing; regression tests; tools; psychology; debugging production.

**18. Refactoring and the Care of Existing Code**  
Why code decays; smells; representative refactorings; safety; strategies; refactoring vs. rewriting; maintaining comments; consistency with existing code.

**19. Performance and Algorithmic Thinking**  
Performance as a requirement; measurement; profiling; algorithmic order; critical-path design; tuning techniques that still matter; the cost of optimization.

**20. Concurrency, Events, and Data-Driven Design**  
Temporal coupling; shared state; actors and message passing; events and streams; blackboards; async/await in TypeScript; state machines and tables; pipelines.

## Part V — Projects and People

**21. Requirements, Architecture, and Estimation**  
Problem definition; requirements as a feedback loop; architecture and its prerequisites; reversibility; estimation methods; uncertainty and ranges.

**22. Tools, Automation, and Integration**  
The toolchain as leverage; plain text; shell and scripting; editors; version control; build and CI; incremental integration; daily builds; measurement.

**23. Teams, Reviews, and Communication**  
Communication as engineering; code review and inspections; pair programming; team size and structure; documentation; security practice; ethics.

**24. Craftsmanship as a Practice**  
Career ownership; the knowledge portfolio; deliberate practice; character and habits; pride, honesty, and responsibility; avoiding cargo cults.

## Part VI — Judgment

**25. Design Judgment: A Field Guide**  
How to decide; where the experts disagree; a decision framework; design review questions; the red-flag catalog; exercises for continued practice.

---

## Reading paths

| Reader | Path |
|--------|------|
| New developer | 1–5, 8, 10–15, 16–18, 21, 24 |
| Experienced developer | 2–9, 11–12, 16, 19–20, 25 |
| Tech lead / architect | 2–9, 16, 21–25 |
| Preparing for design review | 4–9, 21, 25 |
| Working on legacy code | 5, 8, 11, 14, 16–18, 25 |
