# AIRoot Pages Publishing

This folder is prepared for a GitHub Pages entry site for the `FoxsterDev/ai-research-hub` repository.

## Files

- `docs/index.html`
  Public landing page for newcomers.
- `docs/assets/airroot-architecture.svg`
  Source infographic used by the landing page.
- `docs/assets/airroot-social-card.svg`
  Source social preview card in the correct wide format.
- `docs/assets/airroot-social-card.jpg`
  Ready-to-upload repository social preview image.
- `docs/.nojekyll`
  Disables Jekyll processing so Pages serves the static files as-is.

## GitHub Settings

## Suggested Repo Text

### Recommended Description

Use this as the primary repository description:

`Public reusable AI operating layer for engineering repositories: XUUnity, setup contracts, visuals, templates, and integration docs.`

### Shorter Description

Use this if you want a tighter top-line:

`Public AI operating layer for repo-attached engineering workflows, built around XUUnity.`

### Website Label Context

Use this mental model for the `Website` field:

- repo `Description` explains what the repository is
- repo `Website` points to the visual onboarding page in GitHub Pages

### Suggested Social / About Blurb

Use this when you need a one-line intro in posts, shares, or profile context:

`AIRoot is the public protocol layer behind engineering-focused AI workflows, designed to mount into real repos without owning their runtime truth.`

### Pages

In:
- `Settings -> Pages`

Use:
- `Source`: `Deploy from a branch`
- `Branch`: current default branch
- `Folder`: `/docs`

Result:
- the landing page will publish from `docs/index.html`

### About Section

In:
- repo home page sidebar -> `About` -> gear icon

Set:
- `Website`: the GitHub Pages URL for this repo after Pages is enabled

This gives newcomers:
- `README.md` on the `Code` tab
- a cleaner visual onboarding page from the `Website` link

### Social Preview

In:
- `Settings -> General` or repo `About` media controls, depending on GitHub UI version

Upload:
- `docs/assets/airroot-social-card.jpg`

### Refreshing Derived Docs

Do not maintain the site HTML by hand when the public markdown source changes.

Use:

```bash
bash scripts/refresh_public_site.sh
```

This refreshes:

- `docs/visual-map.html` from `Visuals/AI_PROTOCOL_VISUAL_MAP.md`
- `docs/handbook.html` from `Operations/AI_PROTOCOL_HANDBOOK.md`
- `docs/setup-index.html` from `Operations/SETUP_INDEX.md`
- `docs/integration.html` from `INTEGRATION.md`
- social preview derivatives from `docs/assets/airroot-social-card.svg` when local tools are available

Recommended rule:
- markdown in `Visuals/`, `Operations/`, and repo root stays source of truth
- `docs/*.html` stays derived output for the public site
- no separate protocol family is needed for this; a small public operation is enough

## Suggested Topics

These improve discoverability without changing system behavior:

- `ai`
- `developer-tools`
- `documentation`
- `unity`
- `automation`
- `knowledge-system`

## Recommended Public Entry Flow

1. Keep `README.md` as the code-tab technical entrypoint.
2. Use GitHub Pages as the visual onboarding surface.
3. Point the repo `Website` field to the Pages URL.
4. Use the PNG asset as the social preview card.

## Notes

- `AIRoot` stays routerless. Pages should explain the architecture, not become a runtime layer.
- Keep host-private protocol families and mutable host state out of the public landing page.
- If the page evolves, keep links pointed at public-safe docs:
  - `Operations/AI_PROTOCOL_HANDBOOK.md`
  - `Visuals/AI_PROTOCOL_VISUAL_MAP.md`
  - `INTEGRATION.md`
  - `Operations/SETUP_INDEX.md`
