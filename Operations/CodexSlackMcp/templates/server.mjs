#!/usr/bin/env node

const SERVER_NAME = "slack-single-channel";
const SERVER_VERSION = "0.1.0";
const PROTOCOL_VERSION = "2025-03-26";

const token = process.env.SLACK_BOT_TOKEN ?? "";
const readToken = process.env.SLACK_READ_TOKEN?.trim() || token;
const threadReadEnabled = Boolean(process.env.SLACK_READ_TOKEN?.trim());
const allowedChannelId = process.env.SLACK_ALLOWED_CHANNEL_ID ?? "";

if (!token || !allowedChannelId) {
  console.error(
    `[${SERVER_NAME}] Missing required env vars. Expected SLACK_BOT_TOKEN and SLACK_ALLOWED_CHANNEL_ID.`,
  );
  process.exit(1);
}

let inputBuffer = Buffer.alloc(0);

process.stdin.on("data", (chunk) => {
  inputBuffer = Buffer.concat([inputBuffer, chunk]);
  processBuffer().catch((error) => {
    console.error(`[${SERVER_NAME}] ${formatError(error)}`);
  });
});

process.stdin.on("end", () => {
  process.exit(0);
});

function processBuffer() {
  while (true) {
    const headerEnd = inputBuffer.indexOf("\r\n\r\n");
    if (headerEnd === -1) {
      return Promise.resolve();
    }

    const headerText = inputBuffer.slice(0, headerEnd).toString("utf8");
    const headers = parseHeaders(headerText);
    const contentLength = Number.parseInt(headers["content-length"] ?? "", 10);
    if (!Number.isFinite(contentLength) || contentLength < 0) {
      throw new Error("Invalid Content-Length header.");
    }

    const messageEnd = headerEnd + 4 + contentLength;
    if (inputBuffer.length < messageEnd) {
      return Promise.resolve();
    }

    const body = inputBuffer.slice(headerEnd + 4, messageEnd).toString("utf8");
    inputBuffer = inputBuffer.slice(messageEnd);
    const message = JSON.parse(body);
    void handleMessage(message);
  }
}

function parseHeaders(headerText) {
  const headers = {};
  for (const line of headerText.split("\r\n")) {
    const separator = line.indexOf(":");
    if (separator === -1) {
      continue;
    }
    const key = line.slice(0, separator).trim().toLowerCase();
    const value = line.slice(separator + 1).trim();
    headers[key] = value;
  }
  return headers;
}

async function handleMessage(message) {
  if (!message || typeof message.method !== "string") {
    return;
  }

  if (Object.prototype.hasOwnProperty.call(message, "id")) {
    try {
      const result = await handleRequest(message.method, message.params ?? {});
      sendMessage({
        jsonrpc: "2.0",
        id: message.id,
        result,
      });
    } catch (error) {
      sendMessage({
        jsonrpc: "2.0",
        id: message.id,
        error: {
          code: -32000,
          message: formatError(error),
        },
      });
    }
    return;
  }

  if (message.method === "notifications/initialized") {
    return;
  }
}

async function handleRequest(method, params) {
  switch (method) {
    case "initialize":
      return {
        protocolVersion: PROTOCOL_VERSION,
        capabilities: {
          tools: {},
        },
        serverInfo: {
          name: SERVER_NAME,
          version: SERVER_VERSION,
        },
      };
    case "ping":
      return {};
    case "tools/list":
      return {
        tools: buildTools(),
      };
    case "tools/call":
      return callTool(params);
    default:
      throw new Error(`Unsupported method: ${method}`);
  }
}

function buildTools() {
  return [
    {
      name: "slack_channel_status",
      description:
        "Validate the configured Slack bot token and show the fixed workspace/channel target.",
      inputSchema: {
        type: "object",
        properties: {},
        additionalProperties: false,
      },
    },
    {
      name: "slack_read_recent",
      description:
        "Read the most recent messages from the fixed Slack channel. This server cannot read any other channel.",
      inputSchema: {
        type: "object",
        properties: {
          limit: {
            type: "integer",
            minimum: 1,
            maximum: 100,
            description: "How many messages to read, default 20.",
          },
        },
        additionalProperties: false,
      },
    },
    {
      name: "slack_read_thread",
      description:
        "Read a thread from the fixed Slack channel using the parent message timestamp. This tool is available only when SLACK_READ_TOKEN is configured.",
      inputSchema: {
        type: "object",
        properties: {
          thread_ts: {
            type: "string",
            description: "Parent message timestamp of the Slack thread.",
          },
          limit: {
            type: "integer",
            minimum: 1,
            maximum: 100,
            description: "How many replies to read, default 50.",
          },
        },
        required: ["thread_ts"],
        additionalProperties: false,
      },
    },
    {
      name: "slack_post_message",
      description:
        "Post a message to the fixed Slack channel. This server cannot post to any other destination.",
      inputSchema: {
        type: "object",
        properties: {
          text: {
            type: "string",
            minLength: 1,
            description: "Message text to send.",
          },
          thread_ts: {
            type: "string",
            description: "Optional parent timestamp to reply inside a thread.",
          },
        },
        required: ["text"],
        additionalProperties: false,
      },
    },
  ].filter((tool) => threadReadEnabled || tool.name !== "slack_read_thread");
}

