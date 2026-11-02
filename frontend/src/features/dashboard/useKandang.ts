import { useQuery } from "@tanstack/react-query";
import { ambil, api, totalDariHeader, type Skema } from "../../api/client";

export type Kandang = Skema["KandangPublic"];

/** Daftar kandang milik Pemilik / yang ditugaskan ke Pekerja, plus total dari X-Total-Count. */
export function useDaftarKandang(skip = 0, limit = 20) {
  return useQuery({
    queryKey: ["kandang", { skip, limit }],
    queryFn: async () => {
      const { data, response } = await ambil(api.GET("/api/v1/kandang", { params: { query: { skip, limit } } }));
      return { items: data, total: totalDariHeader(response) };
    },
  });
}
