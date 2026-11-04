import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ambil, api, type Skema } from "../../api/client";

export type KandangInput = Skema["KandangCreate"];
export type SiklusBaru = Skema["SiklusKandangCreate"];
export type PopulasiBaru = Skema["PerubahanPopulasiCreate"];
export type Transaksi = Skema["TransaksiStokPublic"];

/** Setelah aksi tulis, data kandang/siklus/notifikasi dimuat ulang (daftar kecil, aman). */
function useSegarkan() {
  const qc = useQueryClient();
  return () =>
    Promise.all([
      qc.invalidateQueries({ queryKey: ["kandang"] }),
      qc.invalidateQueries({ queryKey: ["siklus"] }),
      qc.invalidateQueries({ queryKey: ["notifikasi"] }),
    ]);
}

// ---- Kandang (Pemilik) ----
export function useBuatKandang() {
  const segarkan = useSegarkan();
  return useMutation({
    mutationFn: async (data: KandangInput) => (await ambil(api.POST("/api/v1/kandang", { body: data }))).data,
    onSuccess: segarkan,
  });
}
export function useUbahKandang(id: string) {
  const segarkan = useSegarkan();
  return useMutation({
    mutationFn: async (data: Skema["KandangUpdate"]) =>
      (await ambil(api.PATCH("/api/v1/kandang/{id}", { params: { path: { id } }, body: data }))).data,
    onSuccess: segarkan,
  });
}
export function useHapusKandang(id: string) {
  const segarkan = useSegarkan();
  return useMutation({
    mutationFn: async () => {
      await ambil(api.DELETE("/api/v1/kandang/{id}", { params: { path: { id } } }));
    },
    onSuccess: segarkan,
  });
}

// ---- Alat dan wadah (Pemilik) ----
/** Mengembalikan alat beserta `device_token` mentah; hanya tampil sekali, jadi pemanggil wajib menampilkannya. */
export function useDaftarkanAlat(kandangId: string) {
  const segarkan = useSegarkan();
  return useMutation({
    mutationFn: async () =>
      (await ambil(api.POST("/api/v1/kandang/{id}/alat", { params: { path: { id: kandangId } } }))).data,
    onSuccess: segarkan,
  });
}
export function useRotasiToken() {
  return useMutation({
    mutationFn: async (alatId: string) =>
      (await ambil(api.POST("/api/v1/alat/{id}/rotasi-token", { params: { path: { id: alatId } } }))).data,
  });
}
export function useHapusAlat() {
  const segarkan = useSegarkan();
  return useMutation({
    mutationFn: async (alatId: string) => {
      await ambil(api.DELETE("/api/v1/alat/{id}", { params: { path: { id: alatId } } }));
    },
    onSuccess: segarkan,
  });
}
export function useTambahWadah(alatId: string) {
  const segarkan = useSegarkan();
  return useMutation({
    mutationFn: async (data: { nomor_wadah: number; bahan_pakan_id: string | null }) =>
      (await ambil(api.POST("/api/v1/alat/{id}/wadah", { params: { path: { id: alatId } }, body: data }))).data,
    onSuccess: segarkan,
  });
}
export function useUbahBahanWadah() {
  const segarkan = useSegarkan();
  return useMutation({
    mutationFn: async (v: { wadahId: string; bahanId: string | null }) =>
      (
        await ambil(
          api.PATCH("/api/v1/wadah/{id}", { params: { path: { id: v.wadahId } }, body: { bahan_pakan_id: v.bahanId } }),
        )
      ).data,
    onSuccess: segarkan,
  });
}
export function useHapusWadah() {
  const segarkan = useSegarkan();
  return useMutation({
    mutationFn: async (wadahId: string) => {
      await ambil(api.DELETE("/api/v1/wadah/{id}", { params: { path: { id: wadahId } } }));
    },
    onSuccess: segarkan,
  });
}

