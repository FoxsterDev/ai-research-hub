Upload this local file to Slack as a reply in an existing thread in the fixed
Slack MCP channel.

Path: `<LOCAL_FILE_PATH>`
Title: `<SLACK_FILE_TITLE>`
Thread ts: `<THREAD_TS>`

Optional initial comment:

```text
<INITIAL_COMMENT>
```

Use `slack_upload_file`.
Return:
- uploaded file title
- Slack file id
- permalink if available
- thread ts used
