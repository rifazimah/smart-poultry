import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { pesanGalat } from "../../api/errors";
import { Button } from "../../components/ui/button";
import { Field } from "../../components/ui/field";
import { FormDialog, KonfirmasiHapus, useToast } from "../master-data/bersama";
import { useBuatKandang, useHapusKandang, useUbahKandang } from "./aksi";
import type { KandangDetail } from "./useDetailKandang";

/** Tombol dan dialog "Tambah kandang" di dashboard (Pemilik). */
export function TambahKandang() {
  const { tampilkan } = useToast();
  const navigate = useNavigate();
  const buat = useBuatKandang();
  const [buka, setBuka] = useState(false);
  const [nama, setNama] = useState("");
  const [lokasi, setLokasi] = useState("");

  return (
    <>
      <Button
        onClick={() => {
          setNama("");
          setLokasi("");
          buat.reset();
          setBuka(true);
        }}
      >
        Tambah kandang
      </Button>
      <FormDialog
        judul="Tambah kandang"
        buka={buka}
        saatTutup={() => setBuka(false)}
        memuat={buat.isPending}
        galat={buat.error}
        saatKirim={() =>
          buat.mutate(
            { nama: nama.trim(), lokasi: lokasi.trim() || null },
            {
              onSuccess: (k) => {
                setBuka(false);
                tampilkan("Kandang dibuat", { tipe: "sukses" });
                navigate(`/kandang/${k.id}`);
              },
            },
          )
        }
      >
        <Field label="Nama kandang" value={nama} onChange={(e) => setNama(e.target.value)} required />
        <Field label="Lokasi (opsional)" value={lokasi} onChange={(e) => setLokasi(e.target.value)} />
      </FormDialog>
    </>
  );
}

/** Ubah, aktifkan/nonaktifkan, dan hapus kandang (Pemilik) di halaman detail. */
export function AksiKandang({ kandang }: { kandang: KandangDetail }) {
  const { tampilkan } = useToast();
  const navigate = useNavigate();
  const ubah = useUbahKandang(kandang.id);
  const hapus = useHapusKandang(kandang.id);
  const [form, setForm] = useState(false);
  const [nama, setNama] = useState("");
  const [lokasi, setLokasi] = useState("");
  const [konfirmasiHapus, setKonfirmasiHapus] = useState(false);
  const aktif = kandang.status === "AKTIF";

  return (
    <div className="flex flex-wrap gap-2">
      <Button
        varian="sekunder"
        onClick={() => {
          setNama(kandang.nama);
          setLokasi(kandang.lokasi ?? "");
          ubah.reset();
          setForm(true);
        }}
      >
        Ubah kandang
      </Button>
      <Button
        varian="sekunder"
        memuat={ubah.isPending && !form}
        onClick={() =>
          ubah.mutate(
            { status: aktif ? "NONAKTIF" : "AKTIF" },
            { onSuccess: () => tampilkan(aktif ? "Kandang dinonaktifkan" : "Kandang diaktifkan", { tipe: "sukses" }) },
          )
        }
      >
        {aktif ? "Nonaktifkan" : "Aktifkan"}
      </Button>
      <Button
        varian="ghost"
        onClick={() => {
          hapus.reset();
          setKonfirmasiHapus(true);
        }}
      >
        Hapus kandang
      </Button>
      {ubah.isError && !form && (
        <p role="alert" className="w-full rounded-lg bg-red-50 p-3 text-sm text-red-800">
          {pesanGalat(ubah.error)}
        </p>
      )}

      <FormDialog
        judul="Ubah kandang"
        buka={form}
        saatTutup={() => setForm(false)}
        memuat={ubah.isPending}
        galat={ubah.error}
        saatKirim={() =>
          ubah.mutate(
            { nama: nama.trim(), lokasi: lokasi.trim() || null },
            {
              onSuccess: () => {
                setForm(false);
                tampilkan("Kandang disimpan", { tipe: "sukses" });
              },
            },
          )
        }
      >
        <Field label="Nama kandang" value={nama} onChange={(e) => setNama(e.target.value)} required />
        <Field label="Lokasi" value={lokasi} onChange={(e) => setLokasi(e.target.value)} />
      </FormDialog>

      <KonfirmasiHapus
        nama={konfirmasiHapus ? kandang.nama : null}
        deskripsi={`"${kandang.nama}" dihapus permanen bersama alat dan wadahnya. Kandang yang pernah punya siklus atau perintah tidak dapat dihapus; nonaktifkan saja.`}
        saatTutup={() => setKonfirmasiHapus(false)}
        memuat={hapus.isPending}
        galat={hapus.error}
        saatHapus={() =>
          hapus.mutate(undefined, {
            onSuccess: () => {
              tampilkan("Kandang dihapus", { tipe: "sukses" });
              navigate("/");
            },
          })
        }
      />
    </div>
  );
}
