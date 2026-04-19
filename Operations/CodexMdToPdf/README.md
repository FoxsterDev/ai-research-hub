# Codex Markdown to PDF

This folder contains a public-safe local workflow for converting trusted local
Markdown files into PDF using `md-to-pdf`.

Canonical location:

- `AIRoot/Operations/` because this workflow contains no secrets
- reusable setup, wrapper scripts, and default styling that can be shared across hosts

## Goal

Provide a repeatable Markdown-to-PDF path for Codex workflows that:

- works from the repo without vendoring `node_modules` into the repo
- installs dependencies into a host-local tools folder
- supports trusted local Markdown files and local assets
- gives stable default PDF output for documentation workflows

## Safety Model

Use this workflow only for trusted local Markdown and trusted local assets.

Reason:

- the renderer is browser-based
- Markdown may reference local or remote assets
- browser rendering should not be treated as safe for untrusted content

Do not use this workflow as a sanitizer for unknown input.

## Files

- `init_codex_md_to_pdf.sh`
- `render_md_to_pdf.sh`
- `templates/md-to-pdf.config.js`
- `templates/default.css`

Reusable prompt templates:

- `AIRoot/Templates/CodexMdToPdf/`

## Install

From the repo root:

```bash
bash AIRoot/Operations/CodexMdToPdf/init_codex_md_to_pdf.sh
```

## Render

Basic usage:

```bash
bash AIRoot/Operations/CodexMdToPdf/render_md_to_pdf.sh <input.md>
```

Custom output path:

```bash
bash AIRoot/Operations/CodexMdToPdf/render_md_to_pdf.sh <input.md> <output.pdf>
```

## What It Installs

Dependencies are installed outside the repo by default:

- `~/.codex-tools/md-to-pdf-cli`

You can override this with:

- `CODEX_TOOLS_HOME`

## Current Tool Choice

This workflow uses:

- npm package: `md-to-pdf`
- pinned version: `5.2.5`

Evaluation notes for the selected version:

- license: MIT
- local install completed successfully
- local render test completed successfully on the current macOS host
- npm audit for the installed package reported `0 vulnerabilities` at evaluation time
- upstream GitHub advisory `GHSA-547r-qmjm-8hvw` affects versions `<5.2.5`; this workflow pins the patched `5.2.5` release

Operational rule:

- use this workflow only for trusted local Markdown
- do not treat browser-based rendering as safe for untrusted content

## Default Output Behavior

- page format: A4
- print background: enabled
- reasonable print margins
- simple readable default stylesheet for headings, tables, code, and lists

## PDF Authoring Rules

To reduce ugly page breaks in generated PDFs:

- keep code examples short and focused
- prefer several small code blocks over one large block
- keep headings immediately above the code block they introduce
- avoid placing very large code blocks near a page boundary
- use stylesheet rules that mark `pre`, `table`, `blockquote`, and `img` as `break-inside: avoid`
- prefer compact code-block font size and padding for print output

If a generated PDF still splits a long code sample badly, shorten the sample in the Markdown first instead of trying to force print CSS to keep an oversized block on one page.

## Product-Sheet Layout Pattern

When a README should look polished in PDF form instead of like a plain printed markdown page, prefer this structure:

- start with a compact hero block
- follow with a small fact grid or compatibility panel
- use short feature cards instead of long early bullet lists
- keep code samples short and separated by intent
- use callout blocks for `Basic` versus `Pro` paths or other reader decisions
- keep section rhythm tight so there are no large visual voids between headings and content

Practical implementation pattern:

- use small HTML blocks inside markdown for hero, badges, cards, info panels, and callouts
- add matching CSS classes in `templates/default.css`
- keep the hero text compact; avoid oversized images unless they truly add value
- reserve images for screenshots or diagrams, not as filler
- prefer two-column card grids for print when content is short and scannable
- make sure all custom blocks use `break-inside: avoid-page`

This pattern produced a much cleaner result for the `Connectivity Checker Pro` README PDF than plain markdown headings and bullet lists alone.

## Example

```bash
bash AIRoot/Operations/CodexMdToPdf/render_md_to_pdf.sh \
  /Users/Shared/ConnectivityCheckerPro_1.1.0_release/Assets/FoxsterDev/ConnectivityCheckerPro/README.md \
  /Users/Shared/ConnectivityCheckerPro_1.1.0_release/Assets/ConnectivityCheckerPro/Documentation/README.pdf
```
