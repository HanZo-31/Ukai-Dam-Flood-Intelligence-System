# HEC-RAS run timestamps, all plans (raw record)

Status: draft evidence. Timezone of the stamps is NOT stored in the HDF files and is **unverified**. Nothing here assumes IST.
Source: plan HDF run-window attribute and stored "Computation Time Total", copied as read. Interval = window end minus window start, computed by subtraction.

| Plan | Scenario | Run window start | Run window end | Interval (s) | Stored total | Stored total (s) | Stored minus interval (s) |
|---|---|---|---|---|---|---|---|
| p03 | H01 | 07OCT2026 02:30:27 | 07OCT2026 03:22:07 | 3100 | 00:51:41 | 3101 | +1 |
| p04 | H02 | 07OCT2026 07:47:27 | 07OCT2026 08:34:11 | 2804 | 00:46:45 | 2805 | +1 |
| p05 | H03 | 07OCT2026 10:18:32 | 07OCT2026 11:09:39 | 3067 | 00:51:08 | 3068 | +1 |
| p06 | 2006 | 07OCT2026 00:28:40 | 07OCT2026 01:33:30 | 3890 | 01:04:51 | 3891 | +1 |

Observation: in all four plans the stored total is exactly 1 s more than the stamp-to-stamp interval. Same sign, same size. Rounding or truncation of start/end stamps to whole seconds is a *possible* explanation; it has **not** been confirmed. Not investigated further because it does not affect any depth/velocity/arrival value.

Bundle `run_log` values (separate source, written by the bundle builder, not by HEC-RAS): H01 51:42, H02 46:45, H03 51:09, 2006 "1 h 05 min" (from an on-screen summary, no seconds). H01 and H03 are 1 s above the HDF totals (51:41, 51:08); H02 matches. Cause unconfirmed. These are runtime *labels*, not scientific results.

Other p04 stamps (compute log): "Simulation started 07Oct2026 07:47:19 AM", Date Processed 07:47:25, Complete Process 46:51. These differ from the HDF window start (07:47:27) by a few seconds; different log points, not reconciled.

What this does not show: the time zone, whether the laptop clock was correct, or anything about model accuracy. p08 (stopped run) is excluded.
