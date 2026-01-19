# app.py
from flask import Flask, render_template, request, redirect, url_for, flash
from config import db

app = Flask(__name__)

import secrets
app.secret_key = "12343454565656565"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tournament.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

from models.team import Team
from models.match import Match
from models.tournament import Tournament
from sqlalchemy.orm import aliased 

tournament = Tournament()

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/teams', methods=['GET', 'POST'])
def teams():
    if request.method == 'POST':
        team_name = request.form.get('team_name')
        player1_name = request.form.get('player1_name')
        player2_name = request.form.get('player2_name')

        if team_name and player1_name and player2_name:
            if not tournament.add_team(team_name, player1_name, player2_name):
                error = "Impossible d'ajouter l'équipe : le tournoi a déjà commencé ou l'équipe existe déjà."
                return render_template('teams.html', teams=tournament.get_teams(), error=error)

        return redirect(url_for('teams'))

    return render_template('teams.html', teams=tournament.get_teams())



@app.route('/team/<team_name>', methods=['GET', 'POST'])
def team_detail(team_name):
    team = next((t for t in tournament.get_teams() if t.name == team_name), None)
    if not team:
        return redirect(url_for('teams'))

    if request.method == 'POST':
        player_name = request.form.get('player_name')
        if player_name and len(team.players) < 2:  # Vérifiez que l'équipe a moins de 2 joueurs
            if team.add_player(player_name):
                flash(f"Le joueur {player_name} a été ajouté à l'équipe {team.name} avec succès.", 'success')
            else:
                flash(f"Impossible d'ajouter le joueur {player_name} à l'équipe {team.name}.", 'error')
            return redirect(url_for('team_detail', team_name=team_name))

    # Filtrer les matchs joués par cette équipe
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
    error = None
    success = None
    if request.method == 'POST':
        if 'reset_tournament' in request.form:
            tournament.reset_tournament()
            return redirect(url_for('admin'))
        elif 'start_tournament' in request.form:
            if len(tournament.get_teams()) % 2 != 0:
                error = "Le nombre d'équipes doit être pair pour commencer le tournoi."
                return render_template('admin.html', teams=tournament.get_teams(), error=error)
            if not tournament.generate_matches():
                error = "Impossible de générer les matchs."
                return render_template('admin.html', teams=tournament.get_teams(), error=error)
            return redirect(url_for('matches'))
        elif 'remove_team' in request.form:
            remove_team = request.form.get('remove_team')
            if remove_team:
                if not tournament.remove_team(remove_team):
                    error = f"L'équipe {remove_team} a déjà joué des matchs et ne peut pas être retirée."
            return redirect(url_for('admin'))
        elif 'remove_player' in request.form:
            team_name = request.form.get('team_name')
            player_name = request.form.get('player_name')
            if team_name and player_name:
                result = tournament.remove_player_from_team(team_name, player_name)
                if not result:
                    flash(f"Impossible de retirer le joueur {player_name} de l'équipe {team_name}.", 'error')
                else:
                    flash(f"Le joueur {player_name} a été retiré de l'équipe {team_name} avec succès.", 'success')
            return redirect(url_for('admin'))

    # Recharger les équipes depuis la base de données
    teams = tournament.get_teams()
    return render_template('admin.html', teams=teams)


if __name__ == '__main__':
    app.run(debug=True)
