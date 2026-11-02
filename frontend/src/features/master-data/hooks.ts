import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ambil, api, type Skema } from "../../api/client";

export type Nutrisi = Skema["NutrisiPublic"];
export type NutrisiInput = Skema["NutrisiCreate"];
export type TipeBatas = Skema["TipeBatas"];
export type Bahan = Skema["BahanPakanPublic"];
export type BahanInput = Skema["BahanPakanUpdate"];
export type Kandungan = Skema["KandunganNutrisiBahanDetail"];
export type JenisAyam = Skema["JenisAyamPublic"];
export type Fase = Skema["FasePublic"];
export type FaseInput = Skema["FaseCreate"];
export type Kebutuhan = Skema["KebutuhanNutrisiFaseDetail"];
export type KebutuhanInput = Skema["KebutuhanNutrisiFaseInput"];
export type StandarInput = Skema["StandarKonsumsiCreateUpdate"];
export type Template = Skema["TemplateJenisAyam"];

const BATAS = { skip: 0, limit: 100 };

/** Setelah mutasi master data, semua query master data dimuat ulang (daftar kecil, aman). */
function useSegarkan() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: ["md"] });
}

// ---- Nutrisi ----
export function useDaftarNutrisi() {
  return useQuery({
    queryKey: ["md", "nutrisi"],
    queryFn: async () => (await ambil(api.GET("/api/v1/nutrisi", { params: { query: BATAS } }))).data,
  });
}
export function useSimpanNutrisi() {
  const segarkan = useSegarkan();
  return useMutation({
    mutationFn: async (v: { id?: string; data: NutrisiInput }) =>
      v.id
        ? (await ambil(api.PATCH("/api/v1/nutrisi/{id}", { params: { path: { id: v.id } }, body: v.data }))).data
        : (await ambil(api.POST("/api/v1/nutrisi", { body: v.data }))).data,
    onSuccess: segarkan,
  });
}
export function useHapusNutrisi() {
  const segarkan = useSegarkan();
  return useMutation({
    mutationFn: async (id: string) => {
      await ambil(api.DELETE("/api/v1/nutrisi/{id}", { params: { path: { id } } }));
    },
    onSuccess: segarkan,
  });
}

// ---- Bahan pakan ----
export function useDaftarBahan() {
  return useQuery({
    queryKey: ["md", "bahan"],
    queryFn: async () => (await ambil(api.GET("/api/v1/bahan-pakan", { params: { query: BATAS } }))).data,
  });
}
export function useSimpanBahan() {
  const segarkan = useSegarkan();
  return useMutation({
    mutationFn: async (v: { id?: string; data: BahanInput & { nama: string } }) =>
      v.id
        ? (await ambil(api.PATCH("/api/v1/bahan-pakan/{id}", { params: { path: { id: v.id } }, body: v.data }))).data
        : (await ambil(api.POST("/api/v1/bahan-pakan", { body: v.data }))).data,
    onSuccess: segarkan,
  });
}
export function useHapusBahan() {
  const segarkan = useSegarkan();
  return useMutation({
    mutationFn: async (id: string) => {
      await ambil(api.DELETE("/api/v1/bahan-pakan/{id}", { params: { path: { id } } }));
    },
    onSuccess: segarkan,
  });
}
export function useKandunganBahan(id: string | null) {
  return useQuery({
    queryKey: ["md", "bahan", id, "kandungan"],
    enabled: !!id,
    queryFn: async () =>
      (await ambil(api.GET("/api/v1/bahan-pakan/{id}/nutrisi", { params: { path: { id: id! } } }))).data,
  });
}
export function useSimpanKandungan(id: string) {
  const segarkan = useSegarkan();
  return useMutation({
    mutationFn: async (nilai: { nutrisi_id: string; nilai_per_kg: number }[]) =>
      (await ambil(api.PUT("/api/v1/bahan-pakan/{id}/nutrisi", { params: { path: { id } }, body: nilai }))).data,
    onSuccess: segarkan,
  });
}

