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

### GitHub Pages Launch Checklist

Use this exact sequence:

1. Push the latest `docs/` changes to the default branch.
2. Open `Settings -> Pages`.
3. Set:
   - `Source`: `Deploy from a branch`
   - `Branch`: default branch
   - `Folder`: `/docs`
4. Wait for the first successful Pages deploy.
5. Open the published site:
   - `https://foxsterdev.github.io/ai-research-hub/`
6. Confirm that these files load publicly:
   - `/`
   - `/robots.txt`
   - `/sitemap.xml`
7. Set the repo `Website` field to:
   - `https://foxsterdev.github.io/ai-research-hub/`
8. Upload the social preview image:
   - `docs/assets/airroot-social-card.jpg`

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

## Search Console Launch Checklist

For GitHub Pages on a project URL, use a `URL-prefix property`, not a domain property.

Recommended property:

- `https://foxsterdev.github.io/ai-research-hub/`

Why:

- a domain property requires DNS verification
- this site lives on a GitHub-owned host under a path
- the exact Pages URL is the cleanest property boundary

### Add and verify the property

1. Open Search Console:
   - `https://search.google.com/search-console`
2. Add a new property.
3. Choose `URL-prefix`.
4. Enter:
   - `https://foxsterdev.github.io/ai-research-hub/`
5. Choose one verification method:
   - `HTML file upload`
   - or `HTML tag`

Practical recommendation for this repo:

- prefer `HTML file upload` if Google gives you a downloadable verification file
- commit that file into `docs/` so it is served at the required Pages URL
- if you use the `HTML tag` method instead, paste the verification meta tag into `docs/index.html`

### After verification

1. Open `Sitemaps` in Search Console.
2. Submit:
   - `https://foxsterdev.github.io/ai-research-hub/sitemap.xml`
3. Use `URL Inspection` for:
   - `https://foxsterdev.github.io/ai-research-hub/`
4. Run `Test Live URL`.
5. If the page is accessible, click `Request indexing`.

### First checks after launch

Within the first few days, check:

- `Page indexing`
- `Sitemaps`
- `Enhancements` or structured data status when available
- `Performance` after data starts appearing

### What should already be in the site

These are now present in `docs/`:

- canonical URL in `index.html`
- crawlable internal links
- `robots.txt`
- `sitemap.xml`
- JSON-LD structured data
- social preview metadata

### Common mistakes to avoid

- verifying `https://foxsterdev.github.io/` instead of the full project-site path
- forgetting to push `robots.txt` or `sitemap.xml`
- changing the Pages URL and leaving the canonical URL stale
- publishing the page but not submitting the sitemap
- using vague or generic page titles after launch

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
- `docs/consulting.html` from `Operations/AI_PREMIUM_CONSULTING_OFFER_PAGE.html`
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
4. Use the JPG social card asset as the repository preview image.

## Notes

- `AIRoot` stays routerless. Pages should explain the architecture, not become a runtime layer.
- Keep host-private protocol families and mutable host state out of the public landing page.
- If Search Console verification uses an HTML file, keep that file in `docs/` and do not rename it.
- If the page evolves, keep links pointed at public-safe docs:
  - `Operations/AI_PROTOCOL_HANDBOOK.md`
  - `Visuals/AI_PROTOCOL_VISUAL_MAP.md`
  - `INTEGRATION.md`
  - `Operations/SETUP_INDEX.md`
