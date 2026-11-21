# Issue tracker: local markdown in `.tracker/`, GitHub on request

Specs and tickets live as markdown files in `.tracker/`, committed to git. Use GitHub Issues on `wislertt/bakefile` only when the user explicitly asks for a GitHub issue.

`.tracker/` replaces the `.scratch/` path that the skills name: wherever a skill says `.scratch/`, use `.tracker/`. `.scratch/` is gitignored throwaway space, never the tracker.

## Local conventions (default)

- One feature per directory: `.tracker/<feature-slug>/`, slug matching the branch name where there is one
- The spec is `.tracker/<feature-slug>/spec.md`
- Tickets are one file per ticket at `.tracker/<feature-slug>/issues/<NN>-<slug>.md`, numbered from `01`, never a single combined file
- State is a `Status:` line near the top of each ticket: a triage role (see `triage-labels.md`) while open, `resolved` when done
- Comments and history append under a `## Comments` heading
- Commit spec and ticket files to `main` on their own (`docs:` commit) before any implementation worktree starts, so workers see them. Status changes ride along with each implementation PR.
- When every ticket of a feature is `resolved`, delete `.tracker/<feature-slug>/`. Git history is the archive.

### When a skill says "publish to the issue tracker"

Create a file under `.tracker/<feature-slug>/`, creating the directory if needed.

### When a skill says "fetch the relevant ticket"

Read the file at the referenced path. The user normally passes the path or the number.

### Wayfinding operations

Used by `/wayfinder`. The **map** is a file with one **child** file per ticket.

- **Map**: `.tracker/<effort>/map.md` (the Notes / Decisions-so-far / Fog body).
- **Child ticket**: `.tracker/<effort>/issues/NN-<slug>.md`, numbered from `01`, with the question in the body. A `Type:` line records the ticket type (`research`/`prototype`/`grilling`/`task`); a `Status:` line records `claimed`/`resolved`.
- **Blocking**: a `Blocked by: NN, NN` line near the top. A ticket is unblocked when every file it lists is `resolved`.
- **Frontier**: scan `.tracker/<effort>/issues/` for files that are open, unblocked, and unclaimed; first by number wins.
- **Claim**: set `Status: claimed` and save before any work.
- **Resolve**: append the answer under an `## Answer` heading, set `Status: resolved`, then append a context pointer (gist + link) to the map's Decisions-so-far in `map.md`.

## GitHub (only when the user asks)

Use the `gh` CLI. Before the first `gh issue create` of a session, check the target with `gh repo view --json nameWithOwner` and confirm it is `wislertt/bakefile`. Before applying a triage or `wayfinder:` label, create it with `gh label create` if it is missing, after asking the user.

### Conventions

- **Create an issue**: `gh issue create --title "..." --body "..."`. Use a heredoc for multi-line bodies.
- **Read an issue**: `gh issue view <number> --json number,title,body,labels,comments`.
- **List issues**: `gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'` with appropriate `--label` and `--state` filters.
- **Make an issue a sub-issue of a parent**: `gh issue create --parent <parent> ...`, or `gh issue edit <parent> --add-sub-issue <child>` afterwards (`gh` 2.94+). Older `gh`: `gh api --method POST repos/<owner>/<repo>/issues/<parent>/sub_issues -F sub_issue_id=<child-db-id>` (database id, as in **Blocking** below). Without sub-issues, put `Part of #<parent>` at the top of the child body.
- **Blocking**: GitHub's **native issue dependencies**, the canonical, UI-visible representation. Add an edge with `gh issue create --blocked-by <n>,<n> ...` or `gh issue edit <child> --add-blocked-by <blocker>` (`gh` 2.94+). Older `gh`: `gh api --method POST repos/<owner>/<repo>/issues/<child>/dependencies/blocked_by -F issue_id=<blocker-db-id>`, where `<blocker-db-id>` is the blocker's numeric **database id** (`gh api repos/<owner>/<repo>/issues/<n> --jq .id`, _not_ the `#number` or `node_id`). Where dependencies aren't available, fall back to a `Blocked by: #<n>, #<n>` line at the top of the child body. A ticket is unblocked when every blocker is closed.
- **Count open blockers**: `gh api repos/<owner>/<repo>/issues/<n> --jq .issue_dependencies_summary.blocked_by` (open blockers only; 0 means startable). `gh issue view <n> --json blockedBy` also lists closed blockers, so filter it: `--jq '[.blockedBy.nodes[] | select(.state == "OPEN")] | length'`.
- **Comment on an issue**: `gh issue comment <number> --body "..."`
- **Apply / remove labels**: `gh issue edit <number> --add-label "..."` / `--remove-label "..."`
- **Close**: post the explanation with `gh issue comment <number> --body "..."`, then `gh issue close <number>`. On an already-closed issue, `gh issue close --comment` drops the comment and still exits 0.

File issues only into the user's own repo. Never file into `mattpocock/skills` (the repo these skills come from).

### Pull requests as a triage surface

**PRs as a request surface: no.** _(Set to `yes` if this repo treats external PRs as feature requests; `/triage` reads this flag.)_

### When a skill says "publish" or "fetch" on GitHub

Create a GitHub issue; read it as in **Read an issue** above.

### Wayfinding operations on GitHub

- **Map**: a single issue labelled `wayfinder:map`, holding the Notes / Decisions-so-far / Fog body. `gh issue create --label wayfinder:map`.
- **Child ticket**: an issue linked to the map as a GitHub sub-issue (see **Make an issue a sub-issue of a parent**). Where sub-issues aren't enabled, add the child to a task list in the map body and put `Part of #<map>` at the top of the child body. Labels: `wayfinder:<type>` (`research`/`prototype`/`grilling`/`task`). Once claimed, the ticket is assigned to the driving dev.
- **Blocking**: see **Blocking** under Conventions.
- **Frontier query**: list the map's open children (`gh issue list --state open`, scoped to the map's sub-issues / task list), drop any with an open blocker (see **Count open blockers**, or an open issue in the `Blocked by` line) or an assignee; first in map order wins.
- **Claim**: `gh issue edit <n> --add-assignee @me`, the session's first write.
- **Resolve**: `gh issue comment <n> --body "<answer>"`, then `gh issue close <n>`, then append a context pointer (gist + link) to the map's Decisions-so-far.
