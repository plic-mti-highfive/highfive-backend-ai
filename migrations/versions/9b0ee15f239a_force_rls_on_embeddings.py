"""force_rls_on_embeddings

Revision ID: 9b0ee15f239a
Revises: 8dd8f7f5288f
Create Date: 2026-03-30 18:36:59.493761

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9b0ee15f239a"
down_revision: Union[str, Sequence[str], None] = "8dd8f7f5288f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TABLE embeddings FORCE ROW LEVEL SECURITY")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TABLE embeddings NO FORCE ROW LEVEL SECURITY")
