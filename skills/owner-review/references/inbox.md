# Inbox questions from Jcode

Use Inbox for genuine owner-dependent questions, not routine uncertainty, progress or completed-work summaries. Approval-required actions and material ADRs keep the document-review or GitHub route. Continue independently authorized work while an answer is pending.

## Global connection and scope

The owner enabled native Inbox globally on 2026-10-21. Reuse the configured `plannotator-inbox` MCP instead of adding duplicate servers or asking for per-project enablement. Explicit project opt-outs forbid that project's calls, not machine-wide service startup. Operational holds retain their scope.

The global entry runs the installed `plannotator inbox mcp` with `PLANNOTATOR_INBOX_CONNECT=0`, `PLANNOTATOR_UPDATE_CHECK=0`, `PLANNOTATOR_BROWSER=none`, `PLANNOTATOR_AI=disabled` and `PLANNOTATOR_INBOX_TAILSCALE=1`. Fresh Jcode processes load it normally. In an older session, use Jcode's named connection:

```json
{"action": "connect", "server": "plannotator-inbox"}
```

If its cached configuration cannot see the entry, reconnect only this server with the same configured native command/environment, or wait for the next normal Jcode start. Do not restart shared Jcode services, reload unrelated servers or auto-connect other agent products. Initialization/tool listing can start Inbox. A machine-wide OFF hold therefore requires disabling its auto-connect entry before discovery, not merely a project instruction. Never test or connect an OFF service to check it.

Pass the actual originating `agent_session` and absolute `project_path` explicitly on every applicable call. Do not pin one project/session in the global environment: shared shim defaults identify its process, not each Jcode caller.

Read `plannotator inbox --help` for current features and schemas when needed. Tool availability does not expand this questions-only policy. Do not paste the entire guide into the overlay.

## Ask, notify and retrieve

Check existing project decisions before re-asking. Use `send_message` with context, meaningful choices or Yes/No, recommendation/reason and room for a note. Include only relevant, non-sensitive attachments. Privately save thread/message IDs, exact question/revision, cursor, stable idempotency key, project and session. Do not blindly retry an uncertain send.

Reuse native Tailscale publication. The global environment requests publication on startup; for an already-running local-only Inbox, use native `inbox --background --tailscale`. Record existing Serve mappings first, never use Funnel or a manual proxy. Require the configured exact review host and declared port. Verify the actual HTTPS root serves the intended project/question, then use the parent skill's checked Telegram attention handoff. Do not forward a localhost URL or thread fragment. Workers report to their coordinator instead.

Tell the owner to press **Send**, then resume the originating chat with **check my Inbox reply** if its turn ended. Jcode's generic MCP has **no automatic wake**. At a useful boundary, use `wait_for_reply` with saved IDs/cursor and `timeout_seconds=25`. Pending is not permission. Do not poll continuously. If `read_thread` displays only counts, retrieve the actual returned reply text instead.

Match project, session, thread/message and exact question/revision before applying an answer. Acknowledged, skipped, empty or stale responses do not settle a choice or authorize unrelated work. Preserve messages/receipts after resolution. The global Inbox is shared: leave it available, and never stop it or remove its publication merely because one question finished. Clean up only owned temporary document-review resources, preserving unrelated Serve mappings.
