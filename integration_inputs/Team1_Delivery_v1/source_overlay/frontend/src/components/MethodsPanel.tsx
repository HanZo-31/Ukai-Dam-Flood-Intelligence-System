import { COMPARE_VERSION, WET_THRESHOLD_M } from "../lib/compare";
import { MIN_PAIRED_CELLS, MIN_PAIRED_FRACTION, ZONE_RULE_VERSION, ZONE_SIZE_M } from "../lib/zones";
import { CANDIDATE_CONTRACT_VERSION, PEAK_MAX, PEAK_MIN } from "../lib/candidate";

/** Plain statements of how the comparison, timeline, zone and What-if features work, and what they do not show. Numbers come from the code. */
export default function MethodsPanel() {
  return (
    <section className="methods" aria-labelledby="methods-h">
      <h3 id="methods-h">Methods and limits of the comparison tools</h3>
      <h4>Arrival timeline (Explore)</h4>
      <ul>
        <li>A cell is shown as reached when its stored arrival time is valid and no later than the elapsed time chosen. Cells with no arrival value are never drawn as reached or as safe.</li>
        <li>Time is elapsed model time since the start of the simulation window. No calendar time zone is assumed; the stored clock labels are nominal indexes.</li>
        <li>Depth and velocity coloured on this view are maximum-over-run values, revealed by arrival time. They are not changing water levels.</li>
      </ul>
      <h4>Scenario comparison ({COMPARE_VERSION})</h4>
      <ul>
        <li>All differences are candidate minus baseline. A cell is flooded when maximum depth is above {WET_THRESHOLD_M} m; no-data cells are not counted as dry.</li>
        <li>Rasters are compared only when they share the same grid; nothing is resampled. Cells valid in only one scenario are counted separately and are not part of paired depth or arrival differences.</li>
        <li>The arrival-time difference map colours only cells with a valid arrival in both scenarios, in whole-hour classes (earlier, same, later; steps at 6 and 24 hours). Other cells are left uncoloured, not drawn as no change.</li>
        <li>Areas are cell counts × the raster pixel area (|a·e − b·d| of its transform), shown in km². Maximum velocity is not compared.</li>
        <li>The scenarios differ in hydrograph and are simulated, uncalibrated and not scientifically validated; a difference between them is not a forecast.</li>
      </ul>
      <h4>Coordinate review zones ({ZONE_RULE_VERSION})</h4>
      <ul>
        <li>Zones are fixed {ZONE_SIZE_M / 1000} km squares of the projected grid (EPSG:32643), labelled by the kilometre coordinates of their lower-left corner. They are not administrative areas and carry no population, building or road information.</li>
        <li>Priority for review lists zones with newly flooded area first (largest first), then zones where the candidate reaches cells earlier (largest median advance first). Ties are broken by zone ID so the order is repeatable.</li>
        <li>Timing is used only where at least {MIN_PAIRED_CELLS} cells have an arrival in both scenarios and they cover {MIN_PAIRED_FRACTION * 100}% of cells with an arrival in either. Otherwise timing is shown as not available.</li>
        <li>Priority for review is an ordering for human checking. It is not an evacuation order, a risk score or a recommended dam release.</li>
      </ul>
      <h4>What-if (candidate service, contract {CANDIDATE_CONTRACT_VERSION})</h4>
      <ul>
        <li>The only available mode is selection of an existing stored HEC-RAS reference for a peak release between {PEAK_MIN.toLocaleString("en-US")} and {PEAK_MAX.toLocaleString("en-US")} m³/s. Nothing is computed, interpolated or predicted.</li>
        <li>The range is a selection range, not evidence of calibrated results between the stored peaks. The machine-learning mode stays unavailable while the service says it is.</li>
        <li>The lookup time shown is the service's time to check and find stored data. It is not model run time and not the time to draw a map.</li>
      </ul>
    </section>
  );
}
