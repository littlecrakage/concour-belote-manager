# app.py
from flask import Flask, render_template, request, redirect, url_for, flash
from config import db
from flask_migrate import Migrate

app = Flask(__name__)

import secrets
app.secret_key = "12343454565656565"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tournament.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

migrate = Migrate(app, db)  # Ajoutez cette ligne pour configurer Flask-Migrate


db.init_app(app)

from models.team import Team, Player
from models.match import Match
from models.tournament import Tournament
from sqlalchemy.orm import aliased 

tournament = Tournament()

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/team/<team_name>', methods=['GET', 'POST'])
def team_detail(team_name):
    team = Team.query.filter_by(name=team_name).first()
    if not team:
        return redirect(url_for('admin'))

    if request.method == 'POST':
        if 'add_player' in request.form:
            player_name = request.form.get('player_name')
            if player_name and len(team.players) < 2:
                if team.add_player(player_name):
                    flash(f"Le joueur {player_name} a été ajouté à l'équipe {team.name} avec succès.", 'success')
                else:
                    flash(f"Impossible d'ajouter le joueur {player_name} à l'équipe {team.name}.", 'error')
            else:
                flash(f"L'équipe a déjà 2 joueurs.", 'error')
            return redirect(url_for('team_detail', team_name=team_name))
        elif 'remove_player' in request.form:
            player_name = request.form.get('player_name')
            if player_name:
                if team.remove_player(player_name):
                    flash(f"Le joueur {player_name} a été retiré de l'équipe {team.name} avec succès.", 'success')
                else:
                    flash(f"Impossible de retirer le joueur {player_name} de l'équipe {team.name}.", 'error')
            return redirect(url_for('team_detail', team_name=team_name))

    team_matches = []
    for match in Match.query.filter(Match.score1.isnot(None)).all():
        if match.team1_id == team.id or match.team2_id == team.id:
            opponent_id = match.team2_id if match.team1_id == team.id else match.team1_id
            opponent = Team.query.get(opponent_id)
            score1 = match.score1 if match.team1_id == team.id else match.score2
            score2 = match.score2 if match.team1_id == team.id else match.score1
            team_matches.append({
                'opponent': opponent.name,
                'score1': score1,
                'score2': score2,
                'date': match.date
            })

    return render_template('team_detail.html', team=team, matches=team_matches)






@app.route('/matches', methods=['GET', 'POST'])
def matches():
    if request.method == 'POST':
        if 'record_match' in request.form:
            match_text = request.form.get('match')
            if match_text:
                team1_name, team2_name = match_text.split(" vs ")
                Team1 = aliased(Team, name='team1')
                Team2 = aliased(Team, name='team2')
                match = db.session.query(Match).join(Team1, Match.team1_id == Team1.id).join(Team2, Match.team2_id == Team2.id).filter(
                    Team1.name == team1_name,
                    Team2.name == team2_name,
                    Match.score1.is_(None)
                ).first()
                score1 = int(request.form.get('score1'))
                score2 = int(request.form.get('score2'))
                if match:
                    match.record_score(score1, score2)
                return redirect(url_for('matches'))
        elif 'generate_next_round' in request.form:
            if tournament.has_unplayed_matches():
                error = "Il reste des matchs non joués. Veuillez enregistrer tous les résultats avant de générer le prochain tour."
                unplayed_matches = []
                for match in tournament.get_unplayed_matches():
                    team1 = Team.query.get(match.team1_id)
                    team2 = Team.query.get(match.team2_id)
                    unplayed_matches.append({
                        'team1': team1.name,
                        'team2': team2.name,
                        'match_id': match.id
                    })

                played_matches = []
                for match in tournament.get_played_matches():
                    team1 = Team.query.get(match.team1_id)
                    team2 = Team.query.get(match.team2_id)
                    played_matches.append({
                        'team1': team1.name,
                        'team2': team2.name,
                        'score1': match.score1,
                        'score2': match.score2,
                        'date': match.date
                    })

                return render_template('matches.html', unplayed_matches=unplayed_matches, played_matches=played_matches, error=error)
            else:
                if not tournament.generate_next_round():
                    error = "Impossible de générer le prochain tour."
                    unplayed_matches = []
                    played_matches = []
                    for match in tournament.get_played_matches():
                        team1 = Team.query.get(match.team1_id)
                        team2 = Team.query.get(match.team2_id)
                        played_matches.append({
                            'team1': team1.name,
                            'team2': team2.name,
                            'score1': match.score1,
                            'score2': match.score2,
                            'date': match.date
                        })
                    return render_template('matches.html', unplayed_matches=unplayed_matches, played_matches=played_matches, error=error)
                return redirect(url_for('matches'))

    # Récupérer les matchs non joués
    unplayed_matches = []
    for match in tournament.get_unplayed_matches():
        team1 = Team.query.get(match.team1_id)
        team2 = Team.query.get(match.team2_id)
        unplayed_matches.append({
            'team1': team1.name,
            'team2': team2.name,
            'match_id': match.id
        })

    # Récupérer les matchs joués
    played_matches = []
    for match in tournament.get_played_matches():
        team1 = Team.query.get(match.team1_id)
        team2 = Team.query.get(match.team2_id)
        played_matches.append({
            'team1': team1.name,
            'team2': team2.name,
            'score1': match.score1,
            'score2': match.score2,
            'date': match.date
        })

    return render_template('matches.html', unplayed_matches=unplayed_matches, played_matches=played_matches)

@app.route('/ranking')
def ranking():
    sorted_teams = tournament.get_ranking()
    return render_template('ranking.html', teams=sorted_teams)


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        if 'reset_tournament' in request.form:
            tournament.reset_tournament()
            flash("Le tournoi a été réinitialisé.", 'success')
            return redirect(url_for('admin'))
        elif 'start_tournament' in request.form:
            if len(tournament.get_teams()) % 2 != 0:
                flash("Le nombre d'équipes doit être pair pour commencer le tournoi.", 'error')
                return redirect(url_for('admin'))

            # Vérifiez si c'est le premier tour
            if not Match.query.first():
                # Premier tour : matchs aléatoires
                if not tournament.generate_first_round_matches():
                    flash("Impossible de générer les matchs pour le premier tour.", 'error')
                    return redirect(url_for('admin'))
                flash("Les matchs du premier tour ont été générés aléatoirement avec succès.", 'success')
            else:
                # Tours suivants : matchs selon le classement
                if not tournament.generate_matches():
                    flash("Impossible de générer les matchs pour les tours suivants.", 'error')
                    return redirect(url_for('admin'))
                flash("Les matchs ont été générés selon le classement avec succès.", 'success')
            return redirect(url_for('matches'))

    teams = tournament.get_teams()
    return render_template('admin.html', teams=teams)



if __name__ == '__main__':
    app.run(debug=True)
