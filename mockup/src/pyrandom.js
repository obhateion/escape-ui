// ---------- Python's random, bit for bit (so stickers land exactly where tool/gen.py puts them) ----------
// MT19937 + CPython's seeding: random.Random(int) and random.Random(str) (version 2: str + sha512).
const CRC_TABLE = (() => { const t = new Uint32Array(256); for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; } return t; })();
const utf8 = s => new TextEncoder().encode(s);
function crc32(s) { let c = 0xffffffff; for (const b of utf8(s)) c = CRC_TABLE[(c ^ b) & 0xff] ^ (c >>> 8); return (c ^ 0xffffffff) >>> 0; }

// sha512 with BigInt (only used to seed from strings; a few calls per page)
const SHA512_K = ["428a2f98d728ae22","7137449123ef65cd","b5c0fbcfec4d3b2f","e9b5dba58189dbbc","3956c25bf348b538","59f111f1b605d019","923f82a4af194f9b","ab1c5ed5da6d8118","d807aa98a3030242","12835b0145706fbe","243185be4ee4b28c","550c7dc3d5ffb4e2","72be5d74f27b896f","80deb1fe3b1696b1","9bdc06a725c71235","c19bf174cf692694","e49b69c19ef14ad2","efbe4786384f25e3","0fc19dc68b8cd5b5","240ca1cc77ac9c65","2de92c6f592b0275","4a7484aa6ea6e483","5cb0a9dcbd41fbd4","76f988da831153b5","983e5152ee66dfab","a831c66d2db43210","b00327c898fb213f","bf597fc7beef0ee4","c6e00bf33da88fc2","d5a79147930aa725","06ca6351e003826f","142929670a0e6e70","27b70a8546d22ffc","2e1b21385c26c926","4d2c6dfc5ac42aed","53380d139d95b3df","650a73548baf63de","766a0abb3c77b2a8","81c2c92e47edaee6","92722c851482353b","a2bfe8a14cf10364","a81a664bbc423001","c24b8b70d0f89791","c76c51a30654be30","d192e819d6ef5218","d69906245565a910","f40e35855771202a","106aa07032bbd1b8","19a4c116b8d2d0c8","1e376c085141ab53","2748774cdf8eeb99","34b0bcb5e19b48a8","391c0cb3c5c95a63","4ed8aa4ae3418acb","5b9cca4f7763e373","682e6ff3d6b2b8a3","748f82ee5defb2fc","78a5636f43172f60","84c87814a1f0ab72","8cc702081a6439ec","90befffa23631e28","a4506cebde82bde9","bef9a3f7b2c67915","c67178f2e372532b","ca273eceea26619c","d186b8c721c0c207","eada7dd6cde0eb1e","f57d4f7fee6ed178","06f067aa72176fba","0a637dc5a2c898a6","113f9804bef90dae","1b710b35131c471b","28db77f523047d84","32caab7b40c72493","3c9ebe0a15c9bebc","431d67c49c100d4c","4cc5d4becb3e42b6","597f299cfc657e2a","5fcb6fab3ad6faec","6c44198c4a475817"].map(h => BigInt("0x" + h));
function sha512(bytes) {
  const M = (1n << 64n) - 1n, rotr = (x, n) => ((x >> BigInt(n)) | (x << BigInt(64 - n))) & M;
  let H = ["6a09e667f3bcc908","bb67ae8584caa73b","3c6ef372fe94f82b","a54ff53a5f1d36f1","510e527fade682d1","9b05688c2b3e6c1f","1f83d9abfb41bd6b","5be0cd19137e2179"].map(h => BigInt("0x" + h));
  const L = bytes.length, padLen = ((L + 17 + 127) >> 7) << 7, m = new Uint8Array(padLen);
  m.set(bytes); m[L] = 0x80; let bits = BigInt(L) * 8n;
  for (let i = 0; i < 16; i++) { m[padLen - 1 - i] = Number(bits & 0xffn); bits >>= 8n; }
  const w = new Array(80);
  for (let o = 0; o < padLen; o += 128) {
    for (let i = 0; i < 16; i++) { let v = 0n; for (let j = 0; j < 8; j++) v = (v << 8n) | BigInt(m[o + i * 8 + j]); w[i] = v; }
    for (let i = 16; i < 80; i++) {
      const s0 = rotr(w[i - 15], 1) ^ rotr(w[i - 15], 8) ^ (w[i - 15] >> 7n), s1 = rotr(w[i - 2], 19) ^ rotr(w[i - 2], 61) ^ (w[i - 2] >> 6n);
      w[i] = (w[i - 16] + s0 + w[i - 7] + s1) & M;
    }
    let [a, b, c, d, e, f, g, h] = H;
    for (let i = 0; i < 80; i++) {
      const S1 = rotr(e, 14) ^ rotr(e, 18) ^ rotr(e, 41), ch = (e & f) ^ (~e & M & g);
      const t1 = (h + S1 + ch + SHA512_K[i] + w[i]) & M, S0 = rotr(a, 28) ^ rotr(a, 34) ^ rotr(a, 39), mj = (a & b) ^ (a & c) ^ (b & c);
      const t2 = (S0 + mj) & M; h = g; g = f; f = e; e = (d + t1) & M; d = c; c = b; b = a; a = (t1 + t2) & M;
    }
    H = H.map((x, i) => (x + [a, b, c, d, e, f, g, h][i]) & M);
  }
  const out = new Uint8Array(64);
  H.forEach((x, i) => { for (let j = 7; j >= 0; j--) { out[i * 8 + j] = Number(x & 0xffn); x >>= 8n; } });
  return out;
}

