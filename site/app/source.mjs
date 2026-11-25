// Where a report's data comes from (docs/report_page.md §3.1): the package of
// site/package/, fetched only after the visitor submits, opened by the
// envelope's reader as it is. A wrong password opens nothing. The envelopes
// are ciphertext, so the browser's own HTTP cache may keep them; `no-cache`
// revalidates each against Hosting.
import * as env from "./envelope.mjs";

const PACKAGE = "../package/";

export async function open(reportId, profile, password) {
  const manifest = env.parseManifest(await (await fetch(`${PACKAGE}manifest.json`, { cache: "no-cache" })).text());
  const entry = manifest.reports.get(reportId);
  if (!entry) throw new TypeError(`the package has no ${reportId}`);
  const envelope = new Uint8Array(await (await fetch(`${PACKAGE}${entry.file}`, { cache: "no-cache" })).arrayBuffer());
  try {
    const key = await env.login(manifest, profile, password);
    return (await env.openReport(manifest, envelope, reportId, key)).parquet;
  } catch (error) {
    if (error instanceof env.Refused) return null;  // nothing opened
    throw error;
  }
}
