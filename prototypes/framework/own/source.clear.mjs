// The clear mode's source (docs/framework_prototype.md §2.5.5, "Clear mode"):
// the page fetches the clear-mode fixture's Parquet, which the clear build put
// beside it, after the visitor submits. There is no envelope and no password:
// any submission opens it. Never part of the encrypted route's build.
export const mode = "clear";

export async function open(_password) {
  return new Uint8Array(await (await fetch("data/p01.parquet", { cache: "no-store" })).arrayBuffer());
}
