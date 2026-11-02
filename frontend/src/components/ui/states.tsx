import { AlertTriangle, Inbox } from "lucide-react";
import type { ReactNode } from "react";
import { Button } from "./button";

export function EmptyState({ judul, pesan, aksi }: { judul: string; pesan?: string; aksi?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-stone-300 bg-white px-6 py-10 text-center">
      <Inbox className="h-8 w-8 text-stone-400" aria-hidden="true" />
      <p className="font-semibold text-stone-800">{judul}</p>
      {pesan && <p className="max-w-md text-sm text-stone-500">{pesan}</p>}
      {aksi}
    </div>
  );
}

export function ErrorState({ pesan, ulangi }: { pesan: string; ulangi?: () => void }) {
  return (
    <div role="alert" className="flex flex-col items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-6 py-8 text-center">
      <AlertTriangle className="h-8 w-8 text-red-500" aria-hidden="true" />
      <p className="max-w-md text-sm text-red-800">{pesan}</p>
      {ulangi && (
        <Button varian="sekunder" onClick={ulangi}>
          Coba lagi
        </Button>
      )}
    </div>
  );
}
