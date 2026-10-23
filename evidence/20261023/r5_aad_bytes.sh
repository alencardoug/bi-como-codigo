node --input-type=module <<'JS'
import { webcrypto as c } from 'node:crypto';
import assert from 'node:assert/strict';
const s = c.subtle, encode = x => new TextEncoder().encode(JSON.stringify(x));
const a = {version:1, package:'demo', report:'P01'};
const b = {report:'P01', package:'demo', version:1};
const key = await s.generateKey({name:'AES-GCM', length:256}, false, ['encrypt','decrypt']);
const iv = c.getRandomValues(new Uint8Array(12));
const params = {name:'AES-GCM', iv, tagLength:128, additionalData:encode(a)};
const encrypted = await s.encrypt(params, key, new Uint8Array([1,2,3]));
assert.deepEqual(new Uint8Array(await s.decrypt(params, key, encrypted)), new Uint8Array([1,2,3]));
console.log('Identical AAD bytes: decrypt OK');
assert.deepEqual(a, b);
await assert.rejects(s.decrypt({...params, additionalData:encode(b)}, key, encrypted), {name:'OperationError'});
console.log('Same fields, different JSON order: OperationError');
console.log('Probe only: no product envelope or browser tested');
JS
