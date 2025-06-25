"""Remove foreign key constraints for polymorphic ownership

Revision ID: 98f059c4baa7
Revises: 27a9320b8bb2
Create Date: 2025-06-24 13:45:23.531734+00:00

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "98f059c4baa7"
down_revision = "27a9320b8bb2"
branch_labels = None
depends_on = None


def upgrade():
    # Remove foreign key constraints for polymorphic ownership
    # These tables support both USER and TEAM ownership via owner_type field

    # Drop foreign key constraint on integrations table
    op.drop_constraint("integrations_owner_id_fkey", "integrations", type_="foreignkey")

    # Drop foreign key constraint on devices table
    op.drop_constraint("devices_owner_id_fkey", "devices", type_="foreignkey")

    # Drop foreign key constraint on flows table
    op.drop_constraint("flows_owner_id_fkey", "flows", type_="foreignkey")

    # Drop foreign key constraint on functions table
    op.drop_constraint("functions_owner_id_fkey", "functions", type_="foreignkey")

    # Drop foreign key constraint on labels table
    op.drop_constraint("labels_owner_id_fkey", "labels", type_="foreignkey")

    # Drop foreign key constraint on storage table
    op.drop_constraint("storage_owner_id_fkey", "storage", type_="foreignkey")


def downgrade():
    # Re-add foreign key constraints (this will only work if all owner_ids reference valid users)
    # Note: This downgrade may fail if there are team-owned records in the database

    op.create_foreign_key(
        "storage_owner_id_fkey", "storage", "users", ["owner_id"], ["id"]
    )
    op.create_foreign_key(
        "labels_owner_id_fkey", "labels", "users", ["owner_id"], ["id"]
    )
    op.create_foreign_key(
        "functions_owner_id_fkey", "functions", "users", ["owner_id"], ["id"]
    )
    op.create_foreign_key("flows_owner_id_fkey", "flows", "users", ["owner_id"], ["id"])
    op.create_foreign_key(
        "devices_owner_id_fkey", "devices", "users", ["owner_id"], ["id"]
    )
    op.create_foreign_key(
        "integrations_owner_id_fkey", "integrations", "users", ["owner_id"], ["id"]
    )
