import * as RadixDialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import type { ReactNode } from "react";

interface Props {
  buka: boolean;
  saatBerubah: (buka: boolean) => void;
  judul: string;
  deskripsi?: string;
  children: ReactNode;
  /** "tengah" = modal biasa; "kiri" = laci navigasi di ponsel. */
  posisi?: "tengah" | "kiri";
}

/** Modal aksesibel (focus trap, Esc, aria) di atas Radix. */
export function Dialog({ buka, saatBerubah, judul, deskripsi, children, posisi = "tengah" }: Props) {
  return (
    <RadixDialog.Root open={buka} onOpenChange={saatBerubah}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay className="fixed inset-0 z-40 bg-stone-900/40" />
        <RadixDialog.Content
          className={
            posisi === "kiri"
              ? "fixed inset-y-0 left-0 z-50 w-72 max-w-[85vw] overflow-y-auto bg-white p-4 shadow-xl"
              : "fixed top-1/2 left-1/2 z-50 w-[calc(100vw-2rem)] max-w-lg -translate-x-1/2 -translate-y-1/2 rounded-xl bg-white p-5 shadow-xl"
          }
        >
          <div className="mb-3 flex items-start justify-between gap-3">
            <RadixDialog.Title className="text-base font-semibold text-stone-900">{judul}</RadixDialog.Title>
            <RadixDialog.Close className="rounded-md p-1 text-stone-500 hover:bg-stone-100" aria-label="Tutup">
              <X className="h-5 w-5" aria-hidden="true" />
            </RadixDialog.Close>
          </div>
          {deskripsi ? (
            <RadixDialog.Description className="mb-3 text-sm text-stone-500">{deskripsi}</RadixDialog.Description>
          ) : (
            <RadixDialog.Description className="sr-only">{judul}</RadixDialog.Description>
          )}
          {children}
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
}
