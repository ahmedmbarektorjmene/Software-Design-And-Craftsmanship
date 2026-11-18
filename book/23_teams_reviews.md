# 23. Teams, Reviews, and Communication

Software is built by people, for people. The technical quality of a system is inseparable from how its team communicates: what is written down, what is reviewed, what is assumed, and what is never said. A brilliant design that nobody understands is not a design; it is a private artifact.

This chapter is about the human infrastructure around the code: review, pairing, team shape, documentation, security practice, and professional ethics.

## Learning objectives

- Treat communication as an engineering concern with measurable costs.
- Run code reviews that improve the code and the reviewer.
- Choose between review, pairing, and solo work based on risk and learning goals.
- Explain how team size and structure shape architecture.
- Write documentation that survives its author.
- Apply security practices as design constraints rather than afterthoughts.
- Recognize the ethical dimensions of design decisions.

## 23.1 Communication is engineering

Every misunderstanding has a cost: a requirement built wrong, an interface used incorrectly, a defect that two people each assumed the other had checked. These costs are as real as a slow query, and they scale with team size.

Communication costs grow faster than the team. With *n* people there are *n(n−1)/2* pairwise channels; adding a tenth person adds nine relationships, not one. This is the arithmetic behind the observation that adding people to a late project makes it later: new people consume the attention of the people who already know the system.

The engineering response is to reduce the need for communication by making information **persistent and self-serve**:

- **Written decisions.** A decision recorded in a repository outlives the meeting and reaches people who were not there.
- **Explicit interfaces.** A well-documented type reduces the questions a caller must ask.
- **Automated checks.** A linter or type check communicates a rule to everyone, every time, without a human repeating it.
- **Small, legible changes.** A 200-line change can be reviewed asynchronously; a 2,000-line change requires a meeting.

> **Every recurring question is a documentation or design defect.** If three people ask how to do the same thing, the answer belongs somewhere durable—a README, a type, a script, or a test.

## 23.2 Code review

Code review is the highest-leverage quality practice available to most teams, and one of the most frequently degraded into ritual.

**What review is good at:**

- catching design problems while they are still cheap to fix;
- spreading knowledge of the codebase and its conventions;
- catching defects that tests miss: edge cases, error paths, security issues;
- enforcing consistency and shared standards;
- mentoring, in both directions.

**What review is bad at:**

- catching subtle logic errors in large diffs (reviewers skim);
- verifying behavior (that is what tests are for);
- style enforcement (that is what formatters are for);
- replacing design discussion (a review comment is a poor medium for a debate).

### Making review effective

**Keep changes small.** Review quality collapses as diff size grows. A change of 200–400 lines gets a careful read; a change of 1,500 lines gets a stamp. If a change must be large, split it into a sequence of reviewable commits.

**State the intent.** The author's description should say what problem the change solves, what approach was chosen, and what the reviewer should focus on. "Refactor user service, no behavior change, please check the error paths" is a useful review request.

**Review for the right things, in order:**

1. **Correctness:** does it do what it claims, including edge cases?
2. **Design:** is this the right place for the logic? Does the interface make sense?
3. **Tests:** do they cover the behavior and the failure modes?
4. **Security and data handling:** validation, authorization, secrets, logging of sensitive data.
5. **Readability:** names, structure, comments where needed.
6. **Style:** usually delegated to tooling.

**Distinguish blocking from non-blocking.** Mark comments as "must fix" or "consider." A review that blocks on a preference wastes everyone's time; a review that never blocks on a real problem fails at its job.

**Respond to the code, not the person.** "This function returns null on failure but the caller expects a throw" is a technical statement. "You always forget error handling" is not.

**Close the loop.** The author responds to every comment: fixed, discussed, or declined with a reason. An unresolved comment is an unresolved risk.

```typescript
// A review comment model that distinguishes severity and ownership.
type Severity = "blocking" | "suggestion" | "question" | "nit";

interface ReviewComment {
  readonly file: string;
  readonly line: number;
  readonly severity: Severity;
  readonly body: string;
}

function mustAddress(comments: readonly ReviewComment[]): readonly ReviewComment[] {
  return comments.filter((comment) => comment.severity === "blocking");
}
```

The severity field is not bureaucracy; it tells the author what actually prevents merge, so a discussion about a variable name does not hold up a release.

### Inspections

