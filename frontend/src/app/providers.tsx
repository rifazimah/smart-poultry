import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { layakDiulang } from "../api/errors";
import { AuthProvider } from "../auth/AuthProvider";
import { ToastProvider } from "../components/ui/toast";

export function buatQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: (kali, err) => layakDiulang(err) && kali < 2,
        refetchOnWindowFocus: false, // hemat request; polling dipasang eksplisit di tempat yang membutuhkannya
        staleTime: 10_000,
      },
    },
  });
}

export function AppProviders({ children, client: klienLuar }: { children: ReactNode; client?: QueryClient }) {
  const [klienDalam] = useState(buatQueryClient);
  return (
    <QueryClientProvider client={klienLuar ?? klienDalam}>
      <ToastProvider>
        <AuthProvider>{children}</AuthProvider>
      </ToastProvider>
    </QueryClientProvider>
  );
}
