# Forcing provenance — 2006

File: `flow_forcing_2006_hourly_139.txt` (139 hourly values, m3/s, 2006-08-06 00:00 to 11 Aug 18:00; min 2627, max 25648 at hour 66, last 8495).

## How it was built
1. Twelve-hourly release volumes in million cubic metres (13 blocks, 5 Aug 13:00-24:00 to 11 Aug 13:00-24:00): 55, 172, 279, 539, 978, 1040, 1108, 1058, 835, 771, 669, 478, 367. **The primary source for these values has not been re-verified.** They were read through a summarising tool earlier in the session.
2. Each block converted to mean discharge: MCM x 1e6 / 43200 s (peak block 1108 MCM = 25,648 m3/s).
3. Block mean assigned to the block midpoint; hourly values by linear interpolation (numpy.interp). Sub-12-hour shape is therefore an assumption. Total volume 8,096 MCM vs 8,110 published.
4. Timezone convention not established (assumed local time, IST); not verified.

## Cross-check (2026-10-07) against SANDRP release table (secondary; instantaneous at 0800/2000)
| Time | Table m3/s | Forcing m3/s | Diff |
|---|---|---|---|
| 6 Aug 08:00 | 3,537 | 4,394 | +24% |
| 6 Aug 20:00 | 7,215 | 7,461 | +3% |
| 7 Aug 08:00 | 11,582 | 14,171 | +22% |
| 7 Aug 20:00 | 23,108 | 22,878 | -1% |
| 8 Aug 08:00 | 23,902 | 24,336 | +2% |
| 8 Aug 20:00 | 25,692 | 25,455 | -1% |
| 9 Aug 08:00 | 24,069 | 23,630 | -2% |
| 9 Aug 20:00 | 18,406 | 19,082 | +4% |

Rising limb timing differs (the forcing is smoother and earlier). Cited event peak 25,770-25,780 m3/s. Evidence class: reference/reconstructed, not observed.
