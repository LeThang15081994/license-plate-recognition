# Issue tracker: GitHub

Issues and specs live in GitHub Issues for this repository. Use `gh` from the repo checkout; it resolves the repository from `origin`.

## Operations

- Create: `gh issue create --title "..." --body "..."`
- Read: `gh issue view <number> --comments`
- List: `gh issue list --state open --json number,title,body,labels,comments`
- Comment: `gh issue comment <number> --body "..."`
- Add or remove a label: `gh issue edit <number> --add-label "..."` or `--remove-label "..."`
- Close: `gh issue close <number> --comment "..."`

"Publish to the issue tracker" means create a GitHub issue. "Fetch the relevant ticket" means read the referenced issue and comments.

## Pull requests as a triage surface

**PRs as a request surface: no.** Change this to `yes` only if external PRs should enter the triage queue.

## Wayfinding

- Map: one issue labelled `wayfinder:map` with Notes, Decisions-so-far, and Fog.
- Child tickets: sub-issues where available; otherwise list them in the map and put `Part of #<map>` in each child. Label each `wayfinder:<type>` (`research`, `prototype`, `grilling`, or `task`).
- Blocking: use GitHub issue dependencies where available; otherwise put `Blocked by: #<number>` in the child. An open blocker keeps the child out of the frontier.
- Claim an unassigned, unblocked child with `gh issue edit <number> --add-assignee @me` before working. To resolve, comment with the answer, close the issue, and add its gist and link to the map.
