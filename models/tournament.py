import json
import os
from sqlalchemy import func, or_
from extensions import db
from models.team import Team
from models.match import Match
from datetime import datetime

import random

class Tournament(db.Model):
    __tablename__ = 'tournaments'
    
    id = db.Column(db.Integer, primary_key=True)
    ranking_system = db.Column(db.String(50), default='points_sum')  # 'points_sum' or 'soccer_style'
    prevent_duplicate_matches = db.Column(db.Boolean, default=False)
    
    current_round = 0

    def add_team(self, name):
        if self.has_started():
            return False  # Ne pas ajouter d'équipe si le tournoi a commencé

        if Team.query.filter_by(name=name).first():
            return False  # Équipe déjà existante

        new_team = Team(name=name)
        db.session.add(new_team)
        db.session.commit()
        return True

    def has_started(self):
        return Match.query.filter(Match.score1.isnot(None)).first() is not None

    def get_teams(self):
        """Récupère toutes les équipes triées par nom."""
        return Team.query.order_by(Team.name).all()

    def get_matches(self):
        return Match.query.all()

    def get_unplayed_matches(self):
        return Match.query.filter(Match.score1.is_(None)).all()

    def get_played_matches(self):
        return Match.query.filter(Match.score1.isnot(None)).all()
    

    def get_current_round(self):
        min_matches = db.session.query(func.min(Team.matches_played)).scalar()
        return (min_matches if min_matches is not None else 0) + 1

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

    def remove_team(self, team_name):
        # Trouver l'équipe par son nom
        team = Team.query.filter_by(name=team_name).first()
        if not team:
            return False  # Équipe non trouvée

        # Vérifier si l'équipe a déjà joué des matchs
        if Match.query.filter(
            ((Match.team1_id == team.id) | (Match.team2_id == team.id)) &
            (Match.is_closed == True)
        ).first():
            return False  # L'équipe a déjà joué des matchs

        # Supprimer explicitement les joueurs de l'équipe
        for player in team.players[:]:  # Utilisez une copie de la liste pour éviter les problèmes d'itération
            db.session.delete(player)

        # Supprimer l'équipe
        db.session.delete(team)
        db.session.commit()
        return True

    def reset_tournament(self):
        teams = Team.query.all()
        for team in teams:
            team.matches_played = 0
            team.points_for = 0
            team.points_against = 0

        # Supprimer tous les matchs
        Match.query.delete()

        db.session.commit()
        return True

    def has_unplayed_matches(self):
        return Match.query.filter(Match.score1.is_(None)).first() is not None

    def have_teams_played(self, team1_id, team2_id):
        """Check if two teams have already played against each other"""
        return Match.query.filter(
            ((Match.team1_id == team1_id) & (Match.team2_id == team2_id)) |
            ((Match.team1_id == team2_id) & (Match.team2_id == team1_id))
        ).first() is not None

    def generate_next_round(self):
        if self.has_unplayed_matches():
            return False  # Il reste des matchs non joués
        Match.query.filter(Match.is_closed.isnot(True)).update({'is_closed': True})

        teams = self.get_ranking()

        if len(teams) < 2:
            return False

        if len(teams) % 2 != 0:
            return False

        # If prevent_duplicate_matches is enabled, use smart pairing
        if self.prevent_duplicate_matches:
            return self._generate_round_no_duplicates(teams)
        
        # Default: Générer les matchs pour le prochain tour : 1er vs 2ème, 3ème vs 4ème, etc.
        table_number = 0
        for i in range(0, len(teams), 2):
            table_number += 1
            if i + 1 < len(teams):
                match = Match(team1_id=teams[i].id, team2_id=teams[i + 1].id, table_number = table_number,round_number=self.get_current_round())
                db.session.add(match)

        db.session.commit()
        return True
    
    def _generate_round_no_duplicates(self, teams):
        """Generate matches ensuring no team plays the same opponent twice"""
        available = list(teams)
        matches_to_create = []
        table_number = 0
        
        while len(available) >= 2:
            team1 = available.pop(0)
            paired = False
            
            # Try to find an opponent that team1 hasn't played yet
            for i, team2 in enumerate(available):
                if not self.have_teams_played(team1.id, team2.id):
                    table_number += 1
                    matches_to_create.append((team1.id, team2.id, table_number))
                    available.pop(i)
                    paired = True
                    break
            
            # If no valid opponent found, pair with the first available (duplicate match)
            if not paired and available:
                table_number += 1
                team2 = available.pop(0)
                matches_to_create.append((team1.id, team2.id, table_number))
        
        # Create all matches
        current_round = self.get_current_round()
        for team1_id, team2_id, table_num in matches_to_create:
            match = Match(team1_id=team1_id, team2_id=team2_id, table_number=table_num, round_number=current_round)
            db.session.add(match)
        
        db.session.commit()
        return True

    def generate_first_round_matches(self):
        Match.query.filter_by(is_closed=False).update({'is_closed': True})
        db.session.commit()

        teams = self.get_teams()
        if len(teams) % 2 != 0:
            return False  # Le nombre d'équipes doit être pair

        # Mélangez les équipes de manière aléatoire
        random.shuffle(teams)
        table_number = 0

        # Créez des matchs en appariant les équipes aléatoirement
        for i in range(0, len(teams), 2):
            table_number += 1
            team1 = teams[i]
            team2 = teams[i + 1]

            match = Match(team1_id=team1.id, team2_id=team2.id, table_number = table_number, round_number=self.get_current_round())
            
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







