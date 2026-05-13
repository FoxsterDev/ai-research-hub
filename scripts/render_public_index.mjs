import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const toolsHome = process.env.CODEX_TOOLS_HOME || path.join(process.env.HOME, ".codex-tools");
const installRoot = process.env.CODEX_MD_TO_HTML_INSTALL_ROOT || path.join(toolsHome, "md-to-html-cli");
const markedModulePath = path.join(
  installRoot,
  "node_modules",
  "marked",
  "lib",
  "marked.esm.js"
);

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(process.argv[2] || path.join(scriptDir, ".."));
const docsDir = path.join(repoRoot, "docs");
const sourcePath = path.join(docsDir, "INDEX_SOURCE.md");
const templatePath = path.join(docsDir, "index.template.html");
const outputPath = path.join(docsDir, "index.html");

const [sourceMarkdown, templateHtml] = await Promise.all([
  fs.readFile(sourcePath, "utf8"),
  fs.readFile(templatePath, "utf8")
]);

const { marked } = await import(pathToFileURL(markedModulePath).href);

const trimmedSource = sourceMarkdown.trim();
const renderedBody = /^<[-a-zA-Z!\/][\s\S]*>$/.test(trimmedSource)
  ? trimmedSource
  : marked.parse(sourceMarkdown, {
      gfm: true,
      breaks: false
    }).trim();

const generatedAt = new Date().toISOString().replace("T", " ").replace(/\.\d+Z$/, " UTC");
const derivedComment = `<!-- Derived from docs/INDEX_SOURCE.md at ${generatedAt} -->`;
const finalHtml = templateHtml.replace("{{BODY}}", `${derivedComment}\n${renderedBody}`);

await fs.writeFile(outputPath, finalHtml, "utf8");
console.log(`Generated HTML: ${outputPath}`);
