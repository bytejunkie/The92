# The 92 Agent Guide

Use this file for future Codex sessions working in this repo.

## Project Shape

The 92 is a Django site for tracking football grounds a user has visited, wants to visit, or claims on matchday. The first MVP focuses on:

- A custom user model with username, email, birthday, and favourite team.
- Username validation that permits comedy but blocks profanity.
- Clubs/teams, including the 92 and future non-92 teams.
- Grounds with image/logo fields and practical stats such as capacity and opened date.
- Styled Django pages using the The 92 visual system.

## Tooling

- Use `uv` for dependency management and commands.
- Target the newest local Python available; this repo currently requires Python `>=3.14`.
- Prefer these commands:
  - `uv sync`
  - `uv run python manage.py check`
  - `uv run python manage.py makemigrations`
  - `uv run python manage.py migrate`
  - `uv run python manage.py runserver`
  - `uv run ruff check .`

Do not add `pip` or `virtualenv` instructions unless there is a concrete reason.

## Django Rules

- Keep the custom user model from the start. Do not switch back to Django's default `User`.
- Put user/profile concerns in `accounts`.
- Put clubs, grounds, and ground data in `grounds`.
- Use semantic Django templates and reusable partials as the project grows.
- Use server-rendered flows first. HTMX can be added later for check-ins, filtering, and inline updates.

## Styling Rules

Use the `$the92-style` skill for frontend work.

Source-of-truth files:

- `docs/design-system.md`
- `docs/layout-grid.md`
- `theme/static/theme/css/tokens.css`
- `theme/static/theme/css/layout.css`

Frontend expectations:

- Mobile-first layout.
- Switch to a 12-column grid at `900px`.
- Use `.page-shell`, `.app-grid`, `.component-grid`, `.stats-grid`, `.site-card`, `.pill`, `.button`, and `.pitch-surface` before inventing new layout CSS.
- Keep cards at `8px` radius.
- Support dark mode with `[data-theme="dark"]` or `.theme-dark`.
- Avoid generic Bootstrap-looking UI.

## Design Context

Figma concept:

https://www.figma.com/design/3DQlzgAPKDTApmxODnI0Jt

Key screens already explored:

- Desktop social home.
- Mobile matchday check-in.
- Ground information page.
- Dark-mode desktop home.

## Implementation Style

- Keep changes scoped and incremental.
- Add migrations when models change.
- Run Django checks after model/template changes.
- If adding fixtures or seed data, keep it small and realistic enough for local design validation.
