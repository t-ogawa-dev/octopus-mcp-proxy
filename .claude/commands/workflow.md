# Octopus MCP Proxy 開発ワークフロー

Process the request in `$ARGUMENTS` through design, implementation, review, and testing in that order.

Read `CLAUDE.md` and `docs/DEVELOPMENT.md` as shared rules, and preserve existing uncommitted changes.

## Workflow

### 1. Design

Pass the request to the `designer` agent. Do not start implementation until the design includes:

- requirements and acceptance criteria
- the current implementation path
- files to change and explicit non-goals
- authentication, authorization, database, and compatibility risks
- the test and validation plan

Ask the user when an unknown could change the acceptance criteria.

### 2. Development

Pass the design to the `developer` agent. Implement the smallest change that satisfies it and run focused validation immediately after editing. Keep models, migrations, and tests consistent for database changes.

### 3. Review

Pass the diff to the `reviewer` agent. Check requirements, regressions, MCP compatibility, authentication, authorization, validation, logging, security, and missing tests. If a critical or high-priority finding is reported, return to `developer`, fix it, and rerun the review.

### 4. Testing

Ask the `tester` agent to run focused tests, add missing tests when needed, and run quality checks. Return implementation failures to `developer`, fix them, and rerun the same validation. For environment failures, report the cause and unvalidated scope.

## Final Report

Briefly report the request, design decisions, changed files, review results, executed validation, and unresolved risks or skipped checks.

For small changes, stages may be skipped when justified; state the reason in the final report. Summarize each stage before passing its result to the next stage, and avoid repeating the same investigation.
