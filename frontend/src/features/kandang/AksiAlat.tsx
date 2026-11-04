import { useState } from "react";
import { pesanGalat } from "../../api/errors";
import { Button } from "../../components/ui/button";
import { Dialog } from "../../components/ui/dialog";
import { Field } from "../../components/ui/field";
import { FormDialog, KonfirmasiHapus, keAngka, useToast } from "../master-data/bersama";
import { useDaftarBahan } from "../master-data/hooks";
import {
  useDaftarkanAlat,
  useHapusAlat,
  useHapusWadah,
  useRotasiToken,
  useTambahWadah,
  useUbahBahanWadah,
} from "./aksi";
import type { AlatDetail } from "./useDetailKandang";

type WadahAlat = AlatDetail["wadah"][number];

/** Token alat hanya tampil sekali: dialog ini wajib dibaca sebelum ditutup. */
export function TokenDialog({ token, saatTutup }: { token: string | null; saatTutup: () => void }) {
  const [tersalin, setTersalin] = useState<boolean | null>(null);
  const salin = async () => {
    try {
      await navigator.clipboard.writeText(token ?? "");
      setTersalin(true);
    } catch {
      setTersalin(false);
    }
  };
  return (
    <Dialog
      buka={token !== null}
      saatBerubah={(b) => !b && saatTutup()}
      judul="Token alat"
      deskripsi="Simpan token ini sekarang. Token tidak akan ditampilkan lagi; bila hilang, buat token baru lewat Rotasi token."
    >
      <div className="space-y-3">
        <input
          readOnly
          aria-label="Token alat"
          value={token ?? ""}
          onFocus={(e) => e.currentTarget.select()}
          className="block min-h-10 w-full rounded-lg border border-stone-300 bg-stone-50 px-3 font-mono text-xs"
        />
        {tersalin === true && <p role="status" className="text-sm text-brand-700">Token disalin.</p>}
        {tersalin === false && (
          <p role="status" className="text-sm text-stone-600">
            Tidak dapat menyalin otomatis; pilih teks di atas lalu salin manual.
          </p>
        )}
        <div className="flex justify-end gap-2">
          <Button varian="sekunder" onClick={() => void salin()}>
            Salin token
          </Button>
          <Button onClick={saatTutup}>Sudah saya simpan</Button>
        </div>
      </div>
    </Dialog>
  );
}

/**
 * Tombol "Daftarkan alat" untuk kandang yang belum punya alat. Tombol ini hilang begitu alat terdaftar, jadi token
 * diteruskan ke pemanggil (`saatBerhasil`) yang menampilkannya dari komponen yang tetap ada di layar.
 */
export function DaftarkanAlat({ kandangId, saatBerhasil }: { kandangId: string; saatBerhasil: (token: string) => void }) {
  const daftar = useDaftarkanAlat(kandangId);
  return (
    <div className="space-y-2">
      <Button memuat={daftar.isPending} onClick={() => daftar.mutate(undefined, { onSuccess: (a) => saatBerhasil(a.device_token) })}>
        Daftarkan alat
      </Button>
      {daftar.isError && (
        <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800">
          {pesanGalat(daftar.error)}
        </p>
      )}
    </div>
  );
}

/** Aksi tingkat alat (Pemilik): tambah wadah, rotasi token, hapus alat. */
export function AksiAlat({ alat }: { alat: AlatDetail }) {
  const { tampilkan } = useToast();
  const bahan = useDaftarBahan();
  const tambah = useTambahWadah(alat.id);
  const rotasi = useRotasiToken();
  const hapus = useHapusAlat();
  const [form, setForm] = useState(false);
  const [nomor, setNomor] = useState("");
  const [bahanId, setBahanId] = useState("");
  const [galatLokal, setGalatLokal] = useState<string | null>(null);
  const [konfirmasiRotasi, setKonfirmasiRotasi] = useState(false);
  const [konfirmasiHapus, setKonfirmasiHapus] = useState(false);
  const [token, setToken] = useState<string | null>(null);

  const nomorBerikut = alat.wadah.reduce((m, w) => Math.max(m, w.nomor_wadah), 0) + 1;

  const kirim = () => {
    const n = keAngka(nomor);
    if (n == null || !Number.isInteger(n) || n < 1) return setGalatLokal("Nomor wadah harus bilangan bulat 1 atau lebih.");
    setGalatLokal(null);
    tambah.mutate(
      { nomor_wadah: n, bahan_pakan_id: bahanId || null },
      {
        onSuccess: () => {
          setForm(false);
          tampilkan("Wadah ditambahkan", { tipe: "sukses" });
        },
      },
    );
  };

  return (
    <div className="flex flex-wrap gap-2">
      <Button
        varian="sekunder"
        onClick={() => {
          setNomor(String(nomorBerikut));
          setBahanId("");
          setGalatLokal(null);
          tambah.reset();
          setForm(true);
        }}
      >
        Tambah wadah
      </Button>
      <Button
        varian="sekunder"
        onClick={() => {
          rotasi.reset();
          setKonfirmasiRotasi(true);
        }}
      >
        Rotasi token
      </Button>
      <Button
        varian="ghost"
        onClick={() => {
          hapus.reset();
          setKonfirmasiHapus(true);
        }}
      >
        Hapus alat
      </Button>

      <FormDialog
        judul="Tambah wadah"
        buka={form}
        saatTutup={() => setForm(false)}
        memuat={tambah.isPending}
        galat={galatLokal ?? tambah.error}
        saatKirim={kirim}
      >
        <Field label="Nomor wadah" inputMode="numeric" value={nomor} onChange={(e) => setNomor(e.target.value)} required />
        <PilihBahan id="bahan-baru" nilai={bahanId} saatPilih={setBahanId} bahan={bahan.data} />
      </FormDialog>

      <KonfirmasiHapus
        nama={konfirmasiRotasi ? "token alat" : null}
        judul="Buat token baru?"
        deskripsi="Token lama langsung tidak berlaku. Alat (atau simulator) harus dijalankan ulang dengan token baru."
        tombol="Buat token baru"
        saatTutup={() => setKonfirmasiRotasi(false)}
        memuat={rotasi.isPending}
        galat={rotasi.error}
        saatHapus={() =>
          rotasi.mutate(alat.id, {
            onSuccess: (r) => {
              setKonfirmasiRotasi(false);
              setToken(r.device_token);
            },
          })
        }
      />
      <TokenDialog token={token} saatTutup={() => setToken(null)} />

      <KonfirmasiHapus
        nama={konfirmasiHapus ? "alat ini" : null}
        deskripsi="Alat dan semua wadahnya dihapus. Alat yang sudah punya riwayat perintah atau stok yang belum 0 tidak dapat dihapus."
        saatTutup={() => setKonfirmasiHapus(false)}
        memuat={hapus.isPending}
        galat={hapus.error}
        saatHapus={() =>
          hapus.mutate(alat.id, {
            onSuccess: () => {
              setKonfirmasiHapus(false);
              tampilkan("Alat dihapus", { tipe: "sukses" });
            },
          })
        }
      />
    </div>
  );
}

