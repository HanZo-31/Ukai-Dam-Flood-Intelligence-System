import { useEffect, useSyncExternalStore } from "react";
import { createComputeClient } from "../lib/compute/client";
import { ComputeController, type ControllerState } from "../lib/compute/controller";
import { browserInflate } from "../lib/tiff";

// One controller for the whole window so a running job and the last accepted result survive switching pages. The page tells it when it is
// shown (resume) and hidden (suspend: polling stops, the job identity is kept, nothing is re-submitted).
let shared: ComputeController | null = null;
export function getComputeController(): ComputeController {
  return (shared ??= new ComputeController({ client: createComputeClient(), inflate: browserInflate }));
}
/** Test/harness seam: replace the controller (e.g. with one wired to a test transport). Application code never calls this. */
export function setComputeControllerForTests(c: ComputeController | null): void { shared?.dispose(); shared = c; }

export function useCompute(active: boolean): { state: ControllerState; controller: ComputeController } {
  const controller = getComputeController();
  const state = useSyncExternalStore(controller.subscribe, controller.getState, controller.getState);
  useEffect(() => {
    if (!active) return;
    void controller.resume();
    void controller.loadCapabilities();
    return () => controller.suspend();
  }, [active, controller]);
  return { state, controller };
}
