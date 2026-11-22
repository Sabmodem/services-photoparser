"""add_download_task_table

Revision ID: c501b01595c2
Revises: 0da575080747
Create Date: 2026-11-22 17:11:12.811416

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c501b01595c2'
down_revision: Union[str, Sequence[str], None] = '0da575080747'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add download_task table."""
    op.create_table(
        'download_task',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('search_query_id', sa.UUID(), nullable=False),
        sa.Column('status_id', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('archive_path', sa.String(), nullable=True),
        sa.Column('filename', sa.String(), nullable=True),
        sa.Column('total', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('downloaded', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_msg', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['search_query_id'], ['search_query.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['status_id'], ['search_query_status.id']),
    )
    op.create_index(op.f('ix_download_task_id'), 'download_task', ['id'], unique=False)


def downgrade() -> None:
    """Remove download_task table."""
    op.drop_index(op.f('ix_download_task_id'), table_name='download_task')
    op.drop_table('download_task')
