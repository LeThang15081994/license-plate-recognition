# [AGENT.md](http://AGENT.md)

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

**ASD-STE100:** Follow it when writing in English. Apply its clarity principles in other languages.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:

- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:

- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:

- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:

```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

## Development rules

### Repository layout

- `ui/` is the standalone Vite + React + TypeScript application. Its `package.json`, `package-lock.json`, `README.md`, lint, formatting, TypeScript, and test configurations live there.
- `ui/src/App.tsx` owns the single upload screen. Image validation lives in `ui/src/validateImage.ts`; UI tests live in `ui/src/App.test.tsx`.
- `backend/` is empty. Do not assume an API, database, OCR endpoint, backend language, or backend test command exists. Establish those contracts from actual code when the backend is added.
- `models/yolov8n.pt` is a model artifact, not a runnable backend.
- The repository root has no `package.json`. Run npm commands from `ui/`, not the root.

### Repository rules

`AGENTS.md` is the entry point for project instructions. Read the applicable Markdown rules in `.agents/rules/common/` at the start of work. Before editing TypeScript or JavaScript, also read the applicable rules in `.agents/rules/typescript/`; honor any `paths` conditions. Use the tools available in the current runtime rather than assuming an ECC agent, plugin, or hook is installed. Apply generic rules to the parts of this repository that actually exist; this file owns the repository-specific layout and commands.

### UI development and verification

- Keep the UI in `ui/`. Follow the existing React, TypeScript, CSS, ESLint, Prettier, and Vitest setup instead of adding another application scaffold.
- Use `cd ui` then `npm ci` for a clean install, `npm run dev` for local development, and `npm run build` for TypeScript checking and a production bundle.
- After UI changes, run the relevant focused test and `npm run check` from `ui/`. The check script runs TypeScript, ESLint, Prettier, Vitest, and the production build.
- Exercise visible UI changes in a browser. Validate upload behavior against the accepted image types and 10 MB size limit.
- The text area is a result display, not an OCR implementation. Until a real service contract exists, do not fabricate recognized text or add a mock backend as production behavior.
- For documentation-only changes, verify referenced paths and commands without running unrelated builds.

### Dependencies and source control

- Review changes to `ui/package.json` and `ui/package-lock.json` together. Install dependencies from `ui/`; do not create a root npm workspace.
- Preserve unrelated staged, unstaged, and untracked changes. Commit and push only when requested; stage only files changed for the task.
- Follow `.agents/rules/common/git-workflow.md` for commit messages when committing. Do not force-push or use destructive repository-wide cleanup commands.

### Documentation

- Keep UI setup and usage instructions in `ui/README.md`. Document backend setup only after a backend implementation and its commands exist.
- Update documentation when user-visible behavior or the required commands change.

## Agent skills

### Issue tracker

Issues and specs live in GitHub Issues. See `docs/agents/issue-tracker.md`.

### Triage labels

Use the five default triage labels. See `docs/agents/triage-labels.md`.

### Domain docs

Use the single-context layout. See `docs/agents/domain.md`.