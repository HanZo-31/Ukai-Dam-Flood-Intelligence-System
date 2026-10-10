// WGS84 <-> UTM zone 43N (EPSG:32643), Krueger series. Pure functions, no lookup service.
// Used so the map view can stay in the rasters' native CRS while the GeoJSON outline
// (EPSG:4326) is placed by a verified transform rather than by guessed bounds.
const A = 6378137.0;
const F = 1 / 298.257223563;
const N = F / (2 - F);
const K0 = 0.9996;
const E0 = 500000;
const LON0 = (75 * Math.PI) / 180; // zone 43 central meridian
const A_HAT = (A / (1 + N)) * (1 + (N * N) / 4 + (N ** 4) / 64);
const ALPHA = [
  N / 2 - (2 * N * N) / 3 + (5 * N ** 3) / 16,
  (13 * N * N) / 48 - (3 * N ** 3) / 5,
  (61 * N ** 3) / 240,
];
const BETA = [
  N / 2 - (2 * N * N) / 3 + (37 * N ** 3) / 96,
  (N * N) / 48 + (N ** 3) / 15,
  (17 * N ** 3) / 480,
];
const DELTA = [
  2 * N - (2 * N * N) / 3 - 2 * N ** 3,
  (7 * N * N) / 3 - (8 * N ** 3) / 5,
  (56 * N ** 3) / 15,
];
const DEG = Math.PI / 180;

/** [lon, lat] degrees -> [easting, northing] metres (northern hemisphere). */
export function lonLatToUtm43(lonLat: readonly number[]): [number, number] {
  const phi = lonLat[1] * DEG;
  const dl = lonLat[0] * DEG - LON0;
  const c = (2 * Math.sqrt(N)) / (1 + N);
  const t = Math.sinh(Math.atanh(Math.sin(phi)) - c * Math.atanh(c * Math.sin(phi)));
  const xiP = Math.atan2(t, Math.cos(dl));
  const etaP = Math.atanh(Math.sin(dl) / Math.sqrt(1 + t * t));
  let xi = xiP;
  let eta = etaP;
  for (let j = 1; j <= 3; j++) {
    xi += ALPHA[j - 1] * Math.sin(2 * j * xiP) * Math.cosh(2 * j * etaP);
    eta += ALPHA[j - 1] * Math.cos(2 * j * xiP) * Math.sinh(2 * j * etaP);
  }
  return [E0 + K0 * A_HAT * eta, K0 * A_HAT * xi];
}

/** [easting, northing] metres -> [lon, lat] degrees. */
export function utm43ToLonLat(en: readonly number[]): [number, number] {
  const xi = en[1] / (K0 * A_HAT);
  const eta = (en[0] - E0) / (K0 * A_HAT);
  let xiP = xi;
  let etaP = eta;
  for (let j = 1; j <= 3; j++) {
    xiP -= BETA[j - 1] * Math.sin(2 * j * xi) * Math.cosh(2 * j * eta);
    etaP -= BETA[j - 1] * Math.cos(2 * j * xi) * Math.sinh(2 * j * eta);
  }
  const chi = Math.asin(Math.sin(xiP) / Math.cosh(etaP));
  let phi = chi;
  for (let j = 1; j <= 3; j++) phi += DELTA[j - 1] * Math.sin(2 * j * chi);
  const lam = LON0 + Math.atan2(Math.sinh(etaP), Math.cos(xiP));
  return [lam / DEG, phi / DEG];
}
