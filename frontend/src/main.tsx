import { createRoot } from "react-dom/client";
import "ol/ol.css";
import "./styles.css";
import "./interface.css";
import "./studio.css";
import "./point-inspection.css";
import "./simulation-polish.css";
import App from "./App";

createRoot(document.getElementById("root")!).render(<App />);
