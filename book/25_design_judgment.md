# 25. Design Judgment: A Field Guide

The previous chapters describe principles, techniques, and trade-offs. None of them decides for you. A principle is a compressed lesson from many contexts; your context is one. Judgment is the skill of applying principles to a situation that does not exactly match any of them.

This chapter is a field guide to that skill: how decisions get made, a procedure for making them deliberately, the places where experienced practitioners disagree, and the questions worth asking when you are unsure.

## Learning objectives

- Describe how design decisions are actually made under uncertainty.
- Apply a repeatable decision procedure to a significant design choice.
- Recognize the major disagreements in the field and the conditions that favor each position.
- Use context factors—scale, lifespan, team, risk—to choose between competing goods.
- Run a design review with questions that surface real risks.
- Continue developing judgment deliberately.

## 25.1 How decisions actually get made

Design decisions are rarely a matter of deducing the right answer. They are made by pattern recognition, analogy, constraint satisfaction, and social negotiation:

- **Pattern recognition.** "This looks like the caching problem I solved before; here is what went wrong there."
- **Analogy.** "This is a compiler pipeline; separate the stages."
- **Constraint satisfaction.** "We have four engineers, six weeks, and an existing Postgres cluster. That rules out three options."
- **Social negotiation.** "The team that owns the billing service will not accept a synchronous dependency."
- **Precedent.** "We do it this way here, and changing that costs more than the improvement is worth."

None of these is irrational. The mistake is treating them as if they were deduction: assuming the pattern fits, the analogy holds, or the constraint is immutable. Good designers make these moves *and* check them.

Two failure modes dominate:

**Premature convergence.** The first plausible design becomes the design. Alternatives are never generated, so the team never learns that a better one existed. The remedy is to design it twice (Chapter 9).

**Endless deliberation.** Every option is analyzed, no decision is made, and the cost of delay exceeds the cost of a wrong choice. The remedy is to recognize which decisions are reversible and to make those quickly.

## 25.2 A decision procedure

For a significant decision, a repeatable procedure beats intuition alone—not because intuition is wrong, but because the procedure surfaces what intuition skipped.

**1. Frame the decision.** Write the question in one sentence: "Should the pricing rules live in code or in a data table?" A vague frame ("how should we do pricing?") produces vague answers.

**2. State the constraints.** Time, team, budget, existing systems, regulatory requirements, performance targets. Constraints eliminate options cheaply.

**3. Generate at least two real alternatives.** Different decomposition, different ownership, different representation, different boundary. If both alternatives share the same core assumption, you have one alternative, not two.

**4. Evaluate against criteria.** Use a small set of criteria that reflect what matters here:

| Criterion | Question |
|-----------|----------|
| Correctness | Does it satisfy the requirements, including edge cases? |
| Simplicity | How much must a new developer learn? |
| Change cost | How many places change when a likely requirement changes? |
| Reversibility | How expensive is it to undo? |
| Testability | Can the behavior be verified without the world? |
| Operability | Can it be deployed, monitored, and debugged? |
| Team fit | Does the team have the skills and the capacity? |

**5. Choose, and state why.** The reason matters more than the choice, because it tells the next person when to revisit.

**6. Record it.** A short decision record: context, decision, alternatives, consequences, revisit trigger (Chapter 9).

**7. Set a review point.** When will you know whether it was right? A metric, a date, or an event.

```typescript
interface DecisionRecord {
  readonly title: string;
  readonly context: string;
  readonly decision: string;
  readonly alternatives: readonly string[];
  readonly consequences: readonly string[];
  readonly revisitWhen: string;
}

const pricingDecision: DecisionRecord = {
  title: "Pricing rules as data, not code",
  context: "Marketing changes discount rules weekly; each change currently requires a deploy.",
  decision: "Store rules as typed rows in the pricing table; evaluate with one engine.",
  alternatives: [
    "Rule classes compiled into the service (faster, but requires a deploy per change)",
    "A separate rules service (independent, but another network hop and deployment)",
  ],
  consequences: [
    "Rules become reviewable by non-engineers",
    "The engine's semantics must be documented and tested exhaustively",
  ],
  revisitWhen: "rules require cross-rule state or per-customer scripting",
};
```

The record is not bureaucracy. It is the difference between a decision and an accident.

## 25.3 Where experts disagree

Competent practitioners disagree about several recurring questions. The disagreements are not failures of the field; they reflect different weightings of real costs. Knowing the positions makes you harder to fool—including by yourself.

### Test-first development

