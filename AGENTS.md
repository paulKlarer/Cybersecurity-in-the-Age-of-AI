# Project Agent Instructions

## Graphify

- When the user types `/graphify`, invoke the `graphify` skill before doing anything else.

## Default Development Workflow

Use a multiagent development process for future work in this repository whenever multiagent tools are available.

1. Start each new development or repository-changing request with a critical review subagent.
   - Ask it to check the user's instructions for logic errors, hidden assumptions, ambiguity, conflicting requirements, and clearly better alternative approaches.
   - If it finds important ambiguity, contradictions, or a better path that would change the work, report that to the user and ask how to proceed before making changes.

2. If the critical review does not block the work, use a decomposition subagent.
   - Ask whether the request is one connected task or several independent subtopics.
   - If the request is one connected task, proceed with one implementation path.
   - If the request has independent subtopics, split the work by subtopic.

3. For independent subtopics, assign specialist implementation subagents where useful.
   - Give each subagent a clear, non-overlapping ownership area.
   - Tell subagents that other edits may exist and that they must not revert unrelated changes.
   - Allow subagents to launch further subagents only when the subtask genuinely benefits from deeper delegation.

4. Validate each subtopic proportionally.
   - Use at least one validation subagent per subtopic when the change is substantial.
   - For small changes, perform an explicit local validation pass.
   - The validator should critically inspect the implementation for requirement mismatches, regressions, unsafe assumptions, missing tests, and documentation drift.

5. Keep the process proportional.
   - For tiny documentation, explanation, or single-line changes, the main agent may perform the decomposition locally after the critical check.
   - If multiagent tools are unavailable, state that limitation and emulate the same review steps locally.

6. Preserve user intent.
   - Do not treat this as permission to expand scope.
   - Ask before changing the requested direction when the review finds a meaningful uncertainty or better alternative.
