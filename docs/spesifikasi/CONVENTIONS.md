# Konvensi Proyek — Smart Poultry Backend

Dokumen ini berisi aturan wajib yang harus diikuti oleh seluruh kontributor
saat mengembangkan backend Smart Poultry.

---

## 1. Keamanan Kata Sandi (Password Security)

### 1.1 Nama field: `kata_sandi_hash`

Field di tabel `User` bernama **`kata_sandi_hash`**, bukan `password` atau
`hashed_password`. Ini sudah di-definisikan di `app/models/akses.py`.

### 1.2 Tidak boleh menyimpan kata sandi mentah

Kata sandi mentah (**plain text**) **TIDAK PERNAH** disimpan ke database.
Selalu hash terlebih dahulu menggunakan `passlib` dengan skema **bcrypt**
sebelum menyimpan ke kolom `kata_sandi_hash`.

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Hash kata sandi sebelum disimpan
hashed = pwd_context.hash("kata_sandi_mentah")

# Verifikasi kata sandi saat login
is_valid = pwd_context.verify("kata_sandi_mentah", user.kata_sandi_hash)
```

### 1.3 Response endpoint TIDAK boleh mengandung `kata_sandi_hash`

Setiap endpoint yang mengembalikan data `User` **WAJIB** menggunakan Pydantic
response schema terpisah (misalnya `UserPublic` / `UserRead`) yang **tidak**
menyertakan field `kata_sandi_hash`. Jangan pernah mengembalikan objek tabel
model `User` secara langsung dari endpoint.

```python
# ✅ BENAR — menggunakan response model terpisah
from pydantic import BaseModel
import uuid
from app.models.enums import PeranUser, StatusUser

class UserPublic(BaseModel):
    id: uuid.UUID
    nama: str
    email: str
    role: PeranUser
    status: StatusUser
    # TIDAK ada field kata_sandi_hash

@router.get("/users", response_model=list[UserPublic])
def list_users(...):
    ...

# ❌ SALAH — mengembalikan model tabel langsung
@router.get("/users")
def list_users(...):
    return users  # objek User dari database, mengandung kata_sandi_hash
```

### 1.4 Gunakan `CryptContext` dari passlib

Gunakan `CryptContext` dari `passlib` untuk hashing dan verifikasi.
Instansiasi cukup **satu kali** (misalnya di `app/services/auth.py` atau
modul utilitas), lalu gunakan di seluruh aplikasi.

---

## 2. Linear Programming untuk Formulasi Otomatis

### 2.1 Library: `scipy.optimize.linprog`

Endpoint formulasi otomatis **WAJIB** menggunakan `scipy.optimize.linprog`
(sudah tercantum di `requirements.txt`). **Jangan** menggunakan library LP
lain (PuLP, OR-Tools, dll.) tanpa konfirmasi terlebih dahulu dari pemilik
proyek.

### 2.2 Variabel keputusan

Variabel keputusan: **proporsi (0–1)** untuk setiap bahan pakan yang
terpasang di wadah (container) alat pada kandang tersebut.

### 2.3 Fungsi objektif

Minimisasi total biaya per kg:

```
minimize  Σ (harga_i × proporsi_i)
```

### 2.4 Batasan (constraints)

| Jenis | Rumus | Keterangan |
|---|---|---|
| **Equality** | `Σ proporsi_i = 1` | Total semua proporsi harus tepat 1 |
| **Nutrisi** | `batas_min ≤ Σ (kandungan_nutrisi_ij × proporsi_i) ≤ batas_max` | Untuk setiap nutrisi yang memiliki `batas_min` / `batas_max` di `KebutuhanNutrisiFase` |
| **Batas per bahan** | `proporsi_i ≤ batas_maksimum_i` | Jika `BahanPakan.batas_maksimum` diisi (not null), proporsi bahan tersebut tidak boleh melebihi nilainya |

```python
from scipy.optimize import linprog

# Contoh penyusunan constraint (pseudocode)
c = [harga_i for i in bahan_list]  # koefisien fungsi objektif

# Equality: sum(proporsi) = 1
A_eq = [[1, 1, ..., 1]]
b_eq = [1]

# Inequality: A_ub @ x <= b_ub
# - Nutrisi min:  -(kandungan @ x) <= -batas_min  →  nutrisi >= min
# - Nutrisi max:   (kandungan @ x) <= batas_max   →  nutrisi <= max
# - Batas per bahan: x_i <= batas_maksimum_i

bounds = [(0, batas_maksimum_i or 1) for i in bahan_list]

result = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds)
```

### 2.5 Penanganan infeasible

Jika `linprog` mengembalikan status **infeasible**, endpoint **TETAP**
mengembalikan **HTTP 200** (bukan error) dengan:

```json
{
  "mode": "OTOMATIS",
  "status": "TIDAK_SEMPURNA",
  "total_biaya_per_kg": null,
  "item": [],
  "nutrisi_hasil": [...],
  "pesan": "Formulasi tidak dapat memenuhi batas nutrisi: Protein (min 20%), Kalsium (min 3.5%)"
}
```

Ini adalah bagian dari alur normal aplikasi — **bukan** kegagalan teknis.
Jangan gunakan HTTP 4xx/5xx untuk kasus ini.

---

## 3. Struktur Kode

### 3.1 Model database bersifat final

File di `app/models/` **tidak boleh diubah** pada fase ini kecuali diminta
secara eksplisit. Gunakan model yang sudah ada apa adanya.

### 3.2 Penempatan endpoint (router)

Endpoint baru ditempatkan di:

```
app/routers/<nama_resource>.py
```

Buat folder `app/routers/` jika belum ada. Setiap router didaftarkan di
`app/main.py`:

```python
from .routers import auth, kandang, formulasi

app.include_router(auth.router, prefix="/api/v1")
app.include_router(kandang.router, prefix="/api/v1")
```

### 3.3 Pydantic request/response schema

Schema Pydantic untuk request/response (yang **bukan** model tabel)
ditempatkan di:

```
app/schemas/<nama_resource>.py
```

### 3.4 Business logic di service

Logika bisnis yang panjang (misalnya LP solver) ditempatkan di:

```
app/services/<nama>.py
```

Service dipanggil dari router — **jangan** tulis logika bisnis panjang
langsung di dalam fungsi endpoint.

```python
# ✅ BENAR
# app/routers/formulasi.py
from app.services.formulasi import hitung_formulasi_otomatis

@router.post("/siklus/{id}/formulasi/otomatis")
def formulasi_otomatis(id: uuid.UUID, ...):
    return hitung_formulasi_otomatis(session, siklus_id=id, ...)

# ❌ SALAH — logika LP langsung di endpoint
@router.post("/siklus/{id}/formulasi/otomatis")
def formulasi_otomatis(id: uuid.UUID, ...):
    # 50+ baris kode linprog di sini...
```

### 3.5 Perubahan schema database melalui Alembic

Semua perubahan schema database **WAJIB** melalui Alembic:

```bash
alembic revision --autogenerate -m "deskripsi perubahan"
alembic upgrade head
```

**Jangan pernah** menggunakan `ALTER TABLE` manual langsung ke database.

### 3.6 Ikuti API Contract

Semua endpoint, path, request/response body mengikuti definisi di
[`API_CONTRACT.md`](API_CONTRACT.md) sebagai referensi utama. Jika ada
kebutuhan yang tidak tercakup di `API_CONTRACT.md`, **tanyakan dulu** sebelum
menambahkan endpoint baru yang tidak tercantum di sana.
