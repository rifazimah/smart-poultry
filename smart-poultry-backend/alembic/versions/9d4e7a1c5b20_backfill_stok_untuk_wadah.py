"""backfill stok untuk wadah

Revision ID: 9d4e7a1c5b20
Revises: 3c390b676f31
Create Date: 2026-11-01 20:00:00.000000

Migrasi data (tanpa perubahan skema): setiap Wadah harus punya satu baris Stok.
"""
from alembic import op


revision = '9d4e7a1c5b20'
down_revision = '3c390b676f31'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO stok (id, wadah_id, jumlah_estimasi)
        SELECT gen_random_uuid(), w.id, 0
        FROM wadah w
        WHERE NOT EXISTS (SELECT 1 FROM stok s WHERE s.wadah_id = w.id)
        """
    )


def downgrade() -> None:
    # Data tidak dikembalikan: baris stok bernilai 0 aman dibiarkan.
    pass
