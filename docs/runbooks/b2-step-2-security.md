# B2 Step 2: security baseline and deployment decisions

Scope update, 2026-10-06: the user confirmed local-only project use, without
public exposure, login or keys. The tested local baseline is accepted for that
scope. The external-deployment decisions below are deferred, not prerequisites
for local merging or Step 3. Earlier evidence reports remain historical.

This step is not final production approval. The implemented baseline preserves
B1, the read-only business schemas, provenance/approval gates and existing local
development behavior. No login authority, public exposure, production certificate,
proxy trust or scientific acceptance is invented.

## Implemented local security baseline

- Production Host headers must match an explicit exact allowlist. No wildcard,
  regex, URL/userinfo/path or duplicate/missing Host headers. Ports are validated;
  suffix lookalikes and forwarded-host spoofing do not pass. IPv6 authorities are
  parsed without splitting at the first colon.
- Browser access is denied by default. Explicit origins permit GET/HEAD, not
  writes, credentials/cookies, arbitrary Authorization headers or private-network
  preflights. Range/If-Range and exposed ETag/range/download metadata support maps
  and verified files. Non-browser requests remain possible: CORS is not login or
  authorization and does not make public data confidential.
- Production responses, including error and streaming responses, receive
  nosniff, no-referrer, frame denial, restrictive content-security policy and
  no-store defaults. Existing file lengths, bytes, ranges and ETags are preserved.
  Server/framework identifying headers are suppressed. HSTS is issued only when
  the actual ASGI scheme is HTTPS, never from untrusted forwarding headers.
- Production `/docs`, `/redoc` and `/openapi.json` are disabled. The saved business
  contract remains available to the receiver as a file; local development docs
  and their tests remain available. The OpenAPI description now accurately
  describes the safeguards; business paths/components/examples are unchanged.
- Only read-only HTTP methods are accepted. Requests with bodies or ambiguous
  length/transfer encoding are rejected before reading the body. Application
  header budget is 16 KiB by default. This is not a replacement for edge/server
  connection/rate/timeout limits or an audited HTTP parser.
- Uvicorn still ignores proxy headers and disables access logs. The loopback
  health command explicitly bypasses environment HTTP proxies. Existing
  non-root/read-only containers, private DB secret mounts and reader grants stay.

## Configuration

The API-only Compose stack remains bound to IPv4 loopback. Default production
host allowlist for this stack: `127.0.0.1,localhost,api`. The internal `api` name
permits the isolated container receiving checks; it is not a wildcard.

`B2_ALLOWED_HOSTS`: comma-separated exact lowercase hosts/IPs, at most 32.
No schemes, port suffixes, wildcards or trailing dots. Outside Compose, the
default is just `127.0.0.1,localhost`.

`B2_CORS_ORIGINS`: JSON array of at most 16 exact origin strings, default `[]`.
Use HTTPS origins; HTTP is allowed only for explicitly named loopback development
origins such as `http://localhost:5173`. No credentials, paths, query strings,
fragments, wildcard or `null` origins. The fixture uses an invented `.invalid`
HTTPS origin solely to test the middleware; it is not an approved frontend URL.

`B2_MAX_HEADER_BYTES`: 1–64 KiB, default 16 KiB. It includes header names/values
and framing overhead, not response files. Restart after configuration changes.

`B2_TRUSTED_PROXY_IPS` is unsupported and rejected while the edge policy is
undecided. Do not enable Uvicorn proxy-header trust or wildcard forwarded IPs to
work around it. The API does not interpret forwarded identity or authorization
headers. Production database TLS parameters from Step 1 remain supported, but
the working B1 DB has not been reconfigured or claimed certificate-verified.

## Deferred decisions required only before external deployment

1. Public approved read-only access, or protected access requiring real login?
   Protected access additionally needs the identity provider/gateway, audience,
   trusted issuer/key management and user/role rules. A shared browser API key
   is not a safe substitute for user authentication.
2. Approved frontend origins and API hostname; do not use the fixture origin.
3. Deployment TLS terminator, certificates/renewal, trusted proxy peer addresses
   and enforced HTTPS/routing policy, including prevention of direct-backend
   bypass. These need the deployment owner's agreement and receiving tests.
4. Database TLS/certificate policy for the actual deployment network. The
   isolated local PostGIS rehearsal is not proof of encrypted production DB traffic.

Until these decisions and the corresponding implementation/integration verification
are completed, keep the existing local-only stack. Step 2's local baseline is
accepted for the confirmed local-only scope; Step 3 may proceed. No external
deployment acceptance is implied.
No external service was published, account created, production secret provisioned
or Git operation performed for this baseline.

## Verification

Run the full host suite and fresh disposable-container rehearsal after rebuilding
both images. Require safe configuration rejection, host/proxy spoof rejection,
closed/default and allowlisted CORS, forbidden write/body/header cases, hidden
production docs, headers on successes/errors/streamed files, all eight real
business endpoints, Step 1 dependency failures/recovery, B1 preservation and cleanup.

References: [Starlette middleware](https://starlette.dev/middleware/) and
[OWASP REST security guidance](https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html).
