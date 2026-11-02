import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { ambil, api, aturPenangananSesiBerakhir } from "../api/client";
import { useToast } from "../components/ui/toast";
import { AuthContext, type Pengguna, type StatusAuth } from "./auth-context";
import { ambilToken, hapusToken, simpanToken } from "./token";

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const { tampilkan } = useToast();
  const [pengguna, setPengguna] = useState<Pengguna | null>(null);
  const [status, setStatus] = useState<StatusAuth>(() => (ambilToken() ? "memuat" : "keluar"));

  const bersihkanSesi = useCallback(() => {
    hapusToken();
    setPengguna(null);
    setStatus("keluar");
    queryClient.clear(); // data milik pengguna sebelumnya tidak boleh terlihat oleh pengguna berikutnya
  }, [queryClient]);

  // Server membalas 401 pada request terautentikasi: sesi berakhir.
  useEffect(() => {
    aturPenangananSesiBerakhir(() => {
      if (ambilToken()) tampilkan("Sesi berakhir", { pesan: "Silakan masuk kembali.", tipe: "info" });
      bersihkanSesi();
    });
    return () => aturPenangananSesiBerakhir(null);
  }, [bersihkanSesi, tampilkan]);

  // Pulihkan sesi dari token tersimpan.
  useEffect(() => {
    if (!ambilToken()) return;
    let batal = false;
    ambil(api.GET("/api/v1/auth/me"))
      .then(({ data }) => {
        if (batal) return;
        setPengguna(data);
        setStatus("masuk");
      })
      .catch(() => {
        // 401 sudah ditangani middleware; galat lain (server mati) -> anggap belum masuk tanpa menghapus token
        if (!batal) setStatus("keluar");
      });
    return () => {
      batal = true;
    };
  }, []);

  const masuk = useCallback(
    async (email: string, kataSandi: string) => {
      const { data } = await ambil(api.POST("/api/v1/auth/login", { body: { email, kata_sandi: kataSandi } }));
      simpanToken(data.access_token);
      setPengguna(data.user);
      setStatus("masuk");
    },
    [],
  );

  const nilai = useMemo(() => ({ pengguna, status, masuk, keluar: bersihkanSesi }), [pengguna, status, masuk, bersihkanSesi]);
  return <AuthContext.Provider value={nilai}>{children}</AuthContext.Provider>;
}
