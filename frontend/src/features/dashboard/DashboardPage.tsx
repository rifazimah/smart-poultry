import { Warehouse } from "lucide-react";
import { pesanGalat } from "../../api/errors";
import { useAuth } from "../../auth/auth-context";
import { Badge } from "../../components/ui/badge";
import { Card } from "../../components/ui/card";
import { Spinner } from "../../components/ui/spinner";
import { EmptyState, ErrorState } from "../../components/ui/states";
import { useDaftarKandang, type Kandang } from "./useKandang";

function KartuKandang({ kandang }: { kandang: Kandang }) {
  return (
    <Card className="flex items-start gap-3">
      <Warehouse className="mt-0.5 h-6 w-6 shrink-0 text-brand-700" aria-hidden="true" />
      <div className="min-w-0 flex-1">
        <h3 className="truncate font-semibold text-stone-900">{kandang.nama}</h3>
        <p className="truncate text-sm text-stone-500">{kandang.lokasi || "Lokasi belum diisi"}</p>
      </div>
      <Badge nada={kandang.status === "AKTIF" ? "baik" : "netral"}>{kandang.status === "AKTIF" ? "Aktif" : "Nonaktif"}</Badge>
    </Card>
  );
}

export default function DashboardPage() {
  const { pengguna } = useAuth();
  const { data, isPending, isError, error, refetch } = useDaftarKandang();

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-stone-900 sm:text-2xl">Halo, {pengguna?.nama}</h1>
        <p className="text-sm text-stone-500">Ringkasan kandang Anda.</p>
      </div>

      {isPending && (
        <div className="py-10 text-center">
          <Spinner label="Memuat kandang..." />
        </div>
      )}
      {isError && <ErrorState pesan={pesanGalat(error)} ulangi={() => void refetch()} />}
      {data && data.items.length === 0 && (
        <EmptyState
          judul="Belum ada kandang"
          pesan={
            pengguna?.role === "PEMILIK"
              ? "Kandang akan tampil di sini setelah dibuat."
              : "Anda belum ditugaskan ke kandang mana pun. Hubungi Pemilik."
          }
        />
      )}
      {data && data.items.length > 0 && (
        <>
          <p className="text-sm text-stone-500">{data.total} kandang</p>
          <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {data.items.map((k) => (
              <li key={k.id}>
                <KartuKandang kandang={k} />
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