A formal **inspection** is a structured review with defined roles (author, moderator, reviewers), a checklist, and a recorded outcome. It is more expensive than a pull-request review and catches more defects per hour in high-risk code: safety-critical systems, security boundaries, cryptographic code, financial calculations.

Use inspections for the code where a defect is unacceptable, and lightweight review for everything else. The mistake is applying the ceremony everywhere (it collapses under its own weight) or nowhere (the highest-risk code gets the same skim as a typo fix).

## 23.3 Pair programming

**Pair programming** puts two developers at one workstation: a driver who types and a navigator who reviews, anticipates, and thinks ahead.

Benefits:

- Continuous review, so defects are caught within seconds.
- Knowledge transfer, in both directions, without a separate session.
- Better design decisions, because two people challenge assumptions in real time.
- Fewer context switches: the pair stays on one problem.

Costs:

- Two people on one task: roughly 15–40% more person-hours for the same output, though often with fewer defects and less rework.
- Fatigue: sustained pairing is tiring; most pairs need breaks and solo time.
- Mismatched pairs: a dominant driver or a passive navigator produces neither review nor learning.

Pairing is most valuable when:

- the work is complex or unfamiliar;
- the risk is high;
- a new team member is onboarding;
- a design decision needs two perspectives;
- a defect has resisted solo debugging.

It is least valuable for mechanical work, for work that needs long uninterrupted focus, and for teams where the pairing is forced rather than chosen.

**Remote pairing** works with screen sharing, a shared editor, and explicit turn-taking. The failure mode is the same: one person types while the other disengages. A useful norm is to switch driver every 20–30 minutes and to verbalize intent continuously.

## 23.4 Team size and structure

**Team size** affects communication and architecture. Small teams (three to seven) can coordinate informally; larger groups need explicit interfaces, written decisions, and more structure. Beyond a certain size, the communication overhead exceeds the marginal output, and the organization splits into teams.

**Conway's law** observes that systems tend to mirror the communication structure of the organizations that build them. Four teams building a compiler produce a four-stage compiler; a team split by frontend and backend produces a system split along that boundary.

The law is descriptive, not a command. Two responses:

- **Design the organization to match the architecture you want.** If you want a modular system with clear ownership, organize teams around those modules (the "inverse Conway maneuver").
- **Accept that the architecture will reflect the organization** and make the boundaries explicit, so that the resulting seams are deliberate rather than accidental.

**Ownership** matters more than org charts. A module with a named owner has someone who reviews changes, answers questions, and notices decay. A module owned by "everyone" is owned by no one.

**Autonomy with alignment.** Teams work best with clear boundaries and clear goals: enough autonomy to make local decisions, enough alignment that the decisions compose. The alternative—central approval for every decision—makes the organization the bottleneck; the opposite—no shared standards—produces a system of incompatible parts.

![Communication paths grow with the square of the number of people.](assets/communication-paths.png)

![As projects grow, more errors originate in requirements and design.](assets/defects-by-project-size.png)

![Construction dominates small projects; larger projects need more architecture and integration.](assets/construction-effort-by-size.png)

![Construction work grows nearly linearly with project size; other work grows faster.](assets/construction-work-scaling.png)

## 23.5 Documentation for teams

Documentation is communication that persists. The most valuable kinds:

- **README:** what the project is, how to run it, how to test it, where to get help. The first document a new team member reads.
- **Architecture record:** the structure and the significant decisions, with alternatives and consequences (Chapter 21).
- **Runbooks:** how to operate, monitor, and recover the system. Written for the person on call at 3 a.m.
- **Onboarding guide:** the path from a fresh machine to a first merged change.
- **Glossary:** the domain vocabulary and its code equivalents.
- **Decision log:** why the system is the way it is.

Principles:

- **Write for the reader who arrives later**, without your context.
- **Keep it close to the code.** Documentation in the repository is more likely to be updated than documentation in a separate tool.
- **Prefer examples.** A worked example is worth a page of description.
- **Date and own it.** A document with no owner and no date is a rumor.
- **Delete what is stale.** Wrong documentation is worse than none, because it is trusted.

## 23.6 Security practice

Security is a design property, not a feature to be added at the end. Most breaches exploit ordinary mistakes: unvalidated input, missing authorization checks, secrets in repositories, and dependencies that were never updated.

Design-level practices:

