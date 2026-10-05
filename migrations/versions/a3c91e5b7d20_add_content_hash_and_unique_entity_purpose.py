"""add content_hash and unique (tenant, entity, purpose)

Revision ID: a3c91e5b7d20
Revises: 081d0b8d8cdb
Create Date: 2026-10-05 18:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3c91e5b7d20"
down_revision: Union[str, Sequence[str], None] = "081d0b8d8cdb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Hash du contenu source : évite de recalculer un embedding dont le texte n'a pas changé.
    op.add_column("embeddings", sa.Column("content_hash", sa.String(length=64), nullable=True))

    # Des jobs concurrents ont pu créer des doublons : on garde la ligne la plus récente.
    op.execute(
        """
        DELETE FROM embeddings e
        USING (
            SELECT id, ROW_NUMBER() OVER (
                PARTITION BY tenant_id, entity_id, vector_purpose
                ORDER BY updated_at DESC NULLS LAST, id
            ) AS rn
            FROM embeddings
        ) d
        WHERE e.id = d.id AND d.rn > 1
        """
    )
    op.create_index(
        "uq_embeddings_tenant_entity_purpose",
        "embeddings",
        ["tenant_id", "entity_id", "vector_purpose"],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("uq_embeddings_tenant_entity_purpose", table_name="embeddings")
    op.drop_column("embeddings", "content_hash")
