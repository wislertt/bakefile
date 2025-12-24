# Setup Claude Code Infrastructure - Implementation Plan

## Executive Summary

Integrate production-tested Claude Code infrastructure from [claude-code-infrastructure-showcase](https://github.com/anthropics/courses) into the bakefile project. This will enable:

- Auto-activating skills based on context
- Specialized agents for complex tasks
- Structured dev docs for context persistence
- Progressive disclosure for large knowledge bases

## Current State

**bakefile** - Python-based build system (Make/Justfile alternative)

- Core: `bake` CLI - runs commands from `bakefile.py`
- Meta: `bakefile` CLI - manages bakefile itself (init, lint, docs)
- Key differentiator: OOP-based reusability
- Tech stack: Typer, Pydantic, UV, pytest, ty

**Existing Claude infrastructure:**

- `.claude/CLAUDE.md` - Basic guidance (commands + project info)
- `.claude/plan/` - Plan storage (non-standard pattern)
- `.claude/ref/` - Reference docs (non-standard pattern)

## Desired Future State

Complete Claude Code infrastructure with:

- Auto-suggesting skills via hooks
- Python CLI guidelines skill (typer/pydantic/uv)
- Specialized agents for architecture, refactoring, docs
- Slash commands for dev docs management
- Dev docs pattern in `dev/active/` for ongoing work

## Implementation Phases

### Phase 1: Essential Hooks (15 min)

Auto-activation system for skills.

| Component               | Source         | Purpose             | Customization      |
| ----------------------- | -------------- | ------------------- | ------------------ |
| skill-activation-prompt | showcase hooks | Auto-suggest skills | None (generic)     |
| post-tool-use-tracker   | showcase hooks | Track file changes  | None (auto-detect) |

**Files to copy:**

- `.claude/hooks/skill-activation-prompt.sh`
- `.claude/hooks/skill-activation-prompt.ts`
- `.claude/hooks/post-tool-use-tracker.sh`
- `.claude/hooks/package.json`

**Settings to add:** UserPromptSubmit, PostToolUse hooks

**Acceptance:**

- Hooks executable (`chmod +x`)
- npm packages installed
- settings.json has hook configurations
- Editing a Python file triggers skill suggestions

---

### Phase 2: Skills (30 min)

#### 2.1 skill-developer (Copy as-is)

- Meta-skill for creating skills
- Fully tech-agnostic
- Use to create bakefile-specific skills

#### 2.2 python-cli-guidelines (NEW)

Since showcase skills are Node/React-specific, create new skill:

**Structure:**

```
python-cli-guidelines/
├── SKILL.md
└── resources/
    ├── typer-patterns.md
    ├── pydantic-patterns.md
    ├── oop-design.md
    ├── testing.md
    ├── packaging.md
    └── uv-integration.md
```

**skill-rules.json triggers:**

- Path patterns: `src/**/*.py`
- Keywords: "cli", "command", "typer", "task", "recipe", "pydantic"

**Acceptance:**

- skill-developer copied
- python-cli-guidelines skill created with all resources
- skill-rules.json updated with Python patterns

---

### Phase 3: Agents (15 min)

Copy relevant agents (standalone, no config needed):

**Agents to copy:**

- code-architecture-reviewer.md
- code-refactor-master.md
- documentation-architect.md
- plan-reviewer.md
- refactor-planner.md
- web-research-specialist.md

**Agents to skip/adapt later:**

- frontend-error-fixer → adapt for CLI errors
- auth-route-tester, auth-route-debugger → no auth
- auto-error-resolver → adapt for Python/ty

**Acceptance:**

- 6 agent files copied
- No hardcoded paths requiring update

---

### Phase 4: Slash Commands (10 min)

Copy and customize dev docs commands:

**Commands to copy:**

- dev-docs.md
- dev-docs-update.md

**Customization needed:**

- Update dev/active/ paths

**Acceptance:**

- Commands copied
- Paths verified for this project

---

### Phase 5: Settings and Verification (10 min)

**Create settings.json:**

- Copy from showcase
- Extract only UserPromptSubmit + PostToolUse
- Skip Stop hooks (too complex for single-service)

**Verification:**

```bash
# Hooks executable
ls -la .claude/hooks/*.sh

# JSON valid
cat .claude/skills/skill-rules.json | jq .
cat .claude/settings.json | jq .

# Test activation
# Edit Python file → skill should suggest
```

**Acceptance:**

- All JSON files parse correctly
- Hooks have execute permission
- Skill activation works

---

## Directory Structure After Setup

```
.claude/
├── CLAUDE.md                    # Existing - updated for dev docs pattern
├── settings.json                # NEW - hook configurations
├── settings.local.json          # NEW - local overrides
├── hooks/                       # NEW
│   ├── skill-activation-prompt.sh
│   ├── skill-activation-prompt.ts
│   ├── post-tool-use-tracker.sh
│   ├── package.json
│   └── node_modules/
├── skills/                      # NEW
│   ├── skill-rules.json
│   ├── skill-developer/
│   │   ├── SKILL.md
│   │   └── resources/
│   └── python-cli-guidelines/   # NEW - custom for this project
│       ├── SKILL.md
│       └── resources/
│           ├── typer-patterns.md
│           ├── pydantic-patterns.md
│           ├── oop-design.md
│           ├── testing.md
│           ├── packaging.md
│           └── uv-integration.md
├── agents/                      # NEW
│   ├── code-architecture-reviewer.md
│   ├── code-refactor-master.md
│   ├── documentation-architect.md
│   ├── plan-reviewer.md
│   ├── refactor-planner.md
│   └── web-research-specialist.md
└── commands/                    # NEW
    ├── dev-docs.md
    └── dev-docs-update.md

dev/                             # NEW - dev docs pattern
├── README.md                    # Copy from showcase
├── active/
│   └── setup-claude-infrastructure/
│       ├── setup-claude-infrastructure-plan.md
│       ├── setup-claude-infrastructure-context.md
│       └── setup-claude-infrastructure-tasks.md
└── archive/                     # For completed work
```

---

## Risk Assessment

| Risk                    | Impact | Mitigation                      |
| ----------------------- | ------ | ------------------------------- |
| Hook deps not installed | Medium | Verify npm install succeeds     |
| JSON syntax errors      | High   | Validate with jq after creation |
| Wrong path patterns     | Medium | Test skill activation           |
| Stop hooks too complex  | Low    | Skipping for single-service     |

---

## Success Metrics

- All phases completed
- Hooks fire correctly
- Skills auto-suggest on file edits
- Agents available via Task tool
- Dev docs commands work
- No JSON syntax errors
- All shell scripts executable

---

## Tech Stack Reference

- **CLI Framework**: Typer
- **Data Validation**: Pydantic
- **Package Manager**: UV (auto-resolve Python environments)
- **Testing**: pytest
- **Type Checking**: ty
