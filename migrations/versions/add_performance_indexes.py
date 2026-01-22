"""Add performance indexes for query optimization

Revision ID: add_performance_indexes
Revises: fa02f749a45a
Create Date: 2025-01-22 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_performance_indexes'
down_revision = 'fa02f749a45a'
branch_labels = None
depends_on = None


def upgrade():
    # Create indexes for matches table
    op.create_index('ix_matches_round_number', 'matches', ['round_number'])
    op.create_index('ix_matches_team1_id', 'matches', ['team1_id'])
    op.create_index('ix_matches_team2_id', 'matches', ['team2_id'])
    op.create_index('ix_matches_score1', 'matches', ['score1'])
    
    # Create indexes for teams table
    op.create_index('ix_teams_name', 'teams', ['name'])
    op.create_index('ix_teams_matches_played', 'teams', ['matches_played'])
    op.create_index('ix_teams_points_for', 'teams', ['points_for'])
    
    # Create indexes for users table
    op.create_index('ix_users_username', 'users', ['username'])
    
    # Create indexes for players table
    op.create_index('ix_players_team_id', 'players', ['team_id'])


def downgrade():
    # Drop all created indexes
    op.drop_index('ix_matches_round_number', table_name='matches')
    op.drop_index('ix_matches_team1_id', table_name='matches')
    op.drop_index('ix_matches_team2_id', table_name='matches')
    op.drop_index('ix_matches_score1', table_name='matches')
    op.drop_index('ix_teams_name', table_name='teams')
    op.drop_index('ix_teams_matches_played', table_name='teams')
    op.drop_index('ix_teams_points_for', table_name='teams')
    op.drop_index('ix_users_username', table_name='users')
    op.drop_index('ix_players_team_id', table_name='players')
