import { useState } from "react";
import { Link } from "react-router-dom";
import { pesanGalat } from "../../api/errors";
import { Button } from "../../components/ui/button";
import { Card } from "../../components/ui/card";
import { Dialog } from "../../components/ui/dialog";
import { Field } from "../../components/ui/field";
import { Spinner } from "../../components/ui/spinner";
import { EmptyState, ErrorState } from "../../components/ui/states";
import { FormDialog, KonfirmasiHapus, useToast } from "./bersama";
import {
  useDaftarJenisAyam,
  useDaftarTemplate,
  useHapusJenisAyam,
  useSalinTemplate,
  useSimpanJenisAyam,
  type JenisAyam,
} from "./hooks";

function SalinTemplateDialog({ saatTutup }: { saatTutup: () => void }) {
  const { tampilkan } = useToast();
  const templat = useDaftarTemplate(true);
  const salin = useSalinTemplate();
  const [nama, setNama] = useState("");

  return (
    <Dialog
      buka
      saatBerubah={(b) => !b && saatTutup()}
      judul="Salin dari template"
      deskripsi="Membuat jenis ayam lengkap dengan fase, kebutuhan nutrisi, dan standar konsumsi. Nutrisi yang belum ada dibuat otomatis."
    >
      <div className="space-y-3">
        <Field label="Nama baru (opsional)" value={nama} onChange={(e) => setNama(e.target.value)} bantuan="Kosong = memakai nama template." />
        {templat.isPending && <Spinner label="Memuat template..." />}
        {templat.isError && <ErrorState pesan={pesanGalat(templat.error)} ulangi={() => void templat.refetch()} />}
        {salin.isError && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800">{pesanGalat(salin.error)}</p>}
        {templat.data && (
          <ul className="space-y-2">
            {templat.data.map((t) => (
              <li key={t.id} className="flex items-start justify-between gap-3 rounded-lg border border-stone-200 p-3">
                <div className="min-w-0">
                  <p className="font-medium text-stone-900">{t.nama}</p>
                  <p className="text-sm text-stone-500">{t.deskripsi}</p>
                  <p className="text-xs text-stone-400">{t.fase.length} fase</p>
                </div>
                <Button
                  memuat={salin.isPending && salin.variables?.templateId === t.id}
                  disabled={salin.isPending}
                  aria-label={`Salin ${t.nama}`}
                  onClick={() =>
                    salin.mutate(
                      { templateId: t.id, nama: nama.trim() || undefined },
                      {
                        onSuccess: (j) => {
                          tampilkan(`Jenis ayam "${j.nama}" dibuat`, { tipe: "sukses" });
                          saatTutup();
                        },
                      },
                    )
                  }
                >
                  Salin
                </Button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </Dialog>
  );
}

export function JenisAyamTab() {
  const { tampilkan } = useToast();
  const daftar = useDaftarJenisAyam();
  const simpan = useSimpanJenisAyam();
  const hapus = useHapusJenisAyam();
  const [form, setForm] = useState<JenisAyam | "baru" | null>(null);
  const [nama, setNama] = useState("");
  const [akanHapus, setAkanHapus] = useState<JenisAyam | null>(null);
  const [template, setTemplate] = useState(false);

  const bukaForm = (j: JenisAyam | "baru") => {
    setNama(j === "baru" ? "" : j.nama);
    simpan.reset();
    setForm(j);
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-stone-500">Jenis ayam beserta fase pertumbuhannya.</p>
        <div className="flex gap-2">
          <Button varian="sekunder" onClick={() => setTemplate(true)}>
            Salin dari template
          </Button>
          <Button onClick={() => bukaForm("baru")}>Tambah jenis ayam</Button>
        </div>
      </div>
      {daftar.isPending && <Spinner label="Memuat jenis ayam..." />}
      {daftar.isError && <ErrorState pesan={pesanGalat(daftar.error)} ulangi={() => void daftar.refetch()} />}
      {daftar.data && daftar.data.length === 0 && (
        <EmptyState judul="Belum ada jenis ayam" pesan="Salin dari template untuk mulai dengan cepat." />
      )}
      {daftar.data && daftar.data.length > 0 && (
        <ul className="space-y-2">
          {daftar.data.map((j) => (
            <li key={j.id}>
              <Card className="flex flex-wrap items-center justify-between gap-2">
                <Link to={`/master-data/jenis-ayam/${j.id}`} className="font-medium text-brand-800 hover:underline">
                  {j.nama}
                </Link>
                <div className="flex gap-2">
                  <Button varian="sekunder" onClick={() => bukaForm(j)} aria-label={`Ubah ${j.nama}`}>
                    Ubah
                  </Button>
                  <Button varian="ghost" onClick={() => { hapus.reset(); setAkanHapus(j); }} aria-label={`Hapus ${j.nama}`}>
                    Hapus
                  </Button>
                </div>
              </Card>
            </li>
          ))}
        </ul>
      )}

      <FormDialog
        judul={form === "baru" ? "Tambah jenis ayam" : "Ubah jenis ayam"}
        buka={form !== null}
        saatTutup={() => setForm(null)}
        memuat={simpan.isPending}
        galat={simpan.error}
        saatKirim={() =>
          simpan.mutate(
            { id: form && form !== "baru" ? form.id : undefined, nama: nama.trim() },
            {
              onSuccess: () => {
                setForm(null);
                tampilkan("Jenis ayam disimpan", { tipe: "sukses" });
              },
            },
          )
        }
      >
        <Field label="Nama" value={nama} onChange={(e) => setNama(e.target.value)} required />
      </FormDialog>

      <KonfirmasiHapus
        nama={akanHapus?.nama ?? null}
        saatTutup={() => setAkanHapus(null)}
        memuat={hapus.isPending}
        galat={hapus.error}
        saatHapus={() =>
          akanHapus &&
          hapus.mutate(akanHapus.id, {
            onSuccess: () => {
              setAkanHapus(null);
              tampilkan("Jenis ayam dihapus", { tipe: "sukses" });
            },
          })
        }
      />

      {template && <SalinTemplateDialog saatTutup={() => setTemplate(false)} />}
    </div>
  );
}
