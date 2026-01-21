import json
import os
from sqlalchemy import or_
from extensions import db
from models.team import Team
from models.match import Match
from datetime import datetime

import random

class Tournament():

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
        if os.path.exists('current_round.json'):
            with open('current_round.json', 'r') as f:
                return json.load(f)['current_round']
        return 0

    def increment_current_round(self):
        current_round = self.get_current_round() + 1
        with open('current_round.json', 'w') as f:
            json.dump({'current_round': current_round}, f)
    
    def reset_current_round(self):
        with open('current_round.json', 'w') as f:
            json.dump({'current_round': 0}, f)


    def get_ranking(self):
        return Team.query.order_by(
            Team.points.desc(),
            (Team.points_for - Team.points_against).desc(),
            Team.points_for.desc(),
            Team.points_against.asc()
        ).all()

    def remove_team(self, team_name):
        team = Team.query.filter_by(name=team_name).first()
        if not team:
            return False

        # Vérifiez si l'équipe a déjà joué des matchs
        if Match.query.filter(
            (Match.team1_id == team.id) | (Match.team2_id == team.id),
            Match.score1.isnot(None)
        ).first():
            return False

        # Supprimez l'équipe (les joueurs seront supprimés automatiquement grâce à la relation)
        db.session.delete(team)
        db.session.commit()
        return True

    def reset_tournament(self):
        teams = Team.query.all()
        for team in teams:
            team.points = 0
            team.matches_played = 0
            team.points_for = 0
            team.points_against = 0

        # Supprimer tous les matchs
        Match.query.delete()

        db.session.commit()
        self.reset_current_round()
        return True

    def has_unplayed_matches(self):
        return Match.query.filter(Match.score1.is_(None)).first() is not None

    def generate_next_round(self):
        if self.has_unplayed_matches():
            return False  # Il reste des matchs non joués
        Match.query.filter(Match.is_closed.isnot(True)).update({'is_closed': True})

        teams = self.get_ranking()

        if len(teams) < 2:
            return False

        if len(teams) % 2 != 0:
            return False

        # Générer les matchs pour le prochain tour : 1er vs 2ème, 3ème vs 4ème, etc.
        table_number = 0
        for i in range(0, len(teams), 2):
            table_number += 1
            if i + 1 < len(teams):
                match = Match(team1_id=teams[i].id, team2_id=teams[i + 1].id, table_number = table_number)
                db.session.add(match)

        db.session.commit()
        self.increment_current_round()
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

            match = Match(team1_id=team1.id, team2_id=team2.id, table_number = table_number)
            
            db.session.add(match)

        db.session.commit()
        self.increment_current_round()
        return True
    
    def update_match_result(self, match_id, team1_score, team2_score):
        match = Match.query.get(match_id)
        if not match or match.tournament_id != self.id:
            return False  # Match non trouvé ou ne fait pas partie de ce tournoi

        if match.is_closed:
            return False  # Match déjà terminé ou fermé

        match.team1_score = team1_score
        match.team2_score = team2_score
        match.is_completed = True

        # Mettre à jour les points des équipes
        team1 = Team.query.get(match.team1_id)
        team2 = Team.query.get(match.team2_id)

        if team1_score > team2_score:
            team1.points += 2
            team2.points += 1
        elif team2_score > team1_score:
            team2.points += 2
            team1.points += 1
        else:
            team1.points += 1
            team2.points += 1

        db.session.commit()
        return True






