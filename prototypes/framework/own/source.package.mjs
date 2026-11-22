// The encrypted route's source (docs/framework_prototype.md §2.2): the package
// is fetched from package/ only after the visitor submits, and opened with the
// envelope's reader, unchanged. Its only path to the report is that reader.
import * as env from "./envelope.mjs";

export const mode = "package";

export async function open(password) {
  const manifest = env.parseManifest(await (await fetch("package/manifest.json", { cache: "no-store" })).text());
  const entry = manifest.reports.get("P01");
  if (!entry) throw new TypeError("the package has no P01");
  const envelope = new Uint8Array(await (await fetch(`package/${entry.file}`, { cache: "no-store" })).arrayBuffer());
  try {
    const key = await env.login(manifest, "diretoria", password);
    return (await env.openReport(manifest, envelope, "P01", key)).parquet;
  } catch (error) {
    if (error instanceof env.Refused) return null;  // nothing opened
    throw error;
  }
}