- **Test-first:** writing the failing test first designs the interface from the caller's perspective, guarantees that the test can fail, and produces high coverage of new code. The cycle (red, green, refactor) keeps steps small.
- **Test-after / test-alongside:** some designs are discovered, not specified. Writing tests against an unknown interface locks in a bad shape. Exploratory work, UI, and performance tuning often need code first.

**Where the weight falls:** well-understood behavior with a stable interface favors test-first; discovery work favors test-after with regression tests backfilled. The invariant both sides accept: the behavior must end up covered by meaningful tests.

### Comments

- **Comments-first:** code expresses mechanism; comments express intent, contract, and rationale. Interface comments are a design tool; writing them before the body exposes gaps in the interface.
- **Self-documenting code:** if code needs extensive comments, improve the code—better names, smaller functions, clearer types. Comments drift and are often noise.

**Where the weight falls:** both agree that comments restating code are waste. The difference is emphasis and volume. Domains with regulatory or safety requirements, and interfaces with subtle contracts, favor substantial documentation; small, well-named code with obvious intent favors sparse comments.

### Function size

- **Small functions:** a function should do one thing; short functions are easier to name, test, and reuse.
- **Coherent units:** hard line limits produce shallow, fragmented code where understanding one operation requires visiting ten functions. A longer function that hides a coherent algorithm can be deeper than five one-line functions.

**Where the weight falls:** cohesion and nameability, not line count. Extract when a block has a nameable purpose; keep together when the steps only make sense as a whole.

### Error handling

- **Define errors out of existence:** redesign operations so common failures become defined results. Fewer branches, simpler callers.
- **Fail fast:** do not continue with corrupt state; assert invariants and stop.
- **Defend and recover:** validate at boundaries, handle expected failures, keep the system running.

**Where the weight falls:** by failure class. Expected domain failures favor explicit results; programmer errors favor assertions; transient environmental failures favor retry and fallback. Most arguments here are really disagreements about classification.

### Getters and setters

- **Avoid mechanical accessors:** a getter/setter pair exposing a field is a public field with ceremony; it invites callers to own the object's rules.
- **Accessors at boundaries:** serialization, frameworks, debugging, and migration need to read state; a getter preserves the ability to change representation, and a setter can validate.
- **Tell, don't ask:** prefer asking an object to perform an operation over extracting state, deciding outside, and writing it back.

**Where the weight falls:** accessors are justified when they enforce an invariant or serve a real boundary; they are noise when they exist only because "fields should be private."

### Up-front design

- **Design before building:** architecture decisions are expensive to reverse; thinking before coding prevents costly rework.
- **Emergent design:** requirements change too fast for elaborate up-front design; the design should emerge from small, tested increments and continuous refactoring.

**Where the weight falls:** the cost of reversal. Expensive, hard-to-reverse decisions (data model, integration style, public contracts) deserve deliberate up-front work. Cheap, reversible decisions are better made by building and adjusting.

### Good-enough quality

- **Ship good-enough software:** perfection is unattainable and delay has a cost; users benefit from adequate software now, and feedback improves it.
- **Do not ship known defects:** quality is not a dial to turn down under pressure; the defects you ship become tomorrow's incidents and next year's legacy.

**Where the weight falls:** the consequence of failure. Internal tools tolerate rough edges; payment systems, medical devices, and security boundaries do not. "Good enough" is a judgment about consequences, not an excuse for carelessness.

### Complexity metrics

- **Measure complexity:** cyclomatic complexity, coupling metrics, and code churn identify hotspots and guide refactoring.
- **Metrics mislead:** a number cannot capture readability; teams optimize the metric (shorter functions, lower counts) without improving the design.

**Where the weight falls:** metrics are diagnostic, not targets. Use them to find code worth reading, then judge with reading.

## 25.4 Context decides

When principles conflict, context breaks the tie. The factors that matter most:

**Scale.** Ten users or ten million. A design that is elegant at small scale can be an operational burden at large scale, and vice versa.

**Lifespan.** A script that runs once versus a system that must survive a decade. Longevity justifies documentation, tests, and reversibility; a throwaway script justifies none of them.

**Team size and skill.** A pattern that a large team needs for coordination may be overhead for three people. A technique that requires expertise is a liability if nobody on the team has it.

**Risk and consequence.** A prototype and a payment ledger deserve different rigor. Match the process to the cost of failure.

**Rate of change.** Stable requirements reward up-front design; volatile requirements reward reversibility and small increments.

**Existing constraints.** The database you already run, the language your team knows, the compliance regime you operate under. These are not excuses; they are the actual problem.

