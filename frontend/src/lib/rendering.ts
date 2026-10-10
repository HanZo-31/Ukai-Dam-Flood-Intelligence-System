/** Probe real context availability. The explicit raster=off diagnostic never claims a GPU failure. */
export function supportsRaster(createCanvas: () => Pick<HTMLCanvasElement, "getContext">, search = ""): boolean {
  if (new URLSearchParams(search).get("raster") === "off") return false;
  try {
    const canvas = createCanvas();
    const context = canvas.getContext("webgl2") || canvas.getContext("webgl");
    if (!context) return false;
    // Release the probe context; it is not a map renderer.
    (context as WebGLRenderingContext).getExtension?.("WEBGL_lose_context")?.loseContext();
    return true;
  } catch { return false; }
}
