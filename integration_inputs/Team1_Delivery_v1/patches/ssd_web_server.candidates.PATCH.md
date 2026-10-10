# Proposed patch for final assembly (NOT applied): route candidate calls in the production server

`scripts/ssd_web_server.cjs` serves the built frontend and proxies every `/api/` request to the baseline API (port 8766). It has no route to the
candidate service (127.0.0.1:8770, contract 1.0.0), so in the packaged app the What-if page reports "candidate service unavailable" and the
reference pages keep working. Team 1 did not change the shared launcher. Final assembly (owner: Team 2 / integration) should apply this small change,
then run the real-service checks listed in docs/CANDIDATE_ADAPTER_NOTES.md.

In `ssd_web_server.cjs`, replace
```js
const apiPort = Number(process.env.UKAI_API_PORT || 8766);
```
by
```js
const apiPort = Number(process.env.UKAI_API_PORT || 8766);
const candidatePort = Number(process.env.UKAI_CANDIDATE_PORT || 8770);
```
and in the `/api/` branch replace
```js
    const headers = {...req.headers, host:`127.0.0.1:${apiPort}`};
    delete headers.connection;
    const outgoing = http.request({hostname:'127.0.0.1',port:apiPort,path:req.url,method:req.method,headers}, upstream => {
```
by
```js
    const toCandidate = req.url.startsWith('/api/v1/candidates/') || req.url === '/api/v1/candidates';
    const targetPort = toCandidate ? candidatePort : apiPort;
    const headers = {...req.headers, host:`127.0.0.1:${targetPort}`};
    delete headers.connection;
    const outgoing = http.request({hostname:'127.0.0.1',port:targetPort,path:req.url,method:req.method,headers}, upstream => {
```
and make the "not available" message name the right service (optional):
`JSON.stringify({detail: toCandidate ? 'The candidate service is not available.' : 'The local API is not available.'})`.

Notes
* POST must pass through unchanged (the `/api/` branch already pipes the request body for every method).
* Reference resources returned by the candidate service (`/api/v1/prototypes/scenarios/...`) must keep going to 8766; the prefix test above only matches `/api/v1/candidates`.
* The supervisor must start the candidate service on 127.0.0.1:8770 (or set `UKAI_CANDIDATE_PORT`); that is Team 2's launcher scope.
* In development (`DEV_FRONTEND.cmd`, port 5175) the equivalent rule already exists in `frontend/vite.config.ts`.

---
## Update 8 Oct (integration note)
Team 2 reports a combined same-origin proxy/launcher (`assembly/ssd_web_server.cjs`, `START_TEAM2.cmd`, port 5176) that already routes the candidate service. That likely **supersedes this patch**. Team 1 has not seen or run Team 2's proxy. Use this file only as a description of the routes the frontend expects (`/api/v1/candidates/*` same-origin, plus the existing `/api/v1/prototypes/...` reference routes); do not replace Team 2's proxy with this patch.
