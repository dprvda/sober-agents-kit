# REASON: Generalized TDD skill because the red-green-refactor loop applies to any language or project.

---
name: tdd
description: Test-driven development with red-green-refactor loop. Use when user wants to build features or fix bugs using TDD, mentions "red-green-refactor", wants integration tests, or asks for test-first development.
---

# Test-Driven Development

## Philosophy

**Core principle**: Tests should verify behavior through public interfaces, not implementation details. Code can change entirely; tests shouldn't.

**Good tests** are integration-style: they exercise real code paths through public APIs. They describe _what_ the system does, not _how_ it does it. A good test reads like a specification - "user can checkout with valid cart" tells you exactly what capability exists. These tests survive refactors because they don't care about internal structure.

**Bad tests** are coupled to implementation. They mock internal collaborators, test private methods, or verify through external means (like querying a database directly instead of using the interface). The warning sign: your test breaks when you refactor, but behavior hasn't changed. If you rename an internal function and tests fail, those tests were testing implementation, not behavior.

See [tests.md](tests.md) for examples and [mocking.md](mocking.md) for mocking guidelines.

## Anti-Pattern: Horizontal Slices

**DO NOT write all tests first, then all implementation.** This is "horizontal slicing" - treating RED as "write all tests" and GREEN as "write all code."

This produces **crap tests**:

- Tests written in bulk test _imagined_ behavior, not _actual_ behavior
- You end up testing the _shape_ of things (data structures, function signatures) rather than user-facing behavior
- Tests become insensitive to real changes - they pass when behavior breaks, fail when behavior is fine
- You outrun your headlights, committing to test structure before understanding the implementation

**Correct approach**: Vertical slices via tracer bullets. One test → one implementation → repeat. Each test responds to what you learned from the previous cycle. Because you just wrote the code, you know exactly what behavior matters and how to verify it.

```
WRONG (horizontal):
  RED:   test1, test2, test3, test4, test5
  GREEN: impl1, impl2, impl3, impl4, impl5

RIGHT (vertical):
  STUB → RED → GREEN: stub1 → test1 → impl1
  STUB → RED → GREEN: stub2 → test2 → impl2
  (skip STUB if the code already exists from prior cycle)
  RED → GREEN: test3 → impl3
  ...
```

## STUB before RED — when adding new modules/functions

If the test would import a module/function that **does not exist yet**, write a minimal STUB *before* the test. The stub satisfies the import/call system but returns a placeholder value (`0`, `null`, `None`, a zero value, or `unimplemented` depending on language).

```
STUB:  Create minimal skeleton so imports/calls resolve
       → test runs but FAILS on the assertion (wrong behavior)
RED:   Confirm test fails for the RIGHT reason (wrong output, not missing import)
GREEN: Replace stub with real impl → test passes
```

**Why this matters**: a test that fails with "module not found" or "function not defined" is a meaningless RED. The test isn't testing behavior — it's testing the module system. The first true RED must fail on **wrong behavior**, otherwise you don't know your test would catch a regression.

**Skip STUB when:** the function/module already exists from a previous cycle and you're just adding a new behavior to it.

## Workflow

### 1. Planning

Before writing any code, check whether the issue body already has a `## TDD contract` YAML block (produced by `/to-issues`):

```yaml
goal: "..."
acceptance:
  - given: "..."
    when: "..."
    then: "..."
edge-cases: ["..."]
non-goals: ["..."]
```

**If the YAML contract is present:**

- Each `acceptance` row → one tracer-bullet test (in order).
- Each `edge-cases` row → an additional test after the happy path works.
- `non-goals` are scope guards — refuse to test them, refuse to implement them.
- If during implementation you discover a behavior the contract missed,
  **update the YAML in the issue body** before adding the test, then
  continue. This preserves TDD's learning-through-implementation advantage
  while keeping the contract honest.

**If no YAML contract is present** (free-form issue or direct user ask), draft one with the user before writing any test:

- [ ] Confirm with user what interface changes are needed
- [ ] Confirm with user which behaviors to test (prioritize)
- [ ] Identify opportunities for [deep modules](deep-modules.md) (small interface, deep implementation)
- [ ] Design interfaces for [testability](interface-design.md)
- [ ] List the behaviors to test (not implementation steps)
- [ ] Get user approval on the plan

Ask: "What should the public interface look like? Which behaviors are most important to test?"

**You can't test everything.** Confirm with the user exactly which behaviors matter most. Focus testing effort on critical paths and complex logic, not every possible edge case.

### 2. Tracer Bullet

Write ONE test that confirms ONE thing about the system:

```
STUB:  (only if module/fn doesn't exist) minimal skeleton resolves imports
RED:   Write test for first behavior → fails on wrong behavior
GREEN: Write minimal real code to pass → test passes
```

This is your tracer bullet - proves the path works end-to-end. The STUB step ensures your first RED is a *real* RED (wrong behavior), not a fake RED (missing import).

### 3. Incremental Loop

For each remaining behavior:

```
STUB:  (only if introducing a new module/fn) minimal skeleton
RED:   Write next test → fails on wrong behavior
GREEN: Minimal real code to pass → passes
```

Rules:

- One test at a time
- Only enough code to pass current test
- Don't anticipate future tests
- Keep tests focused on observable behavior

### 4. Refactor

After all tests pass, look for [refactor candidates](refactoring.md):

- [ ] Extract duplication
- [ ] Deepen modules (move complexity behind simple interfaces)
- [ ] Apply SOLID principles where natural
- [ ] Consider what new code reveals about existing code
- [ ] Run tests after each refactor step

**Never refactor while RED.** Get to GREEN first.

## Checklist Per Cycle

```
[ ] Test describes behavior, not implementation
[ ] Test uses public interface only
[ ] Test would survive internal refactor
[ ] Code is minimal for this test
[ ] No speculative features added
```
