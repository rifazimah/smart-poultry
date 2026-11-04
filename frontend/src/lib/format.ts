// Pemformat tampilan (bahasa Indonesia). Tanpa pustaka tanggal/angka tambahan: cukup Intl bawaan browser.

const angka = new Intl.NumberFormat("id-ID", { maximumFractionDigits: 2 });
const rupiah = new Intl.NumberFormat("id-ID", {
  style: "currency",
  currency: "IDR",
  maximumFractionDigits: 0,
});
const persen = new Intl.NumberFormat("id-ID", { style: "percent", maximumFractionDigits: 1 });

export function formatAngka(nilai: number | null | undefined, satuan?: string): string {
  if (nilai === null || nilai === undefined || Number.isNaN(nilai)) return "-";
  const teks = angka.format(nilai);
  return satuan ? `${teks} ${satuan}` : teks;
}

export function formatRupiah(nilai: number | null | undefined): string {
  if (nilai === null || nilai === undefined || Number.isNaN(nilai)) return "-";
  // Intl menghasilkan "Rp 35.892" dengan spasi tak-putus; samakan dengan spasi biasa agar mudah diuji dan disalin.
  return rupiah.format(nilai).replace(/ /g, " ");
}

/** Proporsi 0-1 menjadi persen (0,25 -> "25%"). */
export function formatProporsi(nilai: number | null | undefined): string {
  if (nilai === null || nilai === undefined || Number.isNaN(nilai)) return "-";
  return persen.format(nilai).replace(/ /g, "");
}

/** Gram; di atas 1000 ditampilkan dalam kg agar mudah dibaca. */
export function formatBerat(gram: number | null | undefined): string {
  if (gram === null || gram === undefined || Number.isNaN(gram)) return "-";
  return Math.abs(gram) >= 1000 ? `${angka.format(gram / 1000)} kg` : `${angka.format(gram)} g`;
}

/** Tanggal ISO (YYYY-MM-DD atau waktu ISO) menjadi "2 Nov 2026". */
export function formatTanggal(iso: string | null | undefined): string {
  if (!iso) return "-";
  // Tanggal murni diparse sebagai tanggal lokal agar tidak bergeser zona waktu.
  const tanggalMurni = /^\d{4}-\d{2}-\d{2}$/.test(iso);
  const d = tanggalMurni ? new Date(`${iso}T00:00:00`) : new Date(iso);
  if (Number.isNaN(d.getTime())) return "-";
  return new Intl.DateTimeFormat("id-ID", { day: "numeric", month: "short", year: "numeric" }).format(d);
}

/** Waktu ISO (UTC dari server) menjadi "2 Nov 2026 14.30" menurut zona waktu pengguna. */
export function formatWaktu(iso: string | null | undefined): string {
  if (!iso) return "-";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "-";
  return new Intl.DateTimeFormat("id-ID", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(d);
}

/** Tanggal hari ini menurut zona waktu pengguna, format YYYY-MM-DD (untuk input tanggal). */
export function hariIni(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** Kilogram (teks atau angka dari input) ke gram bulat; kosong/tidak valid -> undefined. */
export function kgKeGram(teks: string): number | undefined {
  if (teks.trim() === "") return undefined;
  const n = Number(teks.replace(",", "."));
  return Number.isFinite(n) ? Math.round(n * 1000) : undefined;
}