class PyRandom {
  constructor(seed) {
    let n;
    if (typeof seed === "string") {   // version 2: int.from_bytes(s + sha512(s), "big")
      const a = utf8(seed), all = new Uint8Array(a.length + 64); all.set(a); all.set(sha512(a), a.length);
      n = 0n; for (const b of all) n = (n << 8n) | BigInt(b);
    } else n = BigInt(Math.abs(seed));
    const key = []; do { key.push(Number(n & 0xffffffffn)); n >>= 32n; } while (n > 0n);
    this.mt = new Uint32Array(624); this.i = 625; this.initByArray(key);
  }
  initGenrand(s) { const mt = this.mt; mt[0] = s >>> 0; for (let i = 1; i < 624; i++) { const p = mt[i - 1] ^ (mt[i - 1] >>> 30); mt[i] = (Math.imul(1812433253, p) + i) >>> 0; } this.i = 624; }
  initByArray(key) {
    this.initGenrand(19650218); const mt = this.mt, kl = key.length; let i = 1, j = 0;
    for (let k = Math.max(624, kl); k; k--) {
      const p = mt[i - 1] ^ (mt[i - 1] >>> 30);
      mt[i] = ((mt[i] ^ Math.imul(p, 1664525)) + key[j] + j) >>> 0; i++; j++;
      if (i >= 624) { mt[0] = mt[623]; i = 1; } if (j >= kl) j = 0;
    }
    for (let k = 623; k; k--) {
      const p = mt[i - 1] ^ (mt[i - 1] >>> 30);
      mt[i] = ((mt[i] ^ Math.imul(p, 1566083941)) - i) >>> 0; i++;
      if (i >= 624) { mt[0] = mt[623]; i = 1; }
    }
    mt[0] = 0x80000000;
  }
  u32() {
    const mt = this.mt;
    if (this.i >= 624) {
      for (let k = 0; k < 624; k++) {
        const y = (mt[k] & 0x80000000) | (mt[(k + 1) % 624] & 0x7fffffff);
        mt[k] = mt[(k + 397) % 624] ^ (y >>> 1) ^ (y & 1 ? 0x9908b0df : 0);
      }
      this.i = 0;
    }
    let y = mt[this.i++];
    y ^= y >>> 11; y ^= (y << 7) & 0x9d2c5680; y ^= (y << 15) & 0xefc60000; y ^= y >>> 18;
    return y >>> 0;
  }
  random() { const a = this.u32() >>> 5, b = this.u32() >>> 6; return (a * 67108864 + b) / 9007199254740992; }
  getrandbits(k) { return this.u32() >>> (32 - k); }   // k <= 32 is all this page needs
  randbelow(n) { const k = n.toString(2).length; let r = this.getrandbits(k); while (r >= n) r = this.getrandbits(k); return r; }
  randrange(n) { return this.randbelow(n); }
  choice(a) { return a[this.randbelow(a.length)]; }
  shuffle(a) { for (let i = a.length - 1; i > 0; i--) { const j = this.randbelow(i + 1); [a[i], a[j]] = [a[j], a[i]]; } }
}
const rng = seed => new PyRandom(crc32(seed));
