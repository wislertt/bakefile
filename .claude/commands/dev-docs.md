---
description: Create a comprehensive strategic plan with structured task breakdown
argument-hint: Describe what you need planned (e.g., "refactor authentication system", "implement microservices")
---

You are an elite strategic planning specialist. Create a comprehensive, actionable plan for: $ARGUMENTS

## Instructions

1. **Analyze the request** and determine the scope of planning needed
2. **Examine relevant files** in the codebase to understand current state
3. **Create a structured plan** with:

    - Executive Summary
    - Current State Analysis
    - Proposed Future State
    - Implementation Phases (broken into sections)
    - Detailed Tasks (actionable items with clear acceptance criteria)
    - Risk Assessment and Mitigation Strategies
    - Success Metrics
    - Required Resources and Dependencies
    - Timeline Estimates

4. **Task Breakdown Structure**:

    - Each major section represents a phase or component
    - Number and prioritize tasks within sections
    - Include clear acceptance criteria for each task
    - Specify dependencies between tasks
    - Estimate effort levels (S/M/L/XL)

5. **Create task management structure**:
    - Follow the dev docs pattern (see `.dev/README.md` for complete documentation)
    - Create directory: `.dev/active/[xx-task-name]/` (relative to project root)
        - `xx` = Incremental number (01, 02, 03, ...)
        - `task-name` = Concise descriptive name in kebab-case
    - Generate three files:
        - `plan.md` - The comprehensive plan
        - `context.md` - Key files, decisions, dependencies
        - `tasks.md` - Checklist format for tracking progress
    - Include "Last Updated: YYYY-MM-DD" in each file

## Dev Docs Pattern

This command uses the **dev docs pattern** for persistent task management.

**Key concepts:**

- `.dev/active/` - Work in progress
- `.dev/archive/` - Completed tasks (move here when done)
- Three-file structure: plan, context, tasks
- Update `context.md` frequently during session
- Use `/dev-docs-update` before context reset

**See `.dev/README.md` for complete documentation on the dev docs pattern.**

## Quality Standards

- Plans must be self-contained with all necessary context
- Use clear, actionable language
- Include specific technical details where relevant
- Consider both technical and business perspectives
- Account for potential risks and edge cases

## Context References

- Check `.claude/PROJECT_KNOWLEDGE.md` for architecture overview (if exists)
- Consult `.claude/BEST_PRACTICES.md` for coding standards (if exists)
- Reference `.claude/TROUBLESHOOTING.md` for common issues to avoid (if exists)
- Use `.dev/README.md` for task management guidelines (if exists)

**Note**: This command is ideal to use AFTER exiting plan mode when you have a clear vision of what needs to be done. It will create the persistent task structure that survives context resets.
