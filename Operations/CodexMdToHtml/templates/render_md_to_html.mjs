import fsSync from "node:fs";
import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";

function usage() {
  console.error(
    "Usage: node render_md_to_html.mjs <install-root> <css-path> <input.md> <output.html>"
  );
  process.exit(1);
}

if (process.argv.length !== 6) {
  usage();
}

const [, , installRoot, cssPath, inputPathArg, outputPathArg] = process.argv;
const inputPath = path.resolve(inputPathArg);
const outputPath = path.resolve(outputPathArg);
const markedModulePath = path.join(
  installRoot,
  "node_modules",
  "marked",
  "lib",
  "marked.esm.js"
);
const mermaidModuleSourcePath = path.join(
  installRoot,
  "node_modules",
  "mermaid",
  "dist",
  "mermaid.min.js"
);

function slugify(value) {
  return value
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/&[a-z]+;/gi, "-")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "") || "section";
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function stripTags(value) {
  return value
    .replace(/<code>(.*?)<\/code>/g, "$1")
    .replace(/<[^>]+>/g, "")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&#39;/g, "'")
    .replace(/&quot;/g, '"')
    .trim();
}

function extractLead(markdown) {
  const lines = markdown.split(/\r?\n/);
  let inFence = false;
  let seenTitle = false;
  const paragraphs = [];
  let current = [];

  function flushParagraph() {
    if (current.length === 0) {
      return;
    }
    const text = current.join(" ").trim();
    if (text) {
      paragraphs.push(text);
    }
    current = [];
  }

  for (const line of lines) {
    if (line.trim().startsWith("```")) {
      inFence = !inFence;
      continue;
    }

    if (inFence) {
      continue;
    }

    if (!seenTitle) {
      if (line.startsWith("# ")) {
        seenTitle = true;
      }
      continue;
    }

    if (line.startsWith("## ")) {
      break;
    }

    if (!line.trim()) {
      flushParagraph();
      continue;
    }

    if (/^[-*]\s/.test(line) || /^\d+\.\s/.test(line) || line.startsWith("|")) {
      flushParagraph();
      continue;
    }

    current.push(line.trim());
  }

  flushParagraph();
  return paragraphs[0] || "";
}

function rewriteMarkdownLinks(html, sourceDir) {
  return html.replace(/href="([^"]+)"/g, (match, href) => {
    if (
      href.startsWith("#") ||
      href.startsWith("http://") ||
      href.startsWith("https://") ||
      href.startsWith("mailto:") ||
      href.startsWith("tel:")
    ) {
      return match;
    }

    const hrefMatch = href.match(/^([^?#]+)(.*)$/);
    if (!hrefMatch || !/\.md$/i.test(hrefMatch[1])) {
      return match;
    }

    const [, pathPart, suffix] = hrefMatch;
    const resolvedMarkdownPath = path.resolve(sourceDir, pathPart);
    const resolvedHtmlPath = resolvedMarkdownPath.replace(/\.md$/i, ".html");
    if (!fsSync.existsSync(resolvedHtmlPath)) {
      return match;
    }

    const updatedHref = `${pathPart.replace(/\.md$/i, ".html")}${suffix}`;
    return `href="${updatedHref}"`;
  });
}

function annotateExternalLinks(html) {
  return html.replace(/<a href="(https?:\/\/[^"]+)">/g, '<a href="$1" target="_blank" rel="noreferrer">');
}

function wrapTables(html) {
  return html.replace(/<table>/g, '<div class="table-wrap"><table>').replace(/<\/table>/g, "</table></div>");
}

function buildMermaidScript(relativeMermaidPath) {
  return `
<script src="${relativeMermaidPath}"></script>
<script>
  if (typeof mermaid === "undefined") {
    console.warn("Mermaid failed to load from local asset.");
  } else {
    mermaid.initialize({
      startOnLoad: false,
      securityLevel: "loose",
      theme: "base",
      themeVariables: {
        primaryColor: "#f4e4cf",
        primaryTextColor: "#211b17",
        primaryBorderColor: "#b98152",
        lineColor: "#214f5c",
        secondaryColor: "#e2eff4",
        tertiaryColor: "#fff8f0",
        clusterBkg: "#fffaf4",
        clusterBorder: "#c9b9a7",
        edgeLabelBackground: "#fffaf4",
        fontFamily: "Georgia, Times New Roman, serif",
        fontSize: "18px"
      },
      flowchart: {
        curve: "basis",
        padding: 18,
        nodeSpacing: 34,
        rankSpacing: 46,
        useMaxWidth: true,
        htmlLabels: true
      }
    });

    const mermaidBlocks = Array.from(document.querySelectorAll("pre > code.language-mermaid"));
    for (const codeBlock of mermaidBlocks) {
      const shell = document.createElement("figure");
      shell.className = "diagram-shell";

      const toolbar = document.createElement("div");
      toolbar.className = "diagram-toolbar";

      const label = document.createElement("span");
      label.className = "diagram-label";
      label.textContent = "Diagram";
      toolbar.appendChild(label);

      const body = document.createElement("div");
      body.className = "diagram-body";

      const host = document.createElement("div");
      host.className = "mermaid";
      host.dataset.rendered = "false";
      host.textContent = codeBlock.textContent.trim();

      body.appendChild(host);
      shell.appendChild(toolbar);
      shell.appendChild(body);
      codeBlock.parentElement.replaceWith(shell);
    }

    if (mermaidBlocks.length > 0) {
      mermaid.run({ querySelector: ".mermaid" });
    }
  }
</script>`;
}

