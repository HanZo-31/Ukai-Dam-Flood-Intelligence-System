import ImageLayer from "ol/layer/Image";
import ImageStatic from "ol/source/ImageStatic";
import terrainUrl from "./terrain/light-terrain.png";
import { TERRAIN_EXTENT } from "./terrain/extent";
import { registerUtm43 } from "./projection";

export const TERRAIN_NOTE = "Local terrain · display only";
export const TERRAIN_LIMITATION = "Derived offline from the supplied terrain. Unlabelled contours and relative shading only: elevation units, vertical datum and source licence remain unverified. Outside its valid footprint the plain grid remains. Not flood depth, water elevation or scientific validation.";

/** Independent backdrop: never fits the view, reads flood values or changes data opacity. */
export function createLocalTerrain(onError: () => void): ImageLayer<ImageStatic> {
  const source = new ImageStatic({ url: terrainUrl, projection: registerUtm43(), imageExtent: [...TERRAIN_EXTENT], interpolate: true });
  source.on("imageloaderror", onError);
  return new ImageLayer({ source, zIndex: -20 });
}
