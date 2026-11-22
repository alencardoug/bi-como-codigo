// Probe A7's Vite configuration (docs/framework_prototype.md §3): Evidence's
// own, unchanged — the one `evidence build` writes into .evidence/template/ —,
// with the pinned-engine plugin first. `evidence build --config ../../vite.bice.mjs`
// hands the option to `vite build`, run in .evidence/template/.
import evidence from "./.evidence/template/vite.config.js";
import pinnedEngine from "./pinned-engine.mjs";

export default { ...evidence, plugins: [pinnedEngine(), ...evidence.plugins] };
