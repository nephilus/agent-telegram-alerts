# ADR 0003: Preserve queries in explicit owner action links

- Date: 2026-10-27
- Status: Proposed record of an owner-requested implementation. Document approval and live login completion are separate outcomes.
- Supersedes ADR 0001's blanket attention-query restriction only. ADR 0002's non-443 review-origin contract remains unchanged.

Explicit attention should deliver a service-issued login URL without altering it. Permit non-secret query strings in that explicit interface, while keeping routine extraction conservative and retaining credential checks.

## Context

The installed sender rejected an Omni CLI login URL because its required query contained a flow and public signing-key identifier. Plain text and Markdown wrappers also failed before delivery. Telegram was never contacted with that link. The owner requested removal of this limitation rather than a shortened or rewritten login URL.

## Decision

In the context of explicit owner login handoffs, facing a blanket query ban that prevents delivery of service-issued requests, we decided for query-aware validation in the attention interface and neglected a global relaxation or redirect wrapper, to achieve exact, usable action-link delivery, accepting that intended request identifiers are disclosed to Telegram, because generated authentication requests must reach the owner unchanged.

`safe_action_url` validates explicitly supplied attention links. It retains the existing HTTPS, public-DNS-shaped hostname, port and path checks, without fetching destinations or resolving DNS. It permits at most 2048 characters and 64 query fields, validates escapes, inspects decoded values, and rejects duplicate normalized field names. Accepted query-bearing URLs are returned unchanged rather than parsed and re-encoded for delivery.

Credential-bearing fields, returned authorization codes, PKCE verifiers, access/refresh/identity tokens, signatures and configured secrets remain ineligible. Controls, malformed encodings and fragments remain ineligible. Login request state, nonce, public key identifiers, PKCE challenges and registered redirect URIs are not returned credentials and may be forwarded. These checks are heuristic, not comprehensive secret detection. The caller remains responsible for forwarding only a current URL the service intends the owner to use.

Routine `safe_url` and output extraction keep their blanket query restriction. The declared non-443 review-host exception still permits only its exact trusted HTTPS root origin. Text fields still cannot carry URLs. This change does not alter credentials, native hooks, trust settings, session filters, delivery preferences or approval semantics.

## Alternatives

- Remove all URL checks: unnecessarily permits credential and destination hazards.
- Allow only one Omni host: resolves this incident but leaves other legitimate service-issued action queries unusable.
- Shorten or wrap the URL: obscures the intended destination and evades validation rather than correcting it.
- Put the URL in ordinary text: the attention contract deliberately requires explicit validated link objects.

## Validation and rollback

Exercise exact Omni-shaped and OAuth/PKCE query preservation, encoded credential rejection, unchanged routine extraction, review-host boundaries, no-send failure paths and deduplication. Run the full suite, build distributions, install the task-only wheel into a fresh environment, and check public entrypoints before touching the existing runtime.

A live acceptance send must be clearly labeled as a test and use a harmless query-bearing documentation or review target. Telegram must acknowledge the exact link entity with previews disabled. That receipt does not prove that an owner opened a link or that a separate Omni login succeeded.

Preserve the existing installed wheel as a recovery point. Rollback reinstalls that wheel into the same runtime without changing native settings or hooks. No schema migration or shared-history rewrite is required.
