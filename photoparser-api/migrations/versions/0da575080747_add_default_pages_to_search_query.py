"""add_default_pages_to_search_query

Revision ID: 0da575080747
Revises: 0c3f5e1a2b3d
Create Date: 2026-11-21 13:57:01.605461

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0da575080747'
down_revision: Union[str, Sequence[str], None] = '0c3f5e1a2b3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        'search_query',
        'pages',
        server_default='1',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        'search_query',
        'pages',
        server_default=None,
    )
