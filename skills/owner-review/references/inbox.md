# Inbox questions from agents

Use Inbox for genuine owner-dependent questions, not routine uncertainty, progress or completed-work summaries in this question workflow. Approval-required actions and material ADRs keep the document-review or configured revision-hosting route. Continue independently authorized work while an answer is pending. The companion `plannotator-inbox` skill covers other permitted Inbox interactions.

## Configured connection and scope

Inbox is an optional configured integration, not an assumed global grant. Reuse the configured `plannotator-inbox` MCP server when available and permitted instead of adding duplicate servers or asking for enablement already granted by applicable instructions. Explicit project opt-outs forbid that project's calls, not machine-wide service startup. Operational holds retain their scope.

For a configured native integration, the service may run the installed `plannotator inbox mcp` with `PLANNOTATOR_INBOX_CONNECT=0`, `PLANNOTATOR_UPDATE_CHECK=0`, `PLANNOTATOR_BROWSER=none`, `PLANNOTATOR_AI=disabled` and `PLANNOTATOR_INBOX_TAILSCALE=1`. These are integration settings, not instructions to change shared configuration. Use the current agent's named MCP connection facility for the existing server. If its cached configuration cannot see the entry, reconnect only this server with the configured native command/environment when authorized, or wait for the next normal agent start. Do not restart shared agent services, reload unrelated servers or auto-connect other agent products. Initialization/tool listing can start Inbox. A machine-wide OFF hold therefore requires its auto-connect entry to be disabled before discovery by the authorized operator, not merely a project instruction. Never test or connect an OFF service to check it.

Pass the actual originating `agent_session` and absolute `project_path` explicitly on every applicable call. Do not pin one project/session in shared environment settings: shared shim defaults identify its process, not each caller.

Read `plannotator inbox --help` for current features and schemas when using this integration. Tool availability does not expand this question workflow's scope. Do not paste the entire guide into shared agent instructions.

## Ask, notify and retrieve

Check existing project decisions before re-asking. Use `send_message` with context, meaningful choices or Yes/No, recommendation/reason and room for a note. Include only relevant, non-sensitive attachments. Privately save thread/message IDs, exact question/revision, cursor, stable idempotency key, project and session. Do not blindly retry an uncertain send.

For a configured Tailscale integration, reuse native publication. If configured to publish on startup, reuse that endpoint. For an already-running local-only Inbox, use native `inbox --background --tailscale` only when authorized. Record existing Serve mappings first, never use Funnel or a manual proxy. Require the configured exact review host and declared port. Verify the actual HTTPS root serves the intended project/question, then use the configured `telegram` integration for the parent skill's checked attention handoff, with `abstract` supplying its summary. `owner-review` retains question scope and exact-revision correlation; delivery does not authorize work. Do not forward a localhost URL or thread fragment. Workers report to their coordinator instead.

Tell the owner to press **Send**, then resume the originating session and retrieve the reply using the configured Inbox tool when needed. Do not assume the current MCP client supports automatic wake. At a useful boundary, use `wait_for_reply` with saved IDs/cursor and `timeout_seconds=25` when that tool is available. Pending is not permission. Do not poll continuously. If `read_thread` displays only counts, retrieve the actual returned reply text instead.

Match project, session, thread/message and exact question/revision before applying an answer. Acknowledged, skipped, empty or stale responses do not settle a choice or authorize unrelated work. Preserve messages/receipts after resolution. A shared Inbox must remain available: never stop it or remove its publication merely because one question finished. Clean up only owned temporary document-review resources, preserving unrelated Serve mappings.