const { marked } = await import(pathToFileURL(markedModulePath).href);
const markdown = await fs.readFile(inputPath, "utf8");
const css = await fs.readFile(cssPath, "utf8");
const hasMermaid = /```mermaid\b/.test(markdown);
const lead = extractLead(markdown);

let htmlBody = marked.parse(markdown, {
  gfm: true,
  breaks: false
});

htmlBody = rewriteMarkdownLinks(htmlBody, path.dirname(inputPath));
htmlBody = annotateExternalLinks(htmlBody);
htmlBody = wrapTables(htmlBody);

const headings = [];
const usedSlugs = new Map();

htmlBody = htmlBody.replace(/<h([1-6])>([\s\S]*?)<\/h\1>/g, (fullMatch, levelText, innerHtml) => {
  const level = Number(levelText);
  const text = stripTags(innerHtml);
  let slug = slugify(text);
  const count = usedSlugs.get(slug) ?? 0;
  usedSlugs.set(slug, count + 1);
  if (count > 0) {
    slug = `${slug}-${count + 1}`;
  }
  headings.push({ level, text, slug });
  return `<h${level} id="${slug}">${innerHtml}</h${level}>`;
});

const titleHeading = headings.find((heading) => heading.level === 1);
const title = titleHeading?.text ?? path.basename(inputPath, path.extname(inputPath));
const sectionLinks = headings.filter((heading) => heading.level === 2);
const sourceRelativeName = path.basename(inputPath);

if (titleHeading) {
  htmlBody = htmlBody.replace(/^<h1 id="[^"]+">[\s\S]*?<\/h1>\s*/i, "");
}

let mermaidScript = "";
if (hasMermaid) {
  const assetDirName = `${path.basename(outputPath, path.extname(outputPath))}.assets`;
  const assetDirPath = path.join(path.dirname(outputPath), assetDirName);
  await fs.mkdir(assetDirPath, { recursive: true });
  const mermaidTargetPath = path.join(assetDirPath, "mermaid.min.js");
  await fs.copyFile(mermaidModuleSourcePath, mermaidTargetPath);
  const relativeMermaidPath = `./${assetDirName}/mermaid.min.js`;
  mermaidScript = buildMermaidScript(relativeMermaidPath);
}

const heroLead = lead
  ? `<p class="lead">${escapeHtml(lead)}</p>`
  : `<p class="lead">Rendered from trusted local Markdown with the CodexMdToHtml workflow.</p>`;

const heroNav = sectionLinks.length
  ? `
      <div class="hero-nav">
        ${sectionLinks
          .map((heading) => `<a href="#${heading.slug}">${escapeHtml(heading.text)}</a>`)
          .join("\n        ")}
      </div>`
  : "";

const generatedAt = new Date().toISOString().replace("T", " ").replace(/\.\d+Z$/, " UTC");

const documentHtml = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>${escapeHtml(title)}</title>
  <style>
${css}
  </style>
</head>
<body>
  <div class="page">
    <section class="hero">
      <p class="eyebrow">Codex Markdown View</p>
      <h1>${escapeHtml(title)}</h1>
      ${heroLead}
      <div class="hero-meta">
        <span class="pill">Source: <code>${escapeHtml(sourceRelativeName)}</code></span>
        <span class="pill">Generated: ${escapeHtml(generatedAt)}</span>
      </div>
      <div class="hero-links">
        <a href="./${encodeURI(sourceRelativeName)}">Open Markdown Source</a>
      </div>
${heroNav}
    </section>

    <main class="content">
      <article>
${htmlBody}
      </article>
    </main>

    <div class="footer">
      Generated by <code>AIRoot/Operations/CodexMdToHtml/render_md_to_html.sh</code>.
    </div>
  </div>
${mermaidScript}
</body>
</html>
`;

await fs.writeFile(outputPath, documentHtml, "utf8");
