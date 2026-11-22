// Probe A7's Vite configuration (docs/framework_prototype.md §3): Evidence's
// own, unchanged — the one `evidence build` writes into .evidence/template/ —,
// with the pinned-engine plugin first and the trimmed-icons plugin of probe A8
// (N100). `evidence build --config ../../vite.bice.mjs` hands the option to
// `vite build`, run in .evidence/template/.
import evidence from "./.evidence/template/vite.config.js";
import pinnedEngine from "./pinned-engine.mjs";
import trimmedIcons from "./trimmed-icons.mjs";

export default { ...evidence, plugins: [pinnedEngine(), trimmedIcons(), ...evidence.plugins] };
