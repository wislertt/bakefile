# Setup Claude Code Infrastructure - Task Checklist

## Phase 1: Essential Hooks ✅ COMPLETE

- [x] Create `.claude/hooks/` directory
- [x] Copy `skill-activation-prompt.sh` from showcase
- [x] Copy `skill-activation-prompt.ts` from showcase
- [x] Copy `post-tool-use-tracker.sh` from showcase
- [x] Copy `package.json` from showcase
- [x] Make shell scripts executable (`chmod +x`)
- [x] Install npm dependencies (`cd .claude/hooks && npm install`)
- [x] Verify `node_modules/` exists

---

## Phase 2: Skills ⏳ NOT STARTED

### 2.1 skill-developer

- [ ] Copy `skill-developer/` directory from showcase
- [ ] Verify all resource files copied

### 2.2 python-cli-guidelines (NEW)

- [ ] Create `python-cli-guidelines/` directory
- [ ] Create `SKILL.md` with Python CLI patterns
- [ ] Create `resources/typer-patterns.md`
- [ ] Create `resources/pydantic-patterns.md`
- [ ] Create `resources/oop-design.md`
- [ ] Create `resources/testing.md`
- [ ] Create `resources/packaging.md`
- [ ] Create `resources/uv-integration.md`

### 2.3 skill-rules.json

- [ ] Copy `skill-rules.json` from showcase
- [ ] Customize path patterns for Python (`src/**/*.py`)
- [ ] Remove irrelevant skills
- [ ] Add python-cli-guidelines triggers
- [ ] Validate JSON (`cat skill-rules.json | jq .`)

---

## Phase 3: Agents ⏳ NOT STARTED

- [ ] Create `.claude/agents/` directory
- [ ] Copy `code-architecture-reviewer.md`
- [ ] Copy `code-refactor-master.md`
- [ ] Copy `documentation-architect.md`
- [ ] Copy `plan-reviewer.md`
- [ ] Copy `refactor-planner.md`
- [ ] Copy `web-research-specialist.md`

---

## Phase 4: Slash Commands ⏳ NOT STARTED

- [ ] Create `.claude/commands/` directory
- [ ] Copy `dev-docs.md` from showcase
- [ ] Copy `dev-docs-update.md` from showcase
- [ ] Verify no hardcoded paths need updating

---

## Phase 5: Settings and Verification ⏳ NOT STARTED

- [ ] Copy `settings.json` from showcase
- [ ] Extract UserPromptSubmit hook only
- [ ] Extract PostToolUse hook only
- [ ] Remove Stop hooks (too complex)
- [ ] Create `settings.local.json` if needed
- [ ] Validate settings.json (`cat settings.json | jq .`)
- [ ] Verify hooks executable (`ls -la .claude/hooks/*.sh`)
- [ ] Test skill activation (edit Python file)

---

## Cleanup ⏳ NOT STARTED

- [ ] Remove `.claude/plan/` (non-standard)
- [ ] Remove `.claude/ref/` (non-standard)
- [ ] Update CLAUDE.md to reference dev/active/ for plans

---

## Quick Resume

**Current Phase:** Phase 2 - Skills

**Next Action:** Copy `skill-developer/` and create `python-cli-guidelines/` skill