async function callTool(params) {
  const name = params?.name;
  const args = params?.arguments ?? {};

  switch (name) {
    case "slack_channel_status": {
      const auth = await slackApi("auth.test", {});
      return toolResult({
        ok: true,
        workspace: auth.team,
        team_id: auth.team_id,
        bot_user_id: auth.user_id,
        allowed_channel_id: allowedChannelId,
        thread_read_enabled: threadReadEnabled,
      });
    }
    case "slack_read_recent": {
      const limit = clampInteger(args.limit, 20, 1, 100);
      const response = await slackApi(
        "conversations.history",
        {
          channel: allowedChannelId,
          limit,
        },
        readToken,
      );
      const messages = [...(response.messages ?? [])]
        .reverse()
        .map(sanitizeMessage);
      return toolResult({
        ok: true,
        channel_id: allowedChannelId,
        count: messages.length,
        messages,
      });
    }
    case "slack_read_thread": {
      if (!threadReadEnabled) {
        throw new Error(
          "slack_read_thread is disabled. Set SLACK_READ_TOKEN only if you explicitly accept broader read access.",
        );
      }
      const threadTs = requireNonEmptyString(args.thread_ts, "thread_ts");
      const limit = clampInteger(args.limit, 50, 1, 100);
      const response = await slackApi(
        "conversations.replies",
        {
          channel: allowedChannelId,
          ts: threadTs,
          limit,
        },
        readToken,
      );
      const messages = (response.messages ?? []).map(sanitizeMessage);
      return toolResult({
        ok: true,
        channel_id: allowedChannelId,
        thread_ts: threadTs,
        count: messages.length,
        messages,
      });
    }
    case "slack_post_message": {
      const text = requireNonEmptyString(args.text, "text");
      const threadTs = optionalNonEmptyString(args.thread_ts);
      const response = await slackApi("chat.postMessage", {
        channel: allowedChannelId,
        text,
        ...(threadTs ? { thread_ts: threadTs } : {}),
      });
      return toolResult({
        ok: true,
        channel_id: allowedChannelId,
        ts: response.ts,
        thread_ts: response.message?.thread_ts ?? null,
        permalink_hint:
          "Open the target Slack channel and use the returned ts/thread_ts to verify delivery.",
      });
    }
    default:
      throw new Error(`Unsupported tool: ${String(name)}`);
  }
}

async function slackApi(method, payload, authToken = token) {
  const response = await fetch(`https://slack.com/api/${method}`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${authToken}`,
      "Content-Type": "application/json; charset=utf-8",
    },
    body: JSON.stringify(payload),
  });

  const text = await response.text();
  let data;
  try {
    data = JSON.parse(text);
  } catch {
    throw new Error(`Slack API ${method} returned non-JSON response (${response.status}).`);
  }

  if (!response.ok) {
    throw new Error(`Slack API ${method} failed with HTTP ${response.status}.`);
  }
  if (!data.ok) {
    throw new Error(`Slack API ${method} error: ${data.error ?? "unknown_error"}`);
  }
  return data;
}

function sanitizeMessage(message) {
  return {
    ts: message.ts ?? null,
    thread_ts: message.thread_ts ?? null,
    user: message.user ?? null,
    text: message.text ?? "",
    reply_count: message.reply_count ?? 0,
    subtype: message.subtype ?? null,
    bot_id: message.bot_id ?? null,
  };
}

function toolResult(payload) {
  return {
    content: [
      {
        type: "text",
        text: JSON.stringify(payload, null, 2),
      },
    ],
    structuredContent: payload,
  };
}

function sendMessage(message) {
  const body = Buffer.from(JSON.stringify(message), "utf8");
  process.stdout.write(`Content-Length: ${body.length}\r\n\r\n`);
  process.stdout.write(body);
}

function clampInteger(value, fallback, min, max) {
  if (value === undefined || value === null || value === "") {
    return fallback;
  }
  const parsed = Number.parseInt(String(value), 10);
  if (!Number.isFinite(parsed)) {
    throw new Error(`Expected integer value, got: ${value}`);
  }
  return Math.min(max, Math.max(min, parsed));
}

function requireNonEmptyString(value, fieldName) {
  if (typeof value !== "string" || value.trim() === "") {
    throw new Error(`Expected non-empty string for ${fieldName}.`);
  }
  return value.trim();
}

function optionalNonEmptyString(value) {
  if (value === undefined || value === null || value === "") {
    return null;
  }
  if (typeof value !== "string" || value.trim() === "") {
    throw new Error("Optional string fields must be strings when provided.");
  }
  return value.trim();
}

function formatError(error) {
  if (error instanceof Error) {
    return error.message;
  }
  return String(error);
}