- **Validate at every trust boundary.** Treat all external input as hostile: HTTP, files, messages, environment, third-party APIs (Chapter 8).
- **Check authorization at the point of action.** Authentication says who you are; authorization says what you may do. A check in the UI is not a check.
- **Apply least privilege.** Services, users, and tokens get the minimum access they need. A read-only job should not have write credentials.
- **Keep secrets out of code and logs.** Use a secret manager; redact at the logging boundary; rotate on suspicion.
- **Parameterize queries and escape output.** String concatenation into SQL, HTML, or shell is the root of injection.
- **Pin and audit dependencies.** A lockfile is a security control; so is a scanner that reports known vulnerabilities.
- **Design for failure.** Assume a component will be compromised: segment networks, limit blast radius, log access.
- **Encrypt in transit and at rest** where the data warrants it, and manage keys deliberately.

```typescript
// Authorization at the point of action, not in the caller's UI.
interface Principal {
  readonly userId: string;
  readonly roles: readonly string[];
}

interface Document {
  readonly id: string;
  readonly ownerId: string;
  readonly tenantId: string;
}

function canRead(principal: Principal, document: Document): boolean {
  if (principal.roles.includes("admin")) return true;
  return document.ownerId === principal.userId;
}

function readDocument(principal: Principal, document: Document): string {
  if (!canRead(principal, document)) {
    // Same error for "not found" and "not allowed": do not leak existence.
    throw new Error("Document not found");
  }
  return `contents of ${document.id}`;
}
```

Two details matter more than the code: the check happens in the function that performs the action (not only in the caller), and the error does not reveal whether the document exists. Both are design decisions about information flow.

Security also has a **human** dimension: phishing, social engineering, and insider risk. No amount of type safety prevents a developer from pasting a production key into a chat. Practices that help: short-lived credentials, audit logs, and a culture where reporting a mistake is safe.

## 23.7 Ethics and responsibility

Software mediates decisions about people: who gets a loan, who is seen by a doctor, who is offered a job, who is surveilled. The engineer who builds the system is not absolved of its effects by a ticket that said "implement the model."

Questions worth asking:

- **Who benefits, and who bears the risk?** A feature that improves conversion by dark patterns transfers value from the user to the business.
- **What happens when it is wrong?** A misclassified fraud alert is an inconvenience; a misclassified medical image is not. The tolerance for error must match the consequence.
- **Is the data collected necessary and consented?** Data collected "just in case" becomes a liability and a privacy risk.
- **Who can appeal or correct?** Automated decisions need a path for the people affected to contest them.
- **Would I be comfortable explaining this decision publicly?** A useful test for designs that are legal but questionable.

Professional responsibility also includes honesty about uncertainty, refusal to ship known-harmful behavior, and reporting defects that put users at risk. These are not abstract virtues; they are part of the job, and organizations that punish them get the systems they deserve.

## Summary

- Communication costs grow faster than team size; reduce the need for it with written decisions, explicit interfaces, and automated checks.
- Code review is the highest-leverage quality practice when changes are small, intent is stated, and comments are prioritized; it is ritual when diffs are huge and every comment blocks.
- Pair programming provides continuous review and knowledge transfer at a real cost; use it for complex, risky, or unfamiliar work.
- Team size and structure shape architecture; make the seams deliberate with ownership and clear boundaries.
- Documentation should be persistent, close to the code, example-driven, owned, and deleted when stale.
- Security is a design property: validate at boundaries, authorize at the point of action, apply least privilege, keep secrets out of code and logs.
- Ethics is part of engineering: consider who benefits, who bears the risk, and whether the decision could be defended publicly.

## Exercises

1. **Review audit.** Look at the last five reviews you gave or received. What fraction of comments were blocking? How many caught a design issue versus a style issue? What would you change?
2. **Small-change experiment.** Take a large change and split it into a sequence of small, reviewable commits. What did the split reveal about the design?
3. **Review checklist.** Write a six-item checklist for reviews in your codebase, ordered by risk. Test it on the next three reviews.
4. **Pairing decision.** For five upcoming tasks, decide whether to pair, review, or work solo. Justify each with risk, novelty, and learning goals.
5. **Conway check.** Draw your team structure and your system's module structure. Where do they match? Is any boundary an accident of the org chart?
6. **Documentation gap.** Find a recurring question in your team's chat. Write the document that would answer it permanently, and place it where people will look.
7. **Security pass.** List the trust boundaries in a system you know. For each, name the validation and authorization that happens there. Which boundary is weakest?
8. **Ethics review.** Take a feature that makes an automated decision about people. Write down who benefits, who bears the risk, what happens when it errs, and how someone can appeal. Would you ship it?
