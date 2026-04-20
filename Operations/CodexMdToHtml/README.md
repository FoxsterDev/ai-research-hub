# Codex Markdown to HTML

This folder contains a public-safe local workflow for converting trusted local
Markdown files into polished standalone HTML with optional Mermaid rendering.

Canonical location:

- `AIRoot/Operations/` because this workflow contains no secrets
- reusable setup, wrapper scripts, and default styling that can be shared across hosts

## Goal

Provide a repeatable Markdown-to-HTML path for Codex workflows that:

- works from the repo without vendoring `node_modules` into the repo
- installs dependencies into a host-local tools folder
- supports trusted local Markdown files and local assets
- produces readable HTML with heading navigation, code blocks, tables, and Mermaid diagrams

## Safety Model

Use this workflow only for trusted local Markdown and trusted local assets.

Reason:

- Markdown may reference local or remote assets
- raw HTML inside Markdown is preserved
- Mermaid rendering runs client-side in the generated HTML

Do not use this workflow as a sanitizer for unknown input.

## Files

- `init_codex_md_to_html.sh`
- `render_md_to_html.sh`
- `templates/render_md_to_html.mjs`
- `templates/default.css`

## Install

From the repo root:

```bash
bash AIRoot/Operations/CodexMdToHtml/init_codex_md_to_html.sh
```

## Render

Basic usage:

```bash
bash AIRoot/Operations/CodexMdToHtml/render_md_to_html.sh <input.md>
```

Custom output path:

```bash
bash AIRoot/Operations/CodexMdToHtml/render_md_to_html.sh <input.md> <output.html>
```

## What It Installs

Dependencies are installed outside the repo by default:

- `~/.codex-tools/md-to-html-cli`

You can override this with:

- `CODEX_TOOLS_HOME`

## Current Tool Choice

This workflow installs:

- npm package: `marked`
- npm package: `mermaid`

The exact pinned versions live in `init_codex_md_to_html.sh`.

## Output Behavior

- standalone HTML with embedded CSS
- relative `.md` links rewritten to `.html` for local doc browsing
- first-level heading used as page title
- section chips generated from `##` headings when present
- Mermaid code fences rendered in-browser from a local copied script asset
- diagram blocks wrapped in a styled visual shell with a tuned Mermaid theme

## Mermaid Behavior

When the Markdown contains ` ```mermaid ` blocks, the renderer writes a sibling
asset folder next to the output HTML:

- `<output-base>.assets/mermaid.min.js`

This keeps the HTML view self-contained for local browsing without depending on a
remote CDN.

## Example

```bash
bash AIRoot/Operations/CodexMdToHtml/render_md_to_html.sh \
  AIOutput/Operations/AI_PROTOCOL_VISUAL_MAP_INTERNAL.md
```
