# Pods — Skills Summary

Skills are domain knowledge files loaded when working on specific tasks.

## How to Use

When you start a task, check the table below. If your task matches a skill's purpose, load it:
```
/skill <name>
```

## Skills

| Skill | When to Load | What It Does |
|-------|-------------|--------------|
| `agentic-engineering` | Planning complex multi-step work | Decompose work into agent-sized units, route by complexity, eval-first |
| `architecture-decision-records` | Making architectural decisions | Log decisions with context, options, rationale — keeps record of why |
| `codebase-onboarding` | First time opening this repo | Project structure overview, conventions, how to get started fast |
| `coding-standards` | Writing or reviewing any code | Naming, readability, immutability, cross-project conventions |
| `context-budget` | Long AI sessions running out of context | Strategies to manage context windows, summarize, prune |
| `database-migrations` | Changing DB schema | Safe migration patterns, rollback, forward-compat |
| `git-workflow` | Branching, PRs, reviewing | Branch naming, commit messages, PR workflow conventions |
| `mcp-server-patterns` | Building MCP server or tools | MCP SDK patterns: tools, resources, prompts, transports |
| `postgres-patterns` | Working with Postgres (future phase) | Query patterns, indexing, JSONB, pgvector |
| `python-patterns` | Writing Python code | Python idioms, project structure, module conventions |
| `python-testing` | Writing or running tests | pytest, fixtures, mocking, parametrization, coverage |
| `tdd-workflow` | Building features test-first | Red-green-refactor cycle, 80%+ coverage, test types |
| `verification-loop` | Verifying AI-generated output | Define verification criteria, run checks, iterate until passing |
