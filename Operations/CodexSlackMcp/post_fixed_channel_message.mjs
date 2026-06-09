#!/usr/bin/env node

import { access, readFile } from "node:fs/promises";
import { spawn } from "node:child_process";
import os from "node:os";
import path from "node:path";

const DEFAULT_RUN_SH = path.join(os.homedir(), ".codex-tools/slack-single-channel-mcp/run.sh");

function parseArgs(argv) {
  const parsed = {};

  for (let index = 0; index < argv.length; index++)
  {
    const arg = argv[index];

    if (arg === "--help" || arg === "-h") {
      parsed.help = true;
      continue;
    }

    if (arg === "--text") {
      parsed.text = readValue(argv, ++index, arg);
      continue;
    }

    if (arg === "--file") {
      parsed.file = readValue(argv, ++index, arg);
      continue;
    }

    if (arg === "--run-sh") {
      parsed.runSh = readValue(argv, ++index, arg);
      continue;
    }

    throw new Error(`Unknown argument: ${arg}`);
  }

  return parsed;
}

function readValue(argv, index, flag) {
  const value = argv[index];
  if (!value) {
    throw new Error(`Missing value for ${flag}.`);
  }

  return value;
}

async function loadMessageText(args) {
  if (args.text && args.file) {
    throw new Error("Use either --text or --file, not both.");
  }

  if (args.text) {
    return requireText(args.text);
  }

  if (args.file) {
    return requireText(await readFile(args.file, "utf8"));
  }

  throw new Error("Missing message. Use --text or --file.");
}

function requireText(value) {
  const text = String(value).trim();
  if (!text) {
    throw new Error("Slack message cannot be empty.");
  }

  return text;
}

async function postToSlack(text, runSh) {
  await access(runSh);

  const client = new McpClient(runSh);
  await client.start();

  try {
    await client.call("initialize", {
      protocolVersion: "2025-03-26",
      capabilities: {},
      clientInfo: { name: "codex-slack-fixed-channel-cli", version: "1.0.0" },
    });

    client.notify("notifications/initialized");

    const response = await client.call("tools/call", {
      name: "slack_post_message",
      arguments: { text },
    }, 60000);

    return response.structuredContent ?? response;
  } finally {
    await client.stop();
  }
}

class McpClient {
  constructor(runSh) {
    this.runSh = runSh;
    this.nextId = 1;
    this.buffer = Buffer.alloc(0);
    this.pending = new Map();
    this.stderr = "";
  }

  async start() {
    this.child = spawn(this.runSh, [], {
      stdio: ["pipe", "pipe", "pipe"],
    });

    this.child.stdout.on("data", (chunk) => {
      this.buffer = Buffer.concat([this.buffer, chunk]);
      this.parseResponses();
    });

    this.child.stderr.on("data", (chunk) => {
      this.stderr += chunk.toString("utf8");
    });

    this.child.on("exit", (code, signal) => {
      for (const { reject, timer } of this.pending.values()) {
        clearTimeout(timer);
        reject(new Error(`Slack MCP exited before response. code=${code} signal=${signal} stderr=${this.stderr}`));
      }

      this.pending.clear();
    });
  }

  async stop() {
    if (this.child?.stdin?.writable) {
      this.child.stdin.end();
    }
  }

  notify(method, params = {}) {
    this.writeMessage({ jsonrpc: "2.0", method, params });
  }

  call(method, params = {}, timeoutMs = 30000) {
    const id = this.nextId++;
    this.writeMessage({ jsonrpc: "2.0", id, method, params });

    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`Timed out waiting for Slack MCP response ${id}. stderr=${this.stderr}`));
      }, timeoutMs);

      this.pending.set(id, { resolve, reject, timer });
    });
  }

  writeMessage(message) {
    const body = Buffer.from(JSON.stringify(message), "utf8");
    this.child.stdin.write(`Content-Length: ${body.length}\r\n\r\n`);
    this.child.stdin.write(body);
  }

  parseResponses() {
    while (true) {
      const headerEnd = this.buffer.indexOf("\r\n\r\n");
      if (headerEnd === -1) {
        return;
      }

      const header = this.buffer.slice(0, headerEnd).toString("utf8");
      const match = /content-length:\s*(\d+)/i.exec(header);
      if (!match) {
        throw new Error(`Invalid MCP header: ${header}`);
      }

      const length = Number.parseInt(match[1], 10);
      const bodyStart = headerEnd + 4;
      const bodyEnd = bodyStart + length;
      if (this.buffer.length < bodyEnd) {
        return;
      }

      const response = JSON.parse(this.buffer.slice(bodyStart, bodyEnd).toString("utf8"));
      this.buffer = this.buffer.slice(bodyEnd);

      const pending = this.pending.get(response.id);
      if (!pending) {
        continue;
      }

      clearTimeout(pending.timer);
      this.pending.delete(response.id);

      if (response.error) {
        pending.reject(new Error(response.error.message));
      } else {
        pending.resolve(response.result);
      }
    }
  }
}

function printHelp() {
  console.log(`Post a message to the configured fixed Slack MCP channel.

Usage:
  node AIRoot/Operations/CodexSlackMcp/post_fixed_channel_message.mjs --file /path/to/message.txt
  node AIRoot/Operations/CodexSlackMcp/post_fixed_channel_message.mjs --text "message"

Options:
  --file <path>      Read Slack message text from a file.
  --text <message>  Slack message text.
  --run-sh <path>   Override the installed Slack MCP run.sh path.
  --help            Show this help.

This helper reads Slack credentials only through the installed fixed-channel MCP wrapper.
It does not print tokens or accept a channel override.`);
}

async function main() {
  const args = parseArgs(process.argv.slice(2));

  if (args.help) {
    printHelp();
    return;
  }

  const text = await loadMessageText(args);
  const result = await postToSlack(text, args.runSh ?? DEFAULT_RUN_SH);
  console.log(JSON.stringify(result, null, 2));
}

await main();
