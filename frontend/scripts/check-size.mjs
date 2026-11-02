// Memeriksa anggaran ukuran bundle awal (gzip) dari hasil `npm run build`.
// JS/CSS awal = yang dimuat langsung oleh dist/index.html (chunk lazy tidak dihitung).
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { gzipSync } from "node:zlib";

const DIST = join(dirname(fileURLToPath(import.meta.url)), "..", "dist");
const ANGGARAN_KB = { js: 200, css: 30 };

const html = readFileSync(join(DIST, "index.html"), "utf8");
const aset = { js: new Set(), css: new Set() };
for (const m of html.matchAll(/(?:src|href)="\/?(assets\/[^"]+\.(js|css))"/g)) aset[m[2]].add(m[1]);

let gagal = false;
for (const jenis of ["js", "css"]) {
  let total = 0;
  for (const berkas of aset[jenis]) total += gzipSync(readFileSync(join(DIST, berkas))).length;
  const kb = total / 1024;
  const ok = kb <= ANGGARAN_KB[jenis];
  gagal ||= !ok;
  console.log(`${ok ? "OK  " : "GAGAL"} ${jenis.toUpperCase()} awal: ${kb.toFixed(1)} KB gzip (anggaran ${ANGGARAN_KB[jenis]} KB, ${aset[jenis].size} berkas)`);
}
process.exit(gagal ? 1 : 0);