// ---- Jenis ayam, fase, template ----
export function useDaftarJenisAyam() {
  return useQuery({
    queryKey: ["md", "jenis-ayam"],
    queryFn: async () => (await ambil(api.GET("/api/v1/jenis-ayam", { params: { query: BATAS } }))).data,
  });
}
export function useJenisAyam(id: string) {
  return useQuery({
    queryKey: ["md", "jenis-ayam", id],
    queryFn: async () => (await ambil(api.GET("/api/v1/jenis-ayam/{id}", { params: { path: { id } } }))).data,
  });
}
export function useSimpanJenisAyam() {
  const segarkan = useSegarkan();
  return useMutation({
    mutationFn: async (v: { id?: string; nama: string }) =>
      v.id
        ? (await ambil(api.PATCH("/api/v1/jenis-ayam/{id}", { params: { path: { id: v.id } }, body: { nama: v.nama } })))
            .data
        : (await ambil(api.POST("/api/v1/jenis-ayam", { body: { nama: v.nama } }))).data,
    onSuccess: segarkan,
  });
}
export function useHapusJenisAyam() {
  const segarkan = useSegarkan();
  return useMutation({
    mutationFn: async (id: string) => {
      await ambil(api.DELETE("/api/v1/jenis-ayam/{id}", { params: { path: { id } } }));
    },
    onSuccess: segarkan,
  });
}
export function useDaftarTemplate(aktif: boolean) {
  return useQuery({
    queryKey: ["md", "template"],
    enabled: aktif,
    queryFn: async () => (await ambil(api.GET("/api/v1/template/jenis-ayam"))).data,
  });
}
export function useSalinTemplate() {
  const segarkan = useSegarkan();
  return useMutation({
    mutationFn: async (v: { templateId: string; nama?: string }) =>
      (
        await ambil(
          api.POST("/api/v1/template/jenis-ayam/{template_id}/salin", {
            params: { path: { template_id: v.templateId } },
            body: { nama: v.nama || null },
          }),
        )
      ).data,
    onSuccess: segarkan,
  });
}

export function useDaftarFase(jenisId: string) {
  return useQuery({
    queryKey: ["md", "jenis-ayam", jenisId, "fase"],
    queryFn: async () =>
      (await ambil(api.GET("/api/v1/jenis-ayam/{id}/fase", { params: { path: { id: jenisId }, query: BATAS } }))).data,
  });
}
export function useSimpanFase(jenisId: string) {
  const segarkan = useSegarkan();
  return useMutation({
    mutationFn: async (v: { id?: string; data: FaseInput }) =>
      v.id
        ? (await ambil(api.PATCH("/api/v1/fase/{id}", { params: { path: { id: v.id } }, body: v.data }))).data
        : (await ambil(api.POST("/api/v1/jenis-ayam/{id}/fase", { params: { path: { id: jenisId } }, body: v.data })))
            .data,
    onSuccess: segarkan,
  });
}
export function useHapusFase() {
  const segarkan = useSegarkan();
  return useMutation({
    mutationFn: async (id: string) => {
      await ambil(api.DELETE("/api/v1/fase/{id}", { params: { path: { id } } }));
    },
    onSuccess: segarkan,
  });
}

export function useKebutuhanFase(faseId: string | null) {
  return useQuery({
    queryKey: ["md", "fase", faseId, "kebutuhan"],
    enabled: !!faseId,
    queryFn: async () =>
      (await ambil(api.GET("/api/v1/fase/{id}/kebutuhan-nutrisi", { params: { path: { id: faseId! } } }))).data,
  });
}
export function useSimpanKebutuhan(faseId: string) {
  const segarkan = useSegarkan();
  return useMutation({
    mutationFn: async (baris: KebutuhanInput[]) =>
      (await ambil(api.PUT("/api/v1/fase/{id}/kebutuhan-nutrisi", { params: { path: { id: faseId } }, body: baris })))
        .data,
    onSuccess: segarkan,
  });
}
export function useStandarFase(faseId: string | null) {
  return useQuery({
    queryKey: ["md", "fase", faseId, "standar"],
    enabled: !!faseId,
    queryFn: async () =>
      (await ambil(api.GET("/api/v1/fase/{id}/standar-konsumsi", { params: { path: { id: faseId! } } }))).data ?? null,
  });
}
export function useSimpanStandar(faseId: string) {
  const segarkan = useSegarkan();
  return useMutation({
    mutationFn: async (data: StandarInput) =>
      (await ambil(api.PUT("/api/v1/fase/{id}/standar-konsumsi", { params: { path: { id: faseId } }, body: data })))
        .data,
    onSuccess: segarkan,
  });
}
