from extensions import db
from datetime import datetime
from models.team import Team

class Match(db.Model):
    __tablename__ = 'matches'

    id = db.Column(db.Integer, primary_key=True)
    team1_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    team2_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    score1 = db.Column(db.Integer, nullable=True)
    score2 = db.Column(db.Integer, nullable=True)
    table_number = db.Column(db.Integer)
    is_closed = db.Column(db.Boolean, default=False)  # Nouveau champ pour marquer les matchs terminés
    date = db.Column(db.String(20), nullable=True)

    def record_score(self, score1, score2):
        self.score1 = score1
        self.score2 = score2
        self.date = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        team1 = Team.query.get(self.team1_id)
        team2 = Team.query.get(self.team2_id)

        team1.matches_played += 1
        team2.matches_played += 1

        team1.points_for += score1
        team1.points_against += score2
        team2.points_for += score2
        team2.points_against += score1

        if score1 > score2:
            team1.points += 2
        elif score2 > score1:
            team2.points += 2
        else:
            team1.points += 1
            team2.points += 1

        db.session.commit()
