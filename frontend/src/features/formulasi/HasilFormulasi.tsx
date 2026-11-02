import { Badge, type NadaBadge } from "../../components/ui/badge";
import { Card } from "../../components/ui/card";
import { formatAngka, formatBerat, formatProporsi, formatRupiah } from "../../lib/format";
import type { Skema } from "../../api/client";

type Status = Skema["StatusFormulasi"];
type StatusNutrisi = Skema["StatusNutrisi"];

const NADA_STATUS: Record<Status, NadaBadge> = { VALID: "baik", TIDAK_SEMPURNA: "peringatan", PERLU_DITINJAU: "peringatan" };
const LABEL_STATUS: Record<Status, string> = {
  VALID: "Valid",
  TIDAK_SEMPURNA: "Tidak sempurna",
  PERLU_DITINJAU: "Perlu ditinjau",
};
const NADA_NUTRISI: Record<StatusNutrisi, NadaBadge> = { SESUAI: "baik", KURANG: "bahaya", BERLEBIH: "peringatan" };
const LABEL_NUTRISI: Record<StatusNutrisi, string> = { SESUAI: "Sesuai", KURANG: "Kurang", BERLEBIH: "Berlebih" };

export interface DataHasil {
  mode: Skema["ModeFormulasi"];
  status: Status;
  pesan?: string | null;
  total_biaya_per_kg?: number | null;
  item: Array<{ bahan_pakan_id: string; nama_bahan?: string | null; proporsi: number; berat_per_sesi: number }>;
  nutrisi_hasil: Array<{
    nutrisi_id: string;
    nama_nutrisi?: string | null;
    nilai_hasil: number;
    batas_min?: number | null;
    batas_max?: number | null;
    keterangan?: string | null;
    status: StatusNutrisi;
  }>;
}

function rentang(min?: number | null, max?: number | null): string {
  if (min != null && max != null) return `${formatAngka(min)} – ${formatAngka(max)}`;
  if (min != null) return `≥ ${formatAngka(min)}`;
  if (max != null) return `≤ ${formatAngka(max)}`;
  return "-";
}

/** Tampilan resep, evaluasi nutrisi, dan diagnosis; dipakai untuk preview maupun formulasi tersimpan. */
export function HasilFormulasi({ data }: { data: DataHasil }) {
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge nada={NADA_STATUS[data.status]}>{LABEL_STATUS[data.status]}</Badge>
        <Badge>{data.mode === "OTOMATIS" ? "Otomatis" : "Manual"}</Badge>
        <span className="text-sm text-stone-500">Biaya per kg: {formatRupiah(data.total_biaya_per_kg)}</span>
      </div>

      {data.pesan && (
        <div role="status" className="rounded-xl border border-accent-400 bg-accent-100 p-4 text-sm text-stone-800">
          <p className="mb-1 font-semibold">Catatan sistem</p>
          <p>{data.pesan}</p>
        </div>
      )}

      <section className="space-y-2">
        <h3 className="font-semibold text-stone-900">Resep</h3>
        {data.item.length === 0 ? (
          <p className="text-sm text-stone-500">Tidak ada komposisi yang dihasilkan.</p>
        ) : (
          <Card className="overflow-x-auto p-0">
            <table className="w-full text-left text-sm">
              <thead className="bg-stone-50 text-xs text-stone-500">
                <tr>
                  <th className="px-4 py-2 font-medium">Bahan</th>
                  <th className="px-4 py-2 text-right font-medium">Proporsi</th>
                  <th className="px-4 py-2 text-right font-medium">Per sesi</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-100">
                {data.item.map((i) => (
                  <tr key={i.bahan_pakan_id}>
                    <td className="px-4 py-2">{i.nama_bahan ?? "-"}</td>
                    <td className="px-4 py-2 text-right">{formatProporsi(i.proporsi)}</td>
                    <td className="px-4 py-2 text-right">{formatBerat(i.berat_per_sesi)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        )}
      </section>

      {data.nutrisi_hasil.length > 0 && (
        <section className="space-y-2">
          <h3 className="font-semibold text-stone-900">Evaluasi nutrisi</h3>
          <Card className="overflow-x-auto p-0">
            <table className="w-full text-left text-sm">
              <thead className="bg-stone-50 text-xs text-stone-500">
                <tr>
                  <th className="px-4 py-2 font-medium">Nutrisi</th>
                  <th className="px-4 py-2 text-right font-medium">Hasil</th>
                  <th className="px-4 py-2 text-right font-medium">Batas</th>
                  <th className="px-4 py-2 font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-100">
                {data.nutrisi_hasil.map((n) => (
                  <tr key={n.nutrisi_id} className="align-top">
                    <td className="px-4 py-2">
                      {n.nama_nutrisi ?? "-"}
                      {n.keterangan && <p className="mt-1 max-w-sm text-xs text-stone-500">{n.keterangan}</p>}
                    </td>
                    <td className="px-4 py-2 text-right">{formatAngka(n.nilai_hasil)}</td>
                    <td className="px-4 py-2 text-right">{rentang(n.batas_min, n.batas_max)}</td>
                    <td className="px-4 py-2">
                      <Badge nada={NADA_NUTRISI[n.status]}>{LABEL_NUTRISI[n.status]}</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </section>
      )}
    </div>
  );
}
