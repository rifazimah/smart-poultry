import { Loader2 } from "lucide-react";

export function Spinner({ label }: { label?: string }) {
  return (
    <span role="status" className="inline-flex items-center gap-2 text-sm text-stone-500">
      <Loader2 className="h-5 w-5 animate-spin text-brand-600" aria-hidden="true" />
      {label ?? <span className="sr-only">Memuat</span>}
    </span>
  );
}
