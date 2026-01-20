# models/team.py
from extensions import db

class Team(db.Model):
    __tablename__ = 'teams'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    points = db.Column(db.Integer, default=0)
    matches_played = db.Column(db.Integer, default=0)
    points_for = db.Column(db.Integer, default=0)
    points_against = db.Column(db.Integer, default=0)
    players = db.relationship('Player', backref='team', lazy=True)

    def add_player(self, player_name):
        if len(self.players) >= 2:
            return False

        if not any(player.name == player_name for player in self.players):
            player = Player(name=player_name, team_id=self.id)
            db.session.add(player)
            db.session.commit()
            return True
        return False

    def remove_player(self, player_name):
        player = next((p for p in self.players if p.name == player_name), None)
        if player:
            db.session.delete(player)
            db.session.commit()
            return True
        return False

    def __repr__(self):
        return f'<Team {self.name}>'

class Player(db.Model):
    __tablename__ = 'players'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
