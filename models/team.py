# models/team.py
from config import db
import json

class Team(db.Model):
    __tablename__ = 'teams'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    points = db.Column(db.Integer, default=0)
    matches_played = db.Column(db.Integer, default=0)
    points_for = db.Column(db.Integer, default=0)
    points_against = db.Column(db.Integer, default=0)
    players = db.Column(db.JSON, default=[])  # Stocke les joueurs comme une liste dans un champ JSON

    def add_player(self, player_name):
        players = self.players if self.players else []
        if len(players) >= 2:
            return False  # Ne pas ajouter si l'équipe a déjà 2 joueurs
        if player_name not in players:
            players.append(player_name)
            self.players = players
            db.session.commit()
            return True
        return False

    
    def remove_player(self, player_name):
        if not isinstance(self.players, list):
            self.players = []

        # Convertir les noms en chaînes de caractères et les normaliser
        self.players = [str(player) for player in self.players]

        if player_name in self.players:
            self.players.remove(player_name)
            db.session.commit()
            print(f"Joueurs après suppression: {self.players}")
            return True
        return False


    def __repr__(self):
        return f'<Team {self.name}>'
