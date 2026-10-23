node --input-type=module <<'JS'
import { webcrypto } from 'node:crypto';
import assert from 'node:assert/strict';
const s = webcrypto.subtle, enc = new TextEncoder(), dec = new TextDecoder();
const random = n => webcrypto.getRandomValues(new Uint8Array(n));
async function kek(password, salt) {
  const p = await s.importKey('raw', enc.encode(password), 'PBKDF2', false, ['deriveKey']);
  return s.deriveKey({name:'PBKDF2', hash:'SHA-256', salt, iterations:100000}, p,
    {name:'AES-KW', length:256}, false, ['wrapKey','unwrapKey']);
}
const passwords = {Diretoria:'senha_complexa_123', Logistica:'complexa_senha_321'};
const salts = {Diretoria:random(16), Logistica:random(16)}, profiles = {};
for (const p of Object.keys(passwords)) profiles[p] = await kek(passwords[p], salts[p]);
const published = {};
for (const report of ['P01','P13']) {
  const key = await s.generateKey({name:'AES-GCM',length:256}, true, ['encrypt','decrypt']);
  const iv = random(12), aad = enc.encode('probe-v1:' + report);
  const ciphertext = await s.encrypt({name:'AES-GCM',iv,additionalData:aad,tagLength:128}, key, enc.encode(report));
  const wraps = {Diretoria:await s.wrapKey('raw',key,profiles.Diretoria,'AES-KW')};
  if (report === 'P13') wraps.Logistica = await s.wrapKey('raw',key,profiles.Logistica,'AES-KW');
  published[report] = {iv,aad,ciphertext,wraps};
}
async function open(report, profile, password, wrappedBy = profile) {
  const p = published[report], k = await kek(password, salts[profile]);
  const key = await s.unwrapKey('raw', p.wraps[wrappedBy], k, 'AES-KW', 'AES-GCM', true, ['encrypt','decrypt']);
  return {key, text:dec.decode(await s.decrypt({name:'AES-GCM',iv:p.iv,additionalData:p.aad,tagLength:128}, key, p.ciphertext))};
}
assert.equal((await open('P13','Logistica',passwords.Logistica)).text, 'P13');
console.log('Logistica password -> P13: OK');
await assert.rejects(open('P01','Logistica',passwords.Logistica,'Diretoria'), {name:'OperationError'});
console.log('Logistica key -> Diretoria wrap for P01: OperationError');
await assert.rejects(open('P13','Logistica','wrong'), {name:'OperationError'});
console.log('Wrong password -> P13: OperationError');
for (const report of Object.keys(published)) {
  assert.equal((await open(report,'Diretoria',passwords.Diretoria)).text, report);
}
console.log('Anonymous reader + public Diretoria password -> P01 and P13: OK');
const {key} = await open('P01','Diretoria',passwords.Diretoria);
const iv = random(12), forged = await s.encrypt({name:'AES-GCM',iv,additionalData:published.P01.aad}, key, enc.encode('altered'));
assert.equal(dec.decode(await s.decrypt({name:'AES-GCM',iv,additionalData:published.P01.aad}, key, forged)), 'altered');
console.log('Public password holder creates valid altered ciphertext: OK');
const corrupt = new Uint8Array(published.P01.ciphertext); corrupt[0] ^= 1;
await assert.rejects(s.decrypt({name:'AES-GCM',iv:published.P01.iv,additionalData:published.P01.aad}, key, corrupt), {name:'OperationError'});
console.log('Bit flip without re-encryption: OperationError');
JS
