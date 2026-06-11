---
name: the92-style
description: Use when styling or implementing The 92 Django site, Django templates, static CSS, Tailwind classes, responsive grids, dark mode, football-ground UI, social product screens, ground cards, check-in flows, profile/list pages, or away fan information pages.
---

# The 92 Style Skill

Use this skill when building or reviewing frontend work for The 92 Django site.

## Required References

Load these repo files before making styling decisions:

- `docs/design-system.md` for palette, typography, UI states, and product feel.
- `docs/layout-grid.md` for shell widths, breakpoints, and desktop/mobile layout rules.
- `theme/static/theme/css/tokens.css` for CSS variables.
- `theme/static/theme/css/layout.css` for reusable grid and component classes.

## Styling Workflow

1. Check whether the repo already has Django templates, static files, or Tailwind config.
2. Use the repo tokens before introducing new colours, spacing, shadows, or radii.
3. Build mobile-first, then add the 12-column layout from `900px` upward.
4. Prefer reusable Django partials for repeated UI: nav, ground card, stat card, activity row, progress dots, and pitch surface.
5. Use `.page-shell`, `.app-grid`, `.component-grid`, `.stats-grid`, `.site-card`, `.pill`, and `.button` classes before inventing page-specific layout CSS.
6. Keep dark mode token-driven with `[data-theme="dark"]` or `.theme-dark`.
7. Validate mobile and desktop views before marking work complete.

## Product Rules

- The first screen should feel like the working product, not a marketing landing page.
- Social signals are core: avatars, recent visits, friends, progress, check-ins, and confidence notes.
- Football cues should be useful and restrained: pitch textures, league tags, ground markers, and matchday states.
- Cards use `8px` radius. Avoid nested cards unless the child is a real embedded module.
- Avoid Bootstrap-looking generic UI. The design should feel custom to football ground collecting.
- Do not use decorative gradient blobs, abstract hero illustrations, or oversized empty sections.

## Django Guidance

- Reference static CSS with `{% load static %}` and `{% static 'theme/css/tokens.css' %}`.
- Keep templates semantic: `main`, `section`, `article`, `nav`, `ul`, and `li` where appropriate.
- Use server-rendered states for visited/want-to-go/historic/check-in-open first; add HTMX later for richer interactions.
- If Tailwind is added, map its theme to the CSS variables rather than duplicating the palette.
