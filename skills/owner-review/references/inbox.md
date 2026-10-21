# Inbox questions from Jcode

Use this route for a genuine owner-dependent question that can wait while independent work continues. Routine uncertainty, progress and completed-work summaries do not belong here. Approval-required actions and material ADRs keep the document-review or GitHub route.

## Check permission before discovery

"Enabled" means the owner or project instructions explicitly permit Inbox use and startup. An installed binary, visible tool or this skill alone is not permission. A closed pilot or operational hold stays off until explicitly released. Do not connect, run `jcode mcp test`, or call Inbox tools to check an OFF service: in Plannotator 0.28.23, even MCP initialization and tool listing start it.

For native capabilities and current schemas, read `plannotator inbox --help` once when needed. It documents questions, attachments, threads, decisions and guided reviews. Those capabilities do not expand this questions-only policy. Do not install another skill or paste the whole guide into the overlay.

## Connect only for authorized use

Reuse a compatible connection/service and record ownership. Otherwise use Jcode's on-demand `mcp` connection, resolving the actual installed binary first:

```json
{
  "action": "connect",
  "server": "plannotator-inbox",
  "command": "plannotator",
  "args": ["inbox", "mcp"],
  "env": {
    "PLANNOTATOR_INBOX_CONNECT": "0",
    "PLANNOTATOR_CWD": "ABSOLUTE_PROJECT_PATH",
    "PLANNOTATOR_UPDATE_CHECK": "0",
    "PLANNOTATOR_BROWSER": "none",
    "PLANNOTATOR_AI": "disabled"
  }
}
```

Replace the project placeholder. Use the resolved binary path when PATH is unreliable. Do not add permanent MCP configuration or auto-connect other agent products. Discover the native tools after this authorized connection.

Pass the actual originating `agent_session` and absolute `project_path` explicitly on every applicable call. The generic shim's generated process identity is not a durable Jcode session identity.

## Ask, notify and retrieve

Use `send_message` with one useful question card, context, meaningful choices, recommendation/reason and room for a note. Check existing project decisions before re-asking a settled question. Keep attachments relevant and non-sensitive. Privately save thread/message IDs, exact question/revision, cursor, stable idempotency key, project and session. Do not blindly retry an uncertain send.

For remote handoff, record existing Serve mappings and use native `inbox --background --tailscale`, never Funnel or a manual proxy. Require the configured exact review host and declared port. Verify the actual HTTPS root serves the intended project/question. Use the parent skill's checked Telegram attention handoff, not a localhost URL or thread fragment. Workers report to their coordinator instead.

Tell the owner to press **Send**, then resume the originating chat with **check my Inbox reply** if its turn has ended. Jcode's generic MCP connection has **no automatic wake**. Continue independent work. At a useful boundary, call `wait_for_reply` with saved IDs/cursor and `timeout_seconds=25`. Pending is not permission. Do not poll continuously. This client's `read_thread` may expose only counts: use the actual returned reply text, not that summary.

Before applying an answer, match project, session, thread/message and exact question/revision. Acknowledged, skipped, empty or stale responses do not settle a choice or authorize unrelated work. After resolution, preserve messages/receipts. Disconnect and stop only owned temporary resources, verifying unrelated Serve mappings remain intact. Never stop a reused service you do not own.
