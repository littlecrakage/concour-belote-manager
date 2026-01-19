from config import db
from models.team import Team
from models.match import Match
from datetime import datetime

import random

class Tournament:
    def add_team(self, name, player1_name, player2_name):
        if self.has_started():
            return False  # Ne pas ajouter d'équipe si le tournoi a commencé

        if Team.query.filter_by(name=name).first():
            return False  # Équipe déjà existante

        new_team = Team(name=name, players=[player1_name, player2_name])
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
        return True

    def has_unplayed_matches(self):
        return Match.query.filter(Match.score1.is_(None)).first() is not None

    def generate_next_round(self):
        if self.has_unplayed_matches():
            return False  # Il reste des matchs non joués

        teams = self.get_ranking()

        if len(teams) < 2:
            return False

        if len(teams) % 2 != 0:
            return False

        # Supprimer uniquement les matchs non joués
        Match.query.filter(Match.score1.is_(None)).delete()
        db.session.commit()

        # Générer les matchs pour le prochain tour : 1er vs 2ème, 3ème vs 4ème, etc.
        for i in range(0, len(teams), 2):
            if i + 1 < len(teams):
                match = Match(team1_id=teams[i].id, team2_id=teams[i + 1].id)
                db.session.add(match)

        db.session.commit()
        return True

    def generate_first_round_matches(self):
        teams = self.get_teams()
        if len(teams) % 2 != 0:
            return False  # Le nombre d'équipes doit être pair

        # Mélangez les équipes de manière aléatoire
        random.shuffle(teams)

        # Créez des matchs en appariant les équipes aléatoirement
        for i in range(0, len(teams), 2):
            team1 = teams[i]
            team2 = teams[i + 1]

            # Vérifiez qu'un match entre ces deux équipes n'existe pas déjà
            existing_match = Match.query.filter(
                ((Match.team1_id == team1.id) & (Match.team2_id == team2.id)) |
                ((Match.team1_id == team2.id) & (Match.team2_id == team1.id))
            ).first()

            if not existing_match:
                match = Match(team1_id=team1.id, team2_id=team2.id)
                db.session.add(match)

        db.session.commit()
        return True





