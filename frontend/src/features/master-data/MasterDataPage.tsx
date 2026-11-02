import { useState } from "react";
import { BahanTab } from "./BahanTab";
import { JenisAyamTab } from "./JenisAyamTab";
import { NutrisiTab } from "./NutrisiTab";

const TAB = [
  { id: "jenis-ayam", label: "Jenis ayam", isi: <JenisAyamTab /> },
  { id: "bahan", label: "Bahan pakan", isi: <BahanTab /> },
  { id: "nutrisi", label: "Nutrisi", isi: <NutrisiTab /> },
] as const;

export default function MasterDataPage() {
  const [aktif, setAktif] = useState<(typeof TAB)[number]["id"]>("jenis-ayam");
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-stone-900 sm:text-2xl">Master data</h1>
      <div role="tablist" aria-label="Master data" className="flex gap-1 border-b border-stone-200">
        {TAB.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            id={`tab-${t.id}`}
            aria-selected={aktif === t.id}
            aria-controls={`panel-${t.id}`}
            onClick={() => setAktif(t.id)}
            className={`min-h-11 border-b-2 px-4 text-sm font-medium ${
              aktif === t.id ? "border-brand-700 text-brand-800" : "border-transparent text-stone-600 hover:text-stone-900"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
      {TAB.map(
        (t) =>
          aktif === t.id && (
            <div key={t.id} role="tabpanel" id={`panel-${t.id}`} aria-labelledby={`tab-${t.id}`}>
              {t.isi}
            </div>
          ),
      )}
    </div>
  );
}
