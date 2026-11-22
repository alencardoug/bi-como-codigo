// Probe A8 (docs/framework_prototype.md §3, N100): a Vite plugin that answers
// `@steeze-ui/simple-icons` with only the brand icons Evidence's components
// import by name — the header's four — copied from the package as it is
// installed. Evidence's `@evidence-dev/component-utilities/icons` re-exports
// the whole package (`export *`), which puts its 3,225 icons, 4.8 MB of SVG
// paths, into the build: there, every year from 2000 to 2199 is spelled as the
// gate searches it (`2.024`), and no calendar of the draw can be clean. A name
// imported and not kept fails the build, which says so.
import { readFileSync } from "node:fs";

const KEEP = ["Github", "Slack", "Bluesky", "X"];
const ID = "\0bice-trimmed-icons";

function trimmed() {
  const source = readFileSync(new URL("./node_modules/@steeze-ui/simple-icons/dist/index.js", import.meta.url), "utf8");
  const lines = source.split("\n").filter((line) => KEEP.some((name) => line.startsWith(`export const ${name} = `)));
  if (lines.length !== KEEP.length) throw new Error(`simple-icons: found ${lines.length} of the ${KEEP.length} kept icons`);
  return lines.join("\n") + "\n";
}

export default function trimmedIcons() {
  return {
    name: "bice-trimmed-icons",
    enforce: "pre",
    resolveId(id) {
      return id === "@steeze-ui/simple-icons" ? ID : null;
    },
    load(id) {
      return id === ID ? trimmed() : null;
    },
  };
}
