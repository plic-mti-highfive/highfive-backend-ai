"""add rls with tenant_id

Revision ID: 8dd8f7f5288f
Revises: 6073a549a951
Create Date: 2026-03-30 17:11:09.020647

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8dd8f7f5288f"
down_revision: Union[str, Sequence[str], None] = "6073a549a951"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create a function to get the current tenant_id from session context
    op.execute(
        """
        CREATE OR REPLACE FUNCTION get_current_tenant_id() RETURNS UUID AS $$
        BEGIN
            RETURN current_setting('app.current_tenant_id')::UUID;
        EXCEPTION WHEN OTHERS THEN
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql STABLE;
        """
    )

    # Enable RLS on embeddings table
    op.execute("ALTER TABLE embeddings ENABLE ROW LEVEL SECURITY;")

    # Policy 1: Users can only SELECT rows where tenant_id matches their current tenant
    op.execute(
        """
        CREATE POLICY embeddings_select_policy ON embeddings
        FOR SELECT
        USING (tenant_id = get_current_tenant_id());
        """
    )

    # Policy 2: Users can only INSERT rows with their tenant_id
    op.execute(
        """
        CREATE POLICY embeddings_insert_policy ON embeddings
        FOR INSERT
        WITH CHECK (tenant_id = get_current_tenant_id());
        """
    )

    # Policy 3: Users can only UPDATE rows where tenant_id matches their current tenant
    op.execute(
        """
        CREATE POLICY embeddings_update_policy ON embeddings
        FOR UPDATE
        USING (tenant_id = get_current_tenant_id())
        WITH CHECK (tenant_id = get_current_tenant_id());
        """
    )

    # Policy 4: Users can only DELETE rows where tenant_id matches their current tenant
    op.execute(
        """
        CREATE POLICY embeddings_delete_policy ON embeddings
        FOR DELETE
        USING (tenant_id = get_current_tenant_id());
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop policies
    op.execute("DROP POLICY IF EXISTS embeddings_delete_policy ON embeddings;")
    op.execute("DROP POLICY IF EXISTS embeddings_update_policy ON embeddings;")
    op.execute("DROP POLICY IF EXISTS embeddings_insert_policy ON embeddings;")
    op.execute("DROP POLICY IF EXISTS embeddings_select_policy ON embeddings;")

    # Disable RLS
    op.execute("ALTER TABLE embeddings DISABLE ROW LEVEL SECURITY;")

    # Drop function
    op.execute("DROP FUNCTION IF EXISTS get_current_tenant_id();")
