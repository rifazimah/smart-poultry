import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { ProtectedRoute } from "../auth/ProtectedRoute";
import { Spinner } from "../components/ui/spinner";
import LoginPage from "../features/auth/LoginPage";
import { AppLayout } from "./AppLayout";

// Halaman dipecah per rute agar kode layar yang tidak dibuka tidak ikut diunduh.
const DashboardPage = lazy(() => import("../features/dashboard/DashboardPage"));

const KandangDetailPage = lazy(() => import("../features/kandang/KandangDetailPage"));

const memuat = (
  <div className="py-10 text-center">
    <Spinner label="Memuat halaman..." />
  </div>
);

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/masuk" element={<LoginPage />} />
      <Route
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route
          index
          element={
            <Suspense fallback={memuat}>
              <DashboardPage />
            </Suspense>
          }
        />
        <Route
          path="kandang/:id"
          element={
            <Suspense fallback={memuat}>
              <KandangDetailPage />
            </Suspense>
          }
        />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
