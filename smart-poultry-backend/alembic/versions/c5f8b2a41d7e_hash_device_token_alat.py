"""hash device token alat

Revision ID: c5f8b2a41d7e
Revises: 9d4e7a1c5b20
Create Date: 2026-11-02 12:00:00.000000

Kolom `alat.device_token` (token mentah) diganti `alat.device_token_hash` (SHA-256 hex).
Token yang sudah terdaftar di-hash di tempat, sehingga alat yang sudah ada tetap valid
dengan token lamanya (server meng-hash header X-Device-Token sebelum mencari).

Downgrade hanya mengembalikan nama kolom/indeks. Token mentah TIDAK dapat dipulihkan dari hash:
setelah downgrade, isi kolom tetap hash sehingga semua alat harus diberi token baru
(POST /alat/{id}/rotasi-token pada versi kode yang lama).
"""
from alembic import op


revision = 'c5f8b2a41d7e'
down_revision = '9d4e7a1c5b20'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('alat', 'device_token', new_column_name='device_token_hash')
    op.execute(
        "UPDATE alat SET device_token_hash = encode(sha256(convert_to(device_token_hash, 'UTF8')), 'hex')"
    )
    op.drop_index('ix_alat_device_token', table_name='alat')
    op.create_index('ix_alat_device_token_hash', 'alat', ['device_token_hash'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_alat_device_token_hash', table_name='alat')
    op.alter_column('alat', 'device_token_hash', new_column_name='device_token')
    op.create_index('ix_alat_device_token', 'alat', ['device_token'], unique=True)
