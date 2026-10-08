import uuid
from sqlmodel import Session, select
from app.models.fisik import Alat, Wadah, Stok, TransaksiStok
from app.models.operasional import Perintah, LogEksekusi, FormulasiItem, Notifikasi
from app.models.enums import StatusPerintah, JenisTransaksi, StatusNotifikasi, JenisNotifikasi
from app.schemas.perintah import DeviceLogRequest

def proses_log_eksekusi(
    session: Session,
    alat: Alat,
    perintah: Perintah,
    req: DeviceLogRequest
) -> LogEksekusi:
    # Idempotency check
    existing_log = session.exec(
        select(LogEksekusi).where(LogEksekusi.id_eksekusi_unik == req.id_eksekusi_unik)
    ).first()
    
    if existing_log:
        return existing_log
        
    log = LogEksekusi(
        perintah_id=perintah.id,
        id_eksekusi_unik=req.id_eksekusi_unik,
        berat_aktual=req.berat_aktual,
        status=req.status
    )
    session.add(log)
    
    # Update status perintah
    if req.status.value == "SUKSES":
        perintah.status = StatusPerintah.SUKSES
        
        # Kurangi stok wadah berdasarkan formulasi (jika ini perintah beri makan)
        if perintah.formulasi_id:
            items = session.exec(
                select(FormulasiItem).where(FormulasiItem.formulasi_id == perintah.formulasi_id)
            ).all()
            
            for item in items:
                # Cari wadah di alat ini yang memuat bahan pakan tersebut
                wadah = session.exec(
                    select(Wadah).where(
                        Wadah.alat_id == alat.id,
                        Wadah.bahan_pakan_id == item.bahan_pakan_id
                    )
                ).first()
                
                if wadah:
                    stok = session.exec(select(Stok).where(Stok.wadah_id == wadah.id)).first()
                    if stok:
                        stok.jumlah_estimasi -= item.berat_per_sesi
                        if stok.jumlah_estimasi < 0:
                            stok.jumlah_estimasi = 0
                        session.add(stok)
                        
                        # Catat transaksi
                        tx = TransaksiStok(
                            wadah_id=wadah.id,
                            dilakukan_oleh_id=perintah.dibuat_oleh_id,
                            jenis=JenisTransaksi.PENGELUARAN,
                            jumlah=item.berat_per_sesi,
                            alasan="Pengeluaran otomatis untuk perintah pakan"
                        )
                        session.add(tx)
    else:
        perintah.status = StatusPerintah.GAGAL
        
    session.add(perintah)
    
    # Buat notifikasi
    notif = Notifikasi(
        user_id=perintah.dibuat_oleh_id,
        jenis=JenisNotifikasi.SISTEM if req.status.value == "SUKSES" else JenisNotifikasi.ALARM,
        judul="Eksekusi Perintah Selesai" if req.status.value == "SUKSES" else "Perintah Gagal",
        pesan=f"Perintah {perintah.tipe.value} telah {req.status.value}.",
        status=StatusNotifikasi.BELUM_DIBACA
    )
    session.add(notif)
    
    session.commit()
    session.refresh(log)
    
    return log
