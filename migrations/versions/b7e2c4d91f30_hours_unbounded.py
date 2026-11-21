"""hours column: widen to allow any realistic value

Revision ID: b7e2c4d91f30
Revises: a3d9e1c24b70
Create Date: 2026-11-21

"""
import sqlalchemy as sa
from alembic import op

revision = "b7e2c4d91f30"
down_revision = "a3d9e1c24b70"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("volunteer_entries") as batch:
        batch.alter_column("hours", existing_type=sa.Numeric(4, 1), type_=sa.Numeric(10, 1), existing_nullable=False)


def downgrade():
    with op.batch_alter_table("volunteer_entries") as batch:
        batch.alter_column("hours", existing_type=sa.Numeric(10, 1), type_=sa.Numeric(4, 1), existing_nullable=False)