A useful habit: before applying a principle, name the context factor that makes it apply. If you cannot, you may be applying it by habit.

## 25.5 Design review questions

A design review is a conversation structured to find risks early. Good questions, in rough order:

**Problem and scope**
- What problem does this solve, and for whom?
- What happens if we do nothing?
- What is explicitly out of scope?

**Structure**
- What are the modules, and what does each hide?
- Where does the data live, and who owns it?
- Which dependencies point which way? Are there cycles?
- What is the common case, and is it simple?

**Change**
- What is most likely to change in the next year?
- If it changes, how many modules change?
- Which decisions are expensive to reverse, and are they isolated?

**Failure**
- What happens when each dependency fails?
- What happens at the boundaries: empty, huge, malformed, concurrent?
- How will we know in production that something is wrong?

**Verification**
- How will this be tested without the world?
- What is the riskiest behavior, and what test covers it?

**People**
- Who owns this after it ships?
- What must a new team member learn to work on it?
- What are we unsure about, and how will we find out?

The questions are not a checklist to complete; they are probes. Two or three that produce uncomfortable silence are worth more than twenty that produce agreement.

## 25.6 Red flags

A red flag is a pattern that often precedes a problem. The ones worth carrying in your head:

- A name that is hard to choose.
- A function that needs a comment to explain what it does.
- A parameter that is always passed the same value.
- A module that knows about more than one unrelated thing.
- Two modules that must change together.
- A test that asserts nothing, or asserts on a mock.
- A global that two tests must reset.
- A cache with no invalidation story.
- An error that is caught and ignored.
- A configuration option nobody can explain.
- A design decision that only one person understands.

None of these is proof of a defect. Each is a prompt to look.

## 25.7 Developing judgment

Judgment improves through **decisions with feedback**. Reading about design helps; making decisions and living with the consequences helps more.

Practices that accelerate it:

- **Keep a decision journal.** Record what you decided, what you expected, and what happened. Review it quarterly. Patterns in your errors become visible.
- **Predict, then check.** Before a change, write down what you expect: how long it will take, what will break, where the defect will be. Compare. Calibration is a skill.
- **Study failures.** Post-incident reviews, your own and others', are the densest source of design lessons available.
- **Review others' designs.** Ask the questions in §25.5 of a design you did not write. You will notice patterns faster in someone else's work.
- **Revisit old decisions.** Read code you wrote two years ago. What did you know then that you would not do now? What did you not know that you now take for granted?
- **Teach.** Explaining a trade-off forces you to state the conditions under which each side wins.

The goal is not certainty. It is to be **less wrong, faster**—to notice the wrong assumption earlier, to choose the reversible option when unsure, and to leave a record that helps the next person do the same.

## Summary

- Design decisions are made by pattern recognition, analogy, constraints, and negotiation; the skill is checking those moves rather than trusting them.
- Use a repeatable procedure: frame, constrain, generate alternatives, evaluate, choose with reasons, record, and set a review point.
- Competent practitioners disagree about TDD, comments, function size, error strategy, accessors, up-front design, and quality thresholds; context decides.
- Scale, lifespan, team, risk, rate of change, and existing constraints are the factors that break ties.
- Design reviews find risks through probes, not checklists; a few uncomfortable questions beat many agreeable ones.
- Red flags are prompts to look, not verdicts.
- Judgment develops through decisions with feedback: a journal, predictions checked against outcomes, failure reviews, and teaching.

## Exercises

1. **Decision procedure.** Apply the seven-step procedure to a decision you are facing. Write the record, including the revisit trigger.
2. **Two alternatives.** For that decision, generate a genuinely different second option. What assumption did both share, and what happened when you broke it?
3. **Position mapping.** Choose one disagreement from §25.3. Write the strongest argument for each side, then state which context factors would make you choose each.
4. **Context audit.** Take a principle from this book that you apply habitually. Name the context factor that makes it right for you, and a context where it would be wrong.
5. **Review someone else's design.** Use the questions in §25.5 on a design you did not write. Which question produced the most useful discussion?
6. **Red-flag sweep.** Scan a module for the red flags in §25.6. For each hit, decide whether it is a real problem or an acceptable trade-off, and why.
7. **Calibration.** For the next five tasks, predict duration, likely defect location, and what will surprise you. Compare with what happened. What is your bias?
8. **Old code review.** Read code you wrote two years ago. List three decisions you would reverse and three you would keep. What does the list say about how your judgment has changed?
