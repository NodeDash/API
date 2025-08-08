"""Add influxdb to provider_type enum

Revision ID: a1b2c3d4e5f6
Revises: 98f059c4baa7
Create Date: 2025-08-08 00:00:01

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "98f059c4baa7"
branch_labels = None
depends_on = None


def upgrade():
    # Add new enum value to Postgres enum type
    op.execute("ALTER TYPE provider_type ADD VALUE IF NOT EXISTS 'influxdb'")


def downgrade():
    # No straightforward way to remove enum value in Postgres; leaving as no-op
    pass
