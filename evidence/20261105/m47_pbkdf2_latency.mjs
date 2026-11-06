// M47 probe: PBKDF2-HMAC-SHA-256 latency in Node's WebCrypto (the browser's API).
const { subtle } = globalThis.crypto;
const pw = new TextEncoder().encode("not-a-real-password");
const salt = crypto.getRandomValues(new Uint8Array(16));
const base = await subtle.importKey("raw", pw, "PBKDF2", false, ["deriveKey"]);
for (const it of [100000, 600000, 1000000]) {
  const ms = [];
  for (let i = 0; i < 5; i++) {
    const t0 = performance.now();
    await subtle.deriveKey({ name: "PBKDF2", salt, iterations: it, hash: "SHA-256" },
      base, { name: "AES-KW", length: 256 }, false, ["unwrapKey"]);
    ms.push(performance.now() - t0);
  }
  ms.sort((a, b) => a - b);
  console.log(`iterations=${it} min=${ms[0].toFixed(1)}ms median=${ms[2].toFixed(1)}ms max=${ms[4].toFixed(1)}ms`);
}
console.log(`node=${process.version} cpu=${(await import("os")).cpus()[0].model}`);
