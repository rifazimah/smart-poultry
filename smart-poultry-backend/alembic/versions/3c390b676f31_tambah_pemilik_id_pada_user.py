"""tambah pemilik_id pada user

Revision ID: 3c390b676f31
Revises: b7c1a2d93e5f
Create Date: 2026-11-01 19:33:24.643919

Hasil autogenerate, disesuaikan: FK diberi nama (agar downgrade berjalan) dan
Pekerja lama di-backfill dari kandang yang pernah ditugaskan kepadanya.
"""
from alembic import op
import sqlalchemy as sa


revision = '3c390b676f31'
down_revision = 'b7c1a2d93e5f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('user', sa.Column('pemilik_id', sa.Uuid(), nullable=True))
    op.create_index(op.f('ix_user_pemilik_id'), 'user', ['pemilik_id'], unique=False)
    op.create_foreign_key('fk_user_pemilik_id_user', 'user', 'user', ['pemilik_id'], ['id'])

    # Backfill: pemilik Pekerja = pemilik kandang dari penugasan terbaru.
    op.execute(
        """
        UPDATE "user" AS u
        SET pemilik_id = sub.pemilik_id
        FROM (
            SELECT DISTINCT ON (p.user_id) p.user_id, k.pemilik_id
            FROM penugasan_kandang p
            JOIN kandang k ON k.id = p.kandang_id
            ORDER BY p.user_id, p.tanggal_mulai DESC
        ) AS sub
        WHERE u.id = sub.user_id AND u.role = 'PEKERJA' AND u.pemilik_id IS NULL
        """
    )


def downgrade() -> None:
    op.drop_constraint('fk_user_pemilik_id_user', 'user', type_='foreignkey')
    op.drop_index(op.f('ix_user_pemilik_id'), table_name='user')
    op.drop_column('user', 'pemilik_id')
