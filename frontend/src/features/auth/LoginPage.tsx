import { Eye, EyeOff } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { pesanGalat } from "../../api/errors";
import { useAuth } from "../../auth/auth-context";
import { Button } from "../../components/ui/button";
import { Card } from "../../components/ui/card";
import { Field } from "../../components/ui/field";

export default function LoginPage() {
  const { masuk, status } = useAuth();
  const navigate = useNavigate();
  const lokasi = useLocation();
  const tujuan = (lokasi.state as { dari?: string } | null)?.dari ?? "/";

  const [email, setEmail] = useState("");
  const [kataSandi, setKataSandi] = useState("");
  const [tampilkan, setTampilkan] = useState(false);
  const [galat, setGalat] = useState<string | null>(null);
  const [memproses, setMemproses] = useState(false);

  if (status === "masuk") return <Navigate to={tujuan} replace />;

  async function kirim(e: FormEvent) {
    e.preventDefault();
    setGalat(null);
    setMemproses(true);
    try {
      await masuk(email.trim(), kataSandi);
      navigate(tujuan, { replace: true });
    } catch (err) {
      setGalat(pesanGalat(err));
    } finally {
      setMemproses(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-brand-50 p-4">
      <Card className="w-full max-w-sm space-y-5 p-6">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-brand-800">Smart Poultry</h1>
          <p className="mt-1 text-sm text-stone-500">Masuk untuk mengelola kandang dan pakan.</p>
        </div>

        <form onSubmit={kirim} className="space-y-4" noValidate>
          {galat && (
            <p role="alert" className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
              {galat}
            </p>
          )}
          <Field
            label="Email"
            type="email"
            autoComplete="username"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <div className="relative">
            <Field
              label="Kata sandi"
              type={tampilkan ? "text" : "password"}
              autoComplete="current-password"
              value={kataSandi}
              onChange={(e) => setKataSandi(e.target.value)}
              className="pr-11"
              required
            />
            <button
              type="button"
              onClick={() => setTampilkan((v) => !v)}
              aria-label={tampilkan ? "Sembunyikan kata sandi" : "Tampilkan kata sandi"}
              className="absolute right-2 bottom-1 rounded-md p-1.5 text-stone-500 hover:bg-stone-100"
            >
              {tampilkan ? <EyeOff className="h-5 w-5" aria-hidden="true" /> : <Eye className="h-5 w-5" aria-hidden="true" />}
            </button>
          </div>
          <Button type="submit" className="w-full" memuat={memproses} disabled={!email || !kataSandi}>
            Masuk
          </Button>
        </form>
      </Card>
    </div>
  );
}
