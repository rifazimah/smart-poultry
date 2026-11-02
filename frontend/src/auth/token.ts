// Penyimpanan token login. localStorage bisa melempar galat (mode privat, data situs diblokir), jadi selalu dibungkus.
const KUNCI = "sp_token";
let cadangan: string | null = null;

export function ambilToken(): string | null {
  try {
    return localStorage.getItem(KUNCI) ?? cadangan;
  } catch {
    return cadangan;
  }
}

export function simpanToken(token: string): void {
  cadangan = token;
  try {
    localStorage.setItem(KUNCI, token);
  } catch {
    /* tetap tersimpan di memori untuk sesi ini */
  }
}

export function hapusToken(): void {
  cadangan = null;
  try {
    localStorage.removeItem(KUNCI);
  } catch {
    /* abaikan */
  }
}
