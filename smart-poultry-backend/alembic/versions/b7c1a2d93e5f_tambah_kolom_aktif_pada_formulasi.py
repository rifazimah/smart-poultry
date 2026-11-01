"""tambah kolom aktif pada formulasi

Revision ID: b7c1a2d93e5f
Revises: 903f737d4420
Create Date: 2026-11-01 15:00:00.000000

Ditulis manual (DB tidak tersedia saat dibuat); setara hasil --autogenerate
untuk satu kolom boolean. Verifikasi dengan `alembic upgrade head` dan
`alembic revision --autogenerate` (harus menghasilkan migrasi kosong).
"""
from alembic import op
import sqlalchemy as sa


revision = 'b7c1a2d93e5f'
down_revision = '903f737d4420'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'formulasi',
        sa.Column('aktif', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column('formulasi', 'aktif', server_default=None)


def downgrade() -> None:
    op.drop_column('formulasi', 'aktif')