// ---- Siklus dan populasi ----
export function useMulaiSiklus(kandangId: string) {
  const segarkan = useSegarkan();
  return useMutation({
    mutationFn: async (data: SiklusBaru) =>
      (await ambil(api.POST("/api/v1/kandang/{id}/siklus", { params: { path: { id: kandangId } }, body: data }))).data,
    onSuccess: segarkan,
  });
}
export function useGantiFase() {
  const segarkan = useSegarkan();
  return useMutation({
    mutationFn: async (v: { siklusId: string; faseId: string }) =>
      (
        await ambil(
          api.PATCH("/api/v1/siklus/{id}/fase", { params: { path: { id: v.siklusId } }, body: { fase_id: v.faseId } }),
        )
      ).data,
    onSuccess: segarkan,
  });
}
export function useSelesaiSiklus() {
  const segarkan = useSegarkan();
  return useMutation({
    mutationFn: async (siklusId: string) =>
      (await ambil(api.POST("/api/v1/siklus/{id}/selesai", { params: { path: { id: siklusId } } }))).data,
    onSuccess: segarkan,
  });
}
export function useKoreksiSiklus() {
  const segarkan = useSegarkan();
  return useMutation({
    mutationFn: async (v: { siklusId: string; data: Skema["SiklusKandangUpdate"] }) =>
      (await ambil(api.PATCH("/api/v1/siklus/{id}", { params: { path: { id: v.siklusId } }, body: v.data }))).data,
    onSuccess: segarkan,
  });
}
export function useHapusSiklus() {
  const segarkan = useSegarkan();
  return useMutation({
    mutationFn: async (siklusId: string) => {
      await ambil(api.DELETE("/api/v1/siklus/{id}", { params: { path: { id: siklusId } } }));
    },
    onSuccess: segarkan,
  });
}
export function useCatatPopulasi() {
  const segarkan = useSegarkan();
  return useMutation({
    mutationFn: async (v: { siklusId: string; data: PopulasiBaru }) =>
      (await ambil(api.POST("/api/v1/siklus/{id}/populasi", { params: { path: { id: v.siklusId } }, body: v.data })))
        .data,
    onSuccess: segarkan,
  });
}
export function useHapusPopulasi() {
  const segarkan = useSegarkan();
  return useMutation({
    mutationFn: async (v: { siklusId: string; populasiId: string }) => {
      await ambil(
        api.DELETE("/api/v1/siklus/{id}/populasi/{populasi_id}", {
          params: { path: { id: v.siklusId, populasi_id: v.populasiId } },
        }),
      );
    },
    onSuccess: segarkan,
  });
}

// ---- Stok ----
export function useIsiUlang() {
  const segarkan = useSegarkan();
  return useMutation({
    mutationFn: async (v: { wadahId: string; gram: number }) =>
      (
        await ambil(
          api.POST("/api/v1/wadah/{id}/stok/isi-ulang", {
            params: { path: { id: v.wadahId } },
            body: { jumlah: v.gram },
          }),
        )
      ).data,
    onSuccess: segarkan,
  });
}
export function useKoreksiStok() {
  const segarkan = useSegarkan();
  return useMutation({
    mutationFn: async (v: { wadahId: string; gramBaru: number; alasan: string }) =>
      (
        await ambil(
          api.POST("/api/v1/wadah/{id}/stok/koreksi", {
            params: { path: { id: v.wadahId } },
            body: { jumlah_baru: v.gramBaru, alasan: v.alasan },
          }),
        )
      ).data,
    onSuccess: segarkan,
  });
}
export function useRiwayatStok(wadahId: string | null) {
  return useQuery({
    queryKey: ["kandang", "stok-transaksi", wadahId],
    enabled: !!wadahId,
    queryFn: async () =>
      (
        await ambil(
          api.GET("/api/v1/wadah/{id}/stok/transaksi", {
            params: { path: { id: wadahId! }, query: { skip: 0, limit: 20 } },
          }),
        )
      ).data,
  });
}
