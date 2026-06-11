# The 92

A Django MVP for a social football ground collecting site.

## Local Development

This project uses `uv`.

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py runserver
```

The design direction lives in:

- `docs/design-system.md`
- `docs/layout-grid.md`
- `theme/static/theme/css/tokens.css`
- `theme/static/theme/css/layout.css`

Use the local Codex skill `$the92-style` when adding or reviewing frontend work.
