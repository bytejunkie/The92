# The 92 Design System

This document captures the visual direction from the Figma concept for The 92. Use it as the source of truth when styling Django templates, static CSS, Tailwind utilities, or future component libraries.

Figma concept: https://www.figma.com/design/3DQlzgAPKDTApmxODnI0Jt

## Product Feel

The 92 should feel like a social product for football supporters, not a generic football news site. The UI should be practical, dense enough for repeated use, and still carry matchday atmosphere.

Core traits:

- Social first: avatars, friend activity, check-ins, lists, progress, and recent visits are primary UI material.
- Football texture: pitch stripes, ground markers, league tags, and matchday states should appear throughout.
- Utility over marketing: first screens should show the product experience, not a decorative landing page.
- Mobile parity: every desktop workflow must have an equally strong mobile version.

## Colour Tokens

Use semantic tokens rather than hardcoded colours in templates.

### Light Theme

| Token | Hex | Use |
| --- | --- | --- |
| `--color-bg` | `#F6F8F5` | Page background |
| `--color-surface` | `#FFFFFF` | Cards, panels, nav |
| `--color-surface-muted` | `#ECF1EC` | Map surfaces, quiet UI areas |
| `--color-text` | `#101820` | Primary text |
| `--color-text-muted` | `#5D6975` | Supporting text |
| `--color-border` | `#DEE4DE` | Card borders, dividers |
| `--color-pitch` | `#19704B` | Primary football green |
| `--color-grass` | `#4DA368` | Pitch stripe green |
| `--color-lime` | `#BDEB80` | Positive highlight, active state |
| `--color-red` | `#D6363E` | Claim/check-in action |
| `--color-navy` | `#182740` | Secondary badges, deep contrast |
| `--color-blue` | `#427BD3` | Social accents |
| `--color-gold` | `#EEB34C` | Avatar/accent states |

### Dark Theme

| Token | Hex | Use |
| --- | --- | --- |
| `--color-bg` | `#080D12` | Page background |
| `--color-surface` | `#12191F` | Cards, panels, nav |
| `--color-surface-muted` | `#19222A` | Nested surfaces |
| `--color-text` | `#F4F8F4` | Primary text |
| `--color-text-muted` | `#9AA8AE` | Supporting text |
| `--color-border` | `#334049` | Card borders, dividers |
| `--color-pitch` | `#116240` | Primary football green |
| `--color-grass` | `#268957` | Pitch stripe green |
| `--color-lime` | `#BEF475` | Positive highlight, active state |
| `--color-red` | `#E83E4B` | Claim/check-in action |
| `--color-navy` | `#172438` | Secondary badges |
| `--color-blue` | `#5390EA` | Social accents |
| `--color-gold` | `#F7B849` | Avatar/accent states |

## Typography

Preferred font: Inter.

Use these roles:

| Role | Size | Weight | Line height |
| --- | --- | --- | --- |
| Hero | `clamp(3rem, 6vw, 4.875rem)` | 800 | 0.98-1.05 |
| Page title | `2.5rem-4.5rem` | 800 | 1.05 |
| Section title | `1.75rem-2rem` | 800 | 1.2 |
| Card title | `1.125rem-1.5rem` | 700 | 1.25 |
| Body | `1rem-1.125rem` | 500 | 1.5 |
| Small/meta | `0.75rem-0.875rem` | 500-700 | 1.3 |

Rules:

- Do not scale font size directly with viewport width except for hero/page titles using `clamp`.
- Keep letter spacing at `0`.
- Keep compact labels legible; avoid making stat labels too small to scan on mobile.

## Components

### Cards

Cards are used for individual product modules: ground cards, profile summaries, check-in panels, maps, feeds, and practical info blocks.

Rules:

- Radius: `8px`.
- Border: `1px solid var(--color-border)`.
- Use restrained shadows. Avoid nested cards unless the child is a real embedded module.
- Cards should work as standalone components inside any grid column.

### Buttons

Button hierarchy:

- Primary claim/check-in: red background, white text.
- Primary onboarding/action: lime background, dark text.
- Secondary: surface or muted surface with border.
- Compact actions: pill-shaped, 34-42px tall.

Button text should be direct: `Claim ground`, `Check in`, `Add historic visit`, `Explore grounds`.

### Tags and States

Common states:

- `Visited`: pitch or lime.
- `Want to go`: navy.
- `Historic`: red or navy depending on context.
- `Matchday open`: lime.
- `Live`: red.

### Football Visual Texture

Use pitch texture sparingly but consistently:

- Green rectangle with alternating translucent stripes.
- Optional halfway line and centre circle.
- Use for hero panels, ground cards, and check-in panels.
- Do not use decorative gradient blobs or abstract football illustrations.

## Content Patterns

### Home Page

The home page should show the product immediately:

- Navigation.
- Hero with clear product promise.
- Profile/progress preview.
- Matchday check-in.
- Friend activity.
- Ground cards.
- Map/list exploration.

### Ground Detail Page

A ground page should include:

- Ground name, club, location, opened date.
- Claim and historic visit actions.
- Capacity, away allocation, social stats, visit status.
- Address and transport.
- Away fan guidance: parking, pubs/drinking, away entrance, ticket/bag notes.
- Community confidence/freshness.
- Recent friend activity.

## Accessibility

- Keep primary text contrast high in both themes.
- Never rely on colour alone for state; pair it with text.
- Touch targets should be at least 44px where possible.
- On mobile, sticky claim actions are acceptable for matchday workflows.
