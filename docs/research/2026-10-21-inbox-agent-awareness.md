# Inbox awareness for Jcode agents

Date: 2026-10-21

**Later owner decision, 2026-10-21 16:10 UTC:** enable Inbox globally and install its MCP if needed. The per-use connection restriction below records the earlier assessment, not the current setup. The [global native adoption instructions](../owner-workflow.md#global-native-mcp-authorized-2026-10-21) supersede it. Questions-only scope, explicit reply retrieval and unrelated operational holds remain unchanged.

## Recommendation

Use a short conditional cue in the existing overlay, advertise Inbox questions in the existing `owner-review` skill, and keep connection/reply instructions in its packaged reference. Connect the native stdio MCP server only for authorized Inbox use. Do not add a second skill, always-on server, custom adapter or automatic wake loop.

This implements agent awareness, not runtime enablement. The earlier questions-only pilot remains closed. A service hold is not released by installing these instructions.

## What official guidance says

[Plannotator's Inbox reference](https://plannotator.ai/docs/reference/inbox/) documents three complementary pieces:

- A native host integration or, for other agents, `plannotator inbox mcp` over stdio. It prefers stdio to a saved HTTP port because that port can change.
- A short reminder or optional instructions note to make the feature discoverable.
- `plannotator inbox --help`, an agent guide covering the tools, question syntax, threads, replies and attachments. A separate Plannotator skill is not required to use Inbox.

The native integrations named there are not a native Jcode integration. A generic MCP client must retrieve replies with `wait_for_reply`; an owner reply does not automatically start another Jcode turn. Pass Jcode's originating session and project explicitly so a process-generated identity does not split a conversation after reconnection.

Official Inbox capabilities include messages, questions, files, annotations, decisions and guided reviews. Our narrower standing preference remains questions only. Progress summaries do not become owner questions, and approval-required actions retain the existing document/GitHub route.

## Important installed-version behavior

The installed guide is Plannotator 0.28.23. Reading `inbox --help` is an offline documentation operation. Connecting its MCP shim is not an OFF-safe discovery operation.

In the [pinned shim](https://github.com/backnotprop/plannotator/blob/e5c03f9968fb97b69986f13290ccf44f10c2d899/apps/hook/server/inbox-mcp-shim.ts#L134-L158), every parsed JSON-RPC request reaches `entry()` before forwarding. That function starts a stopped Inbox. Initialization and `tools/list` can therefore start it even without `send_message`. The [command wiring](https://github.com/backnotprop/plannotator/blob/e5c03f9968fb97b69986f13290ccf44f10c2d899/apps/hook/server/inbox-command.ts#L369-L375) selects this shim.

Consequences:

- Do not add a permanent MCP entry merely to advertise Inbox.
- Do not use `jcode mcp test`, connect or tool discovery to check a service that must remain off.
- Installed software, an advertised skill and an available tool are not startup authorization.
- Keep `PLANNOTATOR_INBOX_CONNECT=0` when an authorized agent starts it, preventing unrelated client auto-configuration.

Jcode's bundled MCP documentation supports on-demand stdio connections with arguments/environment and a default 30-second tool deadline. The reference retains a 25-second reply wait rather than Plannotator's maximum 50 seconds. Do not lower context compaction thresholds or rely on undocumented visibility of MCP initialization instructions.

## What changed

| Layer | Change | Reason |
| --- | --- | --- |
| Overlay | Name Inbox conditionally for genuine small owner decisions | Make the route discoverable without making every uncertainty a question |
| Existing skill description | Mention Inbox questions | Let the skill catalog route Inbox requests to the existing procedure |
| Existing skill body | Link `references/inbox.md` | Avoid depending on a particular repository checkout |
| Packaged reference | Permission, connection, identity, remote handoff, reply and cleanup instructions | Load operational detail only when needed |
| Package and CI | Include and check the reference beside the installed skill | A working checkout must not hide a broken installation |

The overlay is 320 words, versus 319 before. The main skill is 800 words, versus 790. The 493-word reference is loaded on demand. Existing autonomy, plain-language, ADR, attention-delivery and review-trust policies remain intact. No runtime Python module or dependency changed.

## How an enabled use works

1. Investigate and choose ordinary reversible defaults independently. Use Inbox only when owner intent or authority is genuinely missing.
2. Load `owner-review` and its reference. Establish explicit project/startup permission and check holds before connecting.
3. Reuse a compatible service or connect the native stdio server on demand. Attribute applicable calls to the actual originating Jcode session and absolute project path.
4. Send one useful question with context, choices, recommendation/reason and room for a comment. Save the exact question revision and returned identifiers privately.
5. Verify the native Tailscale publication and intended project/question. Send the checked Telegram attention link through the existing route.
6. Continue independent work. Read the actual reply at a useful boundary. If the turn has ended, the owner can resume the originating chat with **check my Inbox reply**.
7. Apply only the matching scoped answer. Preserve the receipt and clean up only temporary resources this run owns.

This is not a guarantee that generic Jcode will wake when the owner presses Send. Adding that capability would be a separate integration project, not a prompt change.

## Validation and limits

The acceptance target for this change is discoverable, self-contained installed guidance that does not alter runtime settings or start Inbox. Observed checks:

| Requirement | Actual check | Observed result |
| --- | --- | --- |
| Discover Inbox without a large overlay | Compare old/new word counts and conditional cue | Overlay 319 to 320 words; enabled-only question route |
| Preserve autonomy and approval boundaries | Full project suite, including all 11 guidance contracts | 250 tests ran, OK with one preexisting skip; ordinary work still has no new approval gate |
| Remove checkout dependency | Build wheel/source archive, install the actual wheel in a fresh environment outside the checkout | All three guidance assets byte-match source; relative skill reference resolves |
| Make the feature visible through Jcode | Reload and read the installed `owner-review` through Jcode's actual skill tool, then read its relative reference | Inbox appears in the description and the new connection/reply procedure is readable |
| Keep configuration and prior pilot intact | Compare protected file hashes before/after installation | Six existing configuration/closed-pilot files unchanged; prior overlay and skill backed up privately |
| Avoid runtime growth | Compare all six runtime modules to the parent commit and inspect wheel metadata | No runtime module changes or runtime dependencies |
| Preserve OFF/startup boundary | Review command history and installed instructions | No MCP connection, tool discovery, Inbox startup, notification or Aorus operation invoked |

These are real packaging, installation and skill-loader checks, not an inference benchmark. They demonstrate that agents can discover and load the instructions, not that every future agent will choose the route correctly.

No new MCP connection, Inbox publication, owner question, Telegram send or Aorus operation is part of this change. A new owner-device round trip is intentionally not claimed. The earlier pilot's real answer established the manual reply path, not automatic wake or permanent cross-project adoption. Validation results and the installed guidance hashes are retained privately; the change PR records the final observed checks.
