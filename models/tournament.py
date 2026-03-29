import json
import os
from sqlalchemy import func, or_
from extensions import db
from models.team import Team
from models.match import Match
from datetime import datetime, timedelta

import random

class Tournament(db.Model):
    __tablename__ = 'tournaments'
    
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    ranking_system = db.Column(db.String(50), default='points_sum')  # 'points_sum' or 'soccer_style'
    prevent_duplicate_matches = db.Column(db.Boolean, default=False)
    verify_belote_scores = db.Column(db.Boolean, default=True)
    pairing_system = db.Column(db.String(20), default='ranked')  # 'ranked' or 'random'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    current_round = 0

    def add_team(self, name):
        if self.has_started():
            return False
        # Scope uniqueness check to THIS tournament
        if Team.query.filter_by(name=name, tournament_id=self.id).first():
            return False
        next_number = Team.query.filter_by(tournament_id=self.id).count() + 1
        new_team = Team(name=name, tournament_id=self.id, tournament_team_number=next_number)
        db.session.add(new_team)
        db.session.commit()
        return True

    def has_started(self):
        return Match.query.filter(
            Match.tournament_id == self.id,
            Match.score1.isnot(None)
        ).first() is not None

    def get_teams(self):
        return Team.query.filter_by(tournament_id=self.id).order_by(Team.name).all()

    def get_matches(self):
        return Match.query.filter_by(tournament_id=self.id).all()

    def get_unplayed_matches(self):
        return Match.query.filter_by(
            tournament_id=self.id
        ).filter(Match.score1.is_(None)).order_by(Match.table_number).all()

    def get_played_matches(self):
        return Match.query.filter_by(
            tournament_id=self.id
        ).filter(Match.score1.isnot(None)).all()
    

    def get_current_round(self):
        result = db.session.query(func.max(Match.round_number)).filter(
            Match.tournament_id == self.id
        ).scalar()
        return result or 0

    def get_ranking(self):
        """Get teams ranked by the configured ranking system"""
        teams = Team.query.all()
        
        if self.ranking_system == 'soccer_style':
            # Calculate soccer points for each team
            for team in teams:
                team.soccer_points = self._calculate_soccer_points(team)
                team.point_difference = team.points_for - team.points_against
            
            # Sort by soccer points, then point difference, then points for
            teams.sort(key=lambda t: (-t.soccer_points, -t.point_difference, -t.points_for))
        else:
            # Default: sort by points_for (sum of points)
            teams.sort(key=lambda t: (-t.points_for, -(t.points_for - t.points_against), t.points_against))
        
        return teams
    
    def _calculate_soccer_points(self, team):
        """Calculate soccer-style points: 3 for win, 1 for draw, 0 for loss"""
        points = 0
        
        # Get all completed matches for this team
        matches = Match.query.filter(
            ((Match.team1_id == team.id) | (Match.team2_id == team.id)) &
            (Match.score1.isnot(None))
        ).all()
        
        for match in matches:
            if match.team1_id == team.id:
                team_score = match.score1
                opponent_score = match.score2
            else:
                team_score = match.score2
                opponent_score = match.score1
            
            if team_score > opponent_score:
                points += 3  # Win
            elif team_score == opponent_score:
                points += 1  # Draw
            # Loss = 0 points
        
        return points

    def remove_team(self, team_id):
        team = Team.query.filter_by(id=team_id, tournament_id=self.id).first()
        if not team:
            return False, "Équipe introuvable."

        if Match.query.filter(
            (Match.team1_id == team.id) | (Match.team2_id == team.id)
        ).first():
            return False, "Impossible de supprimer cette équipe car elle a des matchs associés (joués ou à venir)."

        for player in team.players[:]:
            db.session.delete(player)

        db.session.delete(team)
        db.session.commit()
        return True, None

    def reset_tournament(self):
        Match.query.filter_by(tournament_id=self.id).delete()
        teams = Team.query.filter_by(tournament_id=self.id).all()
        for team in teams:
            team.points_for = 0
            team.points_against = 0
        db.session.commit()

    def has_unplayed_matches(self):
        return Match.query.filter(Match.tournament_id == self.id,
                                  Match.score1.is_(None)).first() is not None

    def have_teams_played(self, team1_id, team2_id):
        return Match.query.filter(
            Match.tournament_id == self.id,
            or_(
                (Match.team1_id == team1_id) & (Match.team2_id == team2_id),
                (Match.team1_id == team2_id) & (Match.team2_id == team1_id)
            )
        ).first() is not None

    def generate_next_round(self):
        if self.has_unplayed_matches():
            return False  # Il reste des matchs non joués
        Match.query.filter(
            Match.tournament_id == self.id,
            Match.is_closed.isnot(True)).update({'is_closed': True})

        teams = self.get_ranking()

        if len(teams) < 2:
            return False

        if len(teams) % 2 != 0:
            return False

        # Random draw: shuffle before pairing
        if self.pairing_system == 'random':
            random.shuffle(teams)

        # If prevent_duplicate_matches is enabled, use smart pairing
        if self.prevent_duplicate_matches:
            return self._generate_round_no_duplicates(teams)

        # Default: pair sequentially (ranked: 1st vs 2nd, 3rd vs 4th… / random: shuffled order)
        next_round = self.get_current_round() + 1
        pairs = [(teams[i], teams[i + 1]) for i in range(0, len(teams), 2) if i + 1 < len(teams)]
        table_numbers = self._assign_tables(pairs)
        for (team1, team2), table_num in zip(pairs, table_numbers):
            match = Match(team1_id=team1.id, team2_id=team2.id, table_number=table_num, round_number=next_round, tournament_id=self.id)
            db.session.add(match)

        db.session.commit()
        return True

    def _assign_tables(self, pairs):
        """Assign table numbers respecting fixed tables for teams with disabilities.
        Teams with a fixed_table always play at that table.
        If two fixed-table teams face each other, one is chosen randomly.
        All other matches fill the remaining table numbers."""
        num_matches = len(pairs)
        all_tables = list(range(1, num_matches + 1))
        assigned = [None] * num_matches
        fixed_tables_taken = set()

        # First pass: assign fixed tables
        for i, (t1, t2) in enumerate(pairs):
            ft1 = t1.fixed_table
            ft2 = t2.fixed_table
            chosen = None
            if ft1 and ft2:
                chosen = random.choice([ft1, ft2])
            elif ft1:
                chosen = ft1
            elif ft2:
                chosen = ft2

            if chosen and chosen not in fixed_tables_taken:
                assigned[i] = chosen
                fixed_tables_taken.add(chosen)

        # Second pass: fill remaining matches with free tables
        free_tables = [t for t in all_tables if t not in fixed_tables_taken]
        free_iter = iter(free_tables)
        for i in range(num_matches):
            if assigned[i] is None:
                assigned[i] = next(free_iter)

        return assigned

    def _generate_round_no_duplicates(self, teams):
        """Generate matches ensuring no team plays the same opponent twice"""
        available = list(teams)
        pairs = []

        while len(available) >= 2:
            team1 = available.pop(0)
            paired = False

            # Try to find an opponent that team1 hasn't played yet
            for i, team2 in enumerate(available):
                if not self.have_teams_played(team1.id, team2.id):
                    pairs.append((team1, team2))
                    available.pop(i)
                    paired = True
                    break

            # If no valid opponent found, pair with the first available (duplicate match)
            if not paired and available:
                pairs.append((team1, available.pop(0)))

        # Assign tables respecting fixed tables
        table_numbers = self._assign_tables(pairs)
        next_round = self.get_current_round() + 1
        for (team1, team2), table_num in zip(pairs, table_numbers):
            match = Match(
                team1_id=team1.id,
                team2_id=team2.id,
                table_number=table_num,
                round_number=next_round,
                tournament_id=self.id
            )
            db.session.add(match)
        db.session.commit()
        return True

    def generate_first_round_matches(self):
        Match.query.filter_by(is_closed=False).update({'is_closed': True})
        db.session.commit()

        teams = self.get_teams()
        if len(teams) % 2 != 0:
            return False

        random.shuffle(teams)
        pairs = [(teams[i], teams[i + 1]) for i in range(0, len(teams), 2)]
        table_numbers = self._assign_tables(pairs)
        for (team1, team2), table_num in zip(pairs, table_numbers):
            match = Match(team1_id=team1.id, team2_id=team2.id, table_number=table_num, round_number=1, tournament_id=self.id)
            db.session.add(match)

        db.session.commit()
        return True

    def get_scores_by_round(self):
        # Récupérer tous les tours joués
        rounds = db.session.query(Match.round_number).distinct().order_by(Match.round_number).all()
        round_numbers = [round[0] for round in rounds if round[0] is not None]

        # Récupérer toutes les équipes triées par points (classement)
        teams = Team.query.order_by(
            Team.points_for.desc(),
            (Team.points_for - Team.points_against).desc(),
            Team.points_against.asc()
        ).all()
        
        # Batch-fetch all matches at once instead of querying per-team-per-round
        all_matches = Match.query.all()
        
        # Build a lookup dict: (team_id, round_number) -> match
        match_map = {}
        for match in all_matches:
            match_map[(match.team1_id, match.round_number)] = match
            match_map[(match.team2_id, match.round_number)] = match

        # Préparer les données pour chaque équipe
        teams_scores = []
        for team in teams:
            team_data = {'team_name': team.name,
                         'team_id': team.id,
                         'team_num': team.tournament_team_number,
                         'team_points_for': team.points_for}
            for round_num in round_numbers:
                # Lookup from map instead of querying
                match = match_map.get((team.id, round_num))

                if match:
                    if match.team1_id == team.id:
                        team_data[f'round_{round_num}'] = match.score1
                    else:
                        team_data[f'round_{round_num}'] = match.score2
                else:
                    team_data[f'round_{round_num}'] = None

            teams_scores.append(team_data)

        return teams_scores, round_numbers
    
    @property
    def expires_at(self):
        return self.created_at + timedelta(weeks=2)
    
    @property
    def is_expired(self):
        return datetime.utcnow() > self.expires_at
    
    @property
    def days_remaining(self):
        delta = self.expires_at - datetime.utcnow()
        return max(0, delta.days)







