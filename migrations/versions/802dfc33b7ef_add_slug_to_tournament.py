"""add slug to tournament

Revision ID: 802dfc33b7ef
Revises: 002_create_tournament
Create Date: 2026-02-19 00:58:28.670928

"""
from alembic import op
import sqlalchemy as sa

revision = '802dfc33b7ef'
down_revision = '002_create_tournament'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('matches', schema=None) as batch_op:
        batch_op.add_column(sa.Column('tournament_id', sa.Integer(), nullable=True))
        batch_op.drop_index(batch_op.f('ix_matches_round_number'))
        batch_op.drop_index(batch_op.f('ix_matches_score1'))
        batch_op.drop_index(batch_op.f('ix_matches_team1_id'))
        batch_op.drop_index(batch_op.f('ix_matches_team2_id'))
        batch_op.create_foreign_key('fk_matches_tournament_id', 'tournaments', ['tournament_id'], ['id'])

    with op.batch_alter_table('players', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_players_team_id'))

    with op.batch_alter_table('teams', schema=None) as batch_op:
        batch_op.add_column(sa.Column('tournament_id', sa.Integer(), nullable=True))
        batch_op.drop_index(batch_op.f('ix_teams_matches_played'))
        batch_op.drop_index(batch_op.f('ix_teams_name'))
        batch_op.drop_index(batch_op.f('ix_teams_points_for'))
        batch_op.create_foreign_key('fk_teams_tournament_id', 'tournaments', ['tournament_id'], ['id'])

    with op.batch_alter_table('tournaments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('slug', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('created_at', sa.DateTime(), nullable=True))
        batch_op.alter_column('ranking_system',
               existing_type=sa.VARCHAR(length=20),
               type_=sa.String(length=50),
               nullable=True,
               existing_server_default=sa.text("'points_sum'"))
        batch_op.alter_column('prevent_duplicate_matches',
               existing_type=sa.BOOLEAN(),
               nullable=True,
               existing_server_default=sa.text("'False'"))
        batch_op.create_unique_constraint('uq_tournaments_slug', ['slug'])

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('tournament_id', sa.Integer(), nullable=True))
        batch_op.drop_index(batch_op.f('ix_users_username'))
        batch_op.create_foreign_key('fk_users_tournament_id', 'tournaments', ['tournament_id'], ['id'])


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_constraint('fk_users_tournament_id', type_='foreignkey')
        batch_op.create_index(batch_op.f('ix_users_username'), ['username'], unique=False)
        batch_op.drop_column('tournament_id')

    with op.batch_alter_table('tournaments', schema=None) as batch_op:
        batch_op.drop_constraint('uq_tournaments_slug', type_='unique')
        batch_op.alter_column('prevent_duplicate_matches',
               existing_type=sa.BOOLEAN(),
               nullable=False,
               existing_server_default=sa.text("'False'"))
        batch_op.alter_column('ranking_system',
               existing_type=sa.String(length=50),
               type_=sa.VARCHAR(length=20),
               nullable=False,
               existing_server_default=sa.text("'points_sum'"))
        batch_op.drop_column('created_at')
        batch_op.drop_column('slug')

    with op.batch_alter_table('teams', schema=None) as batch_op:
        batch_op.drop_constraint('fk_teams_tournament_id', type_='foreignkey')
        batch_op.create_index(batch_op.f('ix_teams_points_for'), ['points_for'], unique=False)
        batch_op.create_index(batch_op.f('ix_teams_name'), ['name'], unique=False)
        batch_op.create_index(batch_op.f('ix_teams_matches_played'), ['matches_played'], unique=False)
        batch_op.drop_column('tournament_id')

    with op.batch_alter_table('players', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_players_team_id'), ['team_id'], unique=False)

    with op.batch_alter_table('matches', schema=None) as batch_op:
        batch_op.drop_constraint('fk_matches_tournament_id', type_='foreignkey')
        batch_op.create_index(batch_op.f('ix_matches_team2_id'), ['team2_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_matches_team1_id'), ['team1_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_matches_score1'), ['score1'], unique=False)
        batch_op.create_index(batch_op.f('ix_matches_round_number'), ['round_number'], unique=False)
        batch_op.drop_column('tournament_id')
