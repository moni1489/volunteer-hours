"""entry period

Replace volunteer_entries.date with a period: date_start (renamed from date) and date_end.
Existing single-day entries get date_end = date_start.

Revision ID: a3d9e1c24b70
Revises: f7c5554ead66
Create Date: 2026-11-21 20:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a3d9e1c24b70'
down_revision = 'f7c5554ead66'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('volunteer_entries') as batch_op:
        batch_op.alter_column(
            'date',
            new_column_name='date_start',
            existing_type=sa.Date(),
            existing_nullable=False,
        )
        batch_op.add_column(sa.Column('date_end', sa.Date(), nullable=True))

    op.execute("UPDATE volunteer_entries SET date_end = date_start")

    with op.batch_alter_table('volunteer_entries') as batch_op:
        batch_op.alter_column('date_end', existing_type=sa.Date(), nullable=False)


def downgrade():
    # Keeps only the start date; the end date is dropped.
    with op.batch_alter_table('volunteer_entries') as batch_op:
        batch_op.drop_column('date_end')
        batch_op.alter_column(
            'date_start',
            new_column_name='date',
            existing_type=sa.Date(),
            existing_nullable=False,
        )
