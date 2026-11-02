import { formatAngka, formatBerat, formatProporsi, formatRupiah, formatTanggal, formatWaktu } from "./format";

describe("format", () => {
  it("angka memakai pemisah id-ID dan menangani kosong", () => {
    expect(formatAngka(1234.5)).toBe("1.234,5");
    expect(formatAngka(0.02, "%")).toBe("0,02 %");
    expect(formatAngka(null)).toBe("-");
    expect(formatAngka(undefined)).toBe("-");
    expect(formatAngka(Number.NaN)).toBe("-");
  });

  it("rupiah tanpa desimal dan dengan spasi biasa", () => {
    expect(formatRupiah(35892)).toBe("Rp 35.892");
    expect(formatRupiah(0)).toBe("Rp 0");
    expect(formatRupiah(null)).toBe("-");
  });

  it("proporsi 0-1 menjadi persen", () => {
    expect(formatProporsi(0.64)).toBe("64%");
    expect(formatProporsi(0.025)).toBe("2,5%");
    expect(formatProporsi(undefined)).toBe("-");
  });

  it("berat memakai gram atau kg", () => {
    expect(formatBerat(800)).toBe("800 g");
    expect(formatBerat(1250)).toBe("1,25 kg");
    expect(formatBerat(null)).toBe("-");
  });

  it("tanggal murni tidak bergeser zona waktu", () => {
    expect(formatTanggal("2026-11-02")).toBe("2 Nov 2026");
    expect(formatTanggal("2026-01-01")).toBe("1 Jan 2026");
    expect(formatTanggal(null)).toBe("-");
    expect(formatTanggal("bukan-tanggal")).toBe("-");
  });

  it("waktu ISO diformat dengan jam", () => {
    const hasil = formatWaktu("2026-11-02T10:30:00Z");
    expect(hasil).toMatch(/2 Nov 2026/);
    expect(hasil).toMatch(/\d{2}[.:]\d{2}/);
    expect(formatWaktu("")).toBe("-");
  });
});
