"""Initial migration - create search query tables

Revision ID: 0c3f5e1a2b3d
Revises: 
Create Date: 2026-11-20 20:20:46.489733

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0c3f5e1a2b3d'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create search_query_status table first (referenced by search_query)
    op.create_table(
        'search_query_status',
        sa.Column('id', sa.Integer, primary_key=True, nullable=False),
        sa.Column('description', sa.String, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True)
    )
    
    # Insert initial status records
    op.execute("""
        INSERT INTO search_query_status (id, description) VALUES 
        (0, 'scheduled'),
        (1, 'processing'),
        (2, 'done'),
        (3, 'error')
    """)
    
    # Create search_query table
    op.create_table(
        'search_query',
        sa.Column('id', sa.UUID, primary_key=True, server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('status_id', sa.Integer, sa.ForeignKey('search_query_status.id'), nullable=False, default=0),
        sa.Column('query_string', sa.String, nullable=False),
        sa.Column('pages', sa.Integer, nullable=False),
        sa.Column('time_range', sa.String, nullable=False),
        sa.Column('language', sa.String, nullable=False),
        sa.Column('safe_search', sa.Integer, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True)
    )
    
    # Create search_result table
    op.create_table(
        'search_result',
        sa.Column('id', sa.UUID, primary_key=True, server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('search_query_id', sa.UUID, sa.ForeignKey('search_query.id', ondelete='CASCADE'), nullable=False),
        sa.Column('img_src', sa.String, nullable=False),
        sa.Column('thumb_src', sa.String, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True)
    )
    
    # Create indexes for better query performance
    op.create_index('idx_search_query_status_id', 'search_query', ['status_id'])
    op.create_index('idx_search_result_search_query_id', 'search_result', ['search_query_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_search_result_search_query_id')
    op.drop_index('idx_search_query_status_id')
    
    # Drop tables
    op.drop_table('search_result')
    op.drop_table('search_query')
    op.drop_table('search_query_status')
