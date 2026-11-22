<script>
  // The login of Evidence's encrypted route (docs/framework_prototype.md §2.3, §3, probe A2):
  // nothing is fetched or opened before submit; the package is opened by the envelope's reader,
  // unchanged. Evidence's own browser client is used through its public module — initDB, to wait
  // for its engine, and setParquetURLs, to make the opened Parquet p01.rows, from a blob URL, which
  // also releases the page's queries, held until a source is set —; its DuckDB-WASM instance,
  // which that module does not export, through the global the client sets, only to load the
  // parquet extension pinned (N98) and, at logout, to terminate its worker before the page is
  // replaced.
  import { onMount } from 'svelte';
  import { initDB, setParquetURLs } from '@evidence-dev/universal-sql/client-duckdb';
  import * as env from '$lib/envelope.mjs';
  import pins from 'bice:pins';
  import { session } from '$lib/session.js';

  let password = '';
  let ready = false;
  let failed = false;
  let busy = false;

  let blobUrl = null;

  // initDB rejects after five seconds of an initialization still under way — the WASM may take
  // longer to arrive —: asked again until the engine is instantiated.
  const engine = async () => {
    for (let i = 0; i < 120; i++) {
      try {
        await initDB();
        return window[Symbol.for('EVIDENCE_QUERY_ENGINE')];
      } catch {
        await new Promise((r) => setTimeout(r, 500));
      }
    }
    throw new Error("Evidence's engine did not start");
  };

  onMount(async () => {
    await engine();
    ready = true;  // the page contract: the field is enabled once a submission can be served
  });

  async function open() {
    const manifest = env.parseManifest(await (await fetch('/package/manifest.json', { cache: 'no-store' })).text());
    const entry = manifest.reports.get('P01');
    const envelope = new Uint8Array(await (await fetch(`/package/${entry.file}`, { cache: 'no-store' })).arrayBuffer());
    try {
      const key = await env.login(manifest, 'diretoria', password);
      return (await env.openReport(manifest, envelope, 'P01', key)).parquet;
    } catch (error) {
      if (error instanceof env.Refused) return null;
      throw error;
    }
  }

  async function pinnedBlob(pin) {
    const response = await fetch(pin.url, { integrity: pin.integrity, credentials: 'omit', mode: 'cors' });
    return URL.createObjectURL(new Blob([await response.arrayBuffer()], { type: 'application/wasm' }));
  }

  async function submit() {
    failed = false;
    busy = true;
    try {
      const parquet = await open();
      if (!parquet) {
        failed = true;
        return;
      }
      const db = await engine();
      const c = await db.connect();
      await c.query('SET GLOBAL autoinstall_known_extensions = false');
      await c.query('SET GLOBAL autoload_known_extensions = false');
      const url = await pinnedBlob(pins.parquet);
      await c.query(`LOAD '${url}#/parquet.duckdb_extension.wasm'`);
      URL.revokeObjectURL(url);
      await c.close();
      blobUrl = URL.createObjectURL(new Blob([parquet], { type: 'application/octet-stream' }));
      await setParquetURLs({ p01: ['rows.parquet'] }, { addBasePath: () => blobUrl });
      session.update((n) => n + 1);
    } finally {
      busy = false;
    }
  }

  async function logout() {
    const db = window[Symbol.for('EVIDENCE_QUERY_ENGINE')];
    if (db) await db.terminate();  // the worker, its database and its registered files end here
    if (blobUrl) URL.revokeObjectURL(blobUrl);
    location.replace(location.pathname);
  }
</script>

{#if !$session}
  <form data-bice="login" on:submit|preventDefault={submit}>
    <label for="senha">Senha da Diretoria</label>
    <input id="senha" data-bice="password" type="password" autocomplete="off" bind:value={password} disabled={!ready || busy} />
    <button data-bice="submit" type="submit" disabled={busy}>Entrar</button>
    <p data-bice="login-error" hidden={!failed}>Senha incorreta: nada foi aberto.</p>
  </form>
{:else}
  <button data-bice="logout" type="button" on:click={logout}>Sair</button>
{/if}
