Create a new commit for all of our uncommitted changes.

Run `git status && git diff HEAD && git status --porcelain` to see what files are uncommitted.

Add the untracked and changed files that are relevant to the work completed.

Create an atomic commit message with an appropriate, descriptive message that explains the "why" not just the "what".

Add a semantic tag prefix that reflects the work:
- `feat:` — new feature or capability
- `fix:` — bug fix
- `docs:` — documentation changes
- `refactor:` — code restructuring without behavior change
- `test:` — adding or updating tests
- `chore:` — tooling, config, dependencies
- `style:` — formatting, linting
- `perf:` — performance improvement

Example: `feat: add user authentication with JWT tokens`

Do not commit files that are irrelevant to the current task (e.g., unrelated config changes, temp files, .env files).