function PilihBahan({
  id,
  nilai,
  saatPilih,
  bahan,
}: {
  id: string;
  nilai: string;
  saatPilih: (v: string) => void;
  bahan: { id: string; nama: string }[] | undefined;
}) {
  return (
    <div className="space-y-1">
      <label htmlFor={id} className="block text-sm font-medium text-stone-700">
        Bahan pakan
      </label>
      <select
        id={id}
        value={nilai}
        onChange={(e) => saatPilih(e.target.value)}
        className="block min-h-10 w-full rounded-lg border border-stone-300 bg-white px-3 text-sm"
      >
        <option value="">Belum diisi</option>
        {bahan?.map((b) => (
          <option key={b.id} value={b.id}>
            {b.nama}
          </option>
        ))}
      </select>
    </div>
  );
}

/** Aksi per wadah (Pemilik): ganti bahan dan hapus. */
export function AksiWadah({ wadah }: { wadah: WadahAlat }) {
  const { tampilkan } = useToast();
  const bahan = useDaftarBahan();
  const ubah = useUbahBahanWadah();
  const hapus = useHapusWadah();
  const [form, setForm] = useState(false);
  const [bahanId, setBahanId] = useState("");
  const [konfirmasiHapus, setKonfirmasiHapus] = useState(false);

  return (
    <div className="flex gap-1">
      <Button
        varian="ghost"
        aria-label={`Ubah bahan wadah ${wadah.nomor_wadah}`}
        onClick={() => {
          setBahanId(wadah.bahan_pakan_id ?? "");
          ubah.reset();
          setForm(true);
        }}
      >
        Ubah bahan
      </Button>
      <Button
        varian="ghost"
        aria-label={`Hapus wadah ${wadah.nomor_wadah}`}
        onClick={() => {
          hapus.reset();
          setKonfirmasiHapus(true);
        }}
      >
        Hapus
      </Button>

      <FormDialog
        judul={`Bahan wadah ${wadah.nomor_wadah}`}
        buka={form}
        saatTutup={() => setForm(false)}
        memuat={ubah.isPending}
        galat={ubah.error}
        saatKirim={() =>
          ubah.mutate(
            { wadahId: wadah.id, bahanId: bahanId || null },
            {
              onSuccess: () => {
                setForm(false);
                tampilkan("Bahan wadah disimpan", { tipe: "sukses" });
              },
            },
          )
        }
      >
        <PilihBahan id={`bahan-${wadah.id}`} nilai={bahanId} saatPilih={setBahanId} bahan={bahan.data} />
      </FormDialog>

      <KonfirmasiHapus
        nama={konfirmasiHapus ? `Wadah ${wadah.nomor_wadah}` : null}
        deskripsi="Wadah dihapus bersama stoknya. Wadah yang pernah mengeluarkan pakan atau yang stoknya belum 0 tidak dapat dihapus."
        saatTutup={() => setKonfirmasiHapus(false)}
        memuat={hapus.isPending}
        galat={hapus.error}
        saatHapus={() =>
          hapus.mutate(wadah.id, {
            onSuccess: () => {
              setKonfirmasiHapus(false);
              tampilkan("Wadah dihapus", { tipe: "sukses" });
            },
          })
        }
      />
    </div>
  );
}
