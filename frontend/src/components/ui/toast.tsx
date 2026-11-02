import * as Toast from "@radix-ui/react-toast";
import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from "react";

type Tipe = "info" | "sukses" | "galat";
interface Item {
  id: number;
  judul: string;
  pesan?: string;
  tipe: Tipe;
}

interface ToastApi {
  tampilkan: (judul: string, opsi?: { pesan?: string; tipe?: Tipe }) => void;
}

const ToastContext = createContext<ToastApi | null>(null);

const warna: Record<Tipe, string> = {
  info: "border-stone-300",
  sukses: "border-brand-600",
  galat: "border-red-600",
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<Item[]>([]);
  const urutan = useRef(0);

  const tampilkan = useCallback<ToastApi["tampilkan"]>((judul, opsi) => {
    urutan.current += 1;
    const item: Item = { id: urutan.current, judul, pesan: opsi?.pesan, tipe: opsi?.tipe ?? "info" };
    setItems((lama) => [...lama, item]);
  }, []);

  const nilai = useMemo(() => ({ tampilkan }), [tampilkan]);

  return (
    <ToastContext.Provider value={nilai}>
      <Toast.Provider swipeDirection="right" duration={5000}>
        {children}
        {items.map((it) => (
          <Toast.Root
            key={it.id}
            onOpenChange={(buka) => !buka && setItems((lama) => lama.filter((x) => x.id !== it.id))}
            className={`rounded-lg border-l-4 bg-white p-3 shadow-lg ${warna[it.tipe]}`}
          >
            <Toast.Title className="text-sm font-semibold text-stone-900">{it.judul}</Toast.Title>
            {it.pesan && <Toast.Description className="mt-0.5 text-sm text-stone-600">{it.pesan}</Toast.Description>}
          </Toast.Root>
        ))}
        <Toast.Viewport className="fixed right-4 bottom-4 z-[100] flex w-80 max-w-[calc(100vw-2rem)] flex-col gap-2 outline-none" />
      </Toast.Provider>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastApi {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast harus dipakai di dalam <ToastProvider>");
  return ctx;
}
