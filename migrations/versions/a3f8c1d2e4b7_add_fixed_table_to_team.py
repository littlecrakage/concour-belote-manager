"""add fixed_table and tournament_team_number to team

Revision ID: a3f8c1d2e4b7
Revises: 6838bf99b815
Create Date: 2026-03-29 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = 'a3f8c1d2e4b7'
down_revision = '6838bf99b815'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('teams', schema=None) as batch_op:
        batch_op.add_column(sa.Column('fixed_table', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('tournament_team_number', sa.Integer(), nullable=True))

    # Backfill tournament_team_number: assign sequential numbers per tournament
    conn = op.get_bind()
    tournaments = conn.execute(text("SELECT id FROM tournaments")).fetchall()
    for (tournament_id,) in tournaments:
        teams = conn.execute(
            text("SELECT id FROM teams WHERE tournament_id = :tid ORDER BY id"),
            {"tid": tournament_id}
        ).fetchall()
        for number, (team_id,) in enumerate(teams, start=1):
            conn.execute(
                text("UPDATE teams SET tournament_team_number = :num WHERE id = :tid"),
                {"num": number, "tid": team_id}
            )


def downgrade():
    with op.batch_alter_table('teams', schema=None) as batch_op:
        batch_op.drop_column('tournament_team_number')
        batch_op.drop_column('fixed_table')
