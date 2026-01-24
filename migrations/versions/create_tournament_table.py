"""Create tournament table with ranking system and duplicate prevention settings

Revision ID: 002_create_tournament
Revises: add_performance_indexes
Create Date: 2026-01-24 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_create_tournament'
down_revision = 'add_performance_indexes'
branch_labels = None
depends_on = None


def upgrade():
    # Create tournaments table
    op.create_table(
        'tournaments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ranking_system', sa.String(20), nullable=False, server_default='points_sum'),
        sa.Column('prevent_duplicate_matches', sa.Boolean(), nullable=False, server_default='False'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('tournaments')
