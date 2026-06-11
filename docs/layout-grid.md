# The 92 Layout Grid

The site should be mobile-first, but desktop should feel intentional rather than stretched. Use a consistent shell and 12-column page grid for large screens, then collapse to one column on mobile.

## Page Shell

Use `.page-shell` for most pages.

```css
.page-shell {
  width: min(100% - 2rem, 82rem);
  margin-inline: auto;
}
```

This gives:

- `16px` side padding on narrow mobile.
- Maximum content width of `1312px`.
- A direct match to the Figma desktop content rhythm.

For very dense app pages, use `.page-shell-wide` with a `90rem` maximum only when the extra width genuinely improves scanning.

## Desktop Grid

Use a 12-column grid from `900px` upward.

```css
.app-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;
}

@media (min-width: 900px) {
  .app-grid {
    grid-template-columns: repeat(12, minmax(0, 1fr));
    gap: 1.5rem;
  }
}
```

## Breakpoints

Use these breakpoints consistently:

| Name | Width | Purpose |
| --- | --- | --- |
| `sm` | `640px` | Larger phones, small component shifts |
| `md` | `768px` | Tablet layouts |
| `lg` | `900px` | Switch to 12-column page grid |
| `xl` | `1280px` | Full desktop treatment |

The `lg` breakpoint is intentionally `900px`, not `1024px`, so tablets and small laptops get structured layouts earlier.

## Common Page Layouts

### Home Page

Desktop:

- Hero text: columns `1 / 7`.
- Social preview: columns `8 / 13`.
- Profile card: columns `1 / 4`.
- Ground cards: columns `4 / 13`.
- Map: columns `1 / 8`.
- Activity rail: columns `8 / 13`.

Mobile:

- One column.
- Hero preview card can sit below hero text.
- Ground cards scroll as a horizontal carousel only if cards remain readable; otherwise stack.

### Ground Detail Page

Desktop:

- Hero text/actions: columns `1 / 7`.
- Fixture/check-in card: columns `8 / 13`.
- Stats: six cards in a 6-column responsive stats grid.
- Address/details: columns `1 / 7`.
- Away fans guide: columns `7 / 13`.
- Checklist: columns `1 / 7`.
- Community/recent visits: columns `7 / 13`.

Mobile:

- One column.
- Claim action should appear near the top and may be repeated as a sticky bottom action on matchday.
- Away fan guidance should stay above social activity because it is practical day-of-match information.

### Profile/List Page

Desktop:

- Profile summary: columns `1 / 4`.
- Main list/map: columns `4 / 13`.
- Filters can be sticky inside the main list column.

Mobile:

- Profile summary first.
- Segmented controls for `Visited`, `Want to go`, `Historic`.
- Filters collapse into a sheet or disclosure.

## Component Sizing

Use container queries for reusable components:

- Ground cards should adapt to parent width, not viewport width.
- Feed rows should hide secondary metadata only when their container is narrow.
- Stat grids should auto-fit columns with a minimum of `9rem`.

Preferred pattern:

```css
.component-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 14rem), 1fr));
  gap: 1rem;
}
```

## Spacing

Use these spacing steps:

| Token | Value |
| --- | --- |
| `--space-1` | `0.25rem` |
| `--space-2` | `0.5rem` |
| `--space-3` | `0.75rem` |
| `--space-4` | `1rem` |
| `--space-6` | `1.5rem` |
| `--space-8` | `2rem` |
| `--space-10` | `2.5rem` |
| `--space-12` | `3rem` |
| `--space-16` | `4rem` |

Avoid large empty bands. The 92 is an app-like product; density should feel considered.
