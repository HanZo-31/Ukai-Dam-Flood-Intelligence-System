# Portable SSD copy

Use [../START_HERE_SSD.md](../START_HERE_SSD.md). Start with START_SSD.cmd; this copy uses http://127.0.0.1:5174. The notes below are retained as original development history.

---

# Ukai Flood Explorer — start here

Simulated, uncalibrated prototype. Not scientifically validated.

## Run it (two steps)
1. Start the backend: double-click `START_UKAI.cmd` (project root). Wait for **READY: 4 scenarios verified**.
2. Start the app: double-click `START_FRONTEND.cmd` (project root), then open **http://127.0.0.1:5173**.

The first run needs internet once (`npm install`). After that the app runs offline.
Needs Node.js 20.19 or newer.

Optional production-style check: `START_FRONTEND_PREVIEW.cmd` (builds, then serves the build at the same address).

## What you see
- **Explore**: pick one of the four scenarios on the left, choose Extent / Depth / Velocity / Arrival, change opacity, fit the map. Right panel = evidence.
- **Compare**: table, shared-scale bars, two synchronized maps.
- **Evidence**: engine, sources and licences, model clock, limitations, unavailable products, checksums, downloads.

## Good to know
- No basemap is used on purpose: the map is a plain coordinate view (EPSG:32643, metres).
- Arrival time is stored in minutes and shown in hours.
- "Not available" means the API has no value. It is never shown as zero.
- The app only reads from `/api/v1/prototypes/...` and never changes data.

## If something is wrong
- "API not reachable": start `START_UKAI.cmd` first; the app reconnects by itself.
- "Port 5173 busy": close the other program using it.
- Map says WebGL is needed: use a current Chrome or Edge with hardware acceleration on.

Commands (inside `frontend\`): `npm run dev`, `npm run build`, `npm run preview`, `npm test`, `npm run typecheck`.
