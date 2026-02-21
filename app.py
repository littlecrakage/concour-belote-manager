# app.py
import os
import json
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_migrate import Migrate
from dotenv import load_dotenv
from sqlalchemy import and_
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')

# Load info panels configuration
def load_info_panels():
    try:
        with open(os.path.join(os.path.dirname(__file__), 'info_panels.json'), 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

info_panels = load_info_panels()

# Make info_panels available to all templates
@app.context_processor
def inject_info_panels():
    return dict(info_panels=info_panels)

@app.context_processor
def inject_tournament():
    """Make tournament available to all templates"""
    global tournament
    return dict(tournament=tournament if tournament else None)

db_url = os.environ.get("DATABASE_URL")

if db_url:
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        db_url
        .replace("postgres://", "postgresql+psycopg://", 1)
        .replace("postgresql://", "postgresql+psycopg://", 1)
    )

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

from extensions import db, login_manager

migrate = Migrate(app, db)  # Ajoutez cette ligne pour configurer Flask-Migrate


db.init_app(app)

from models.team import Team, Player
from models.match import Match
from models.tournament import Tournament
from models.user import User
from sqlalchemy.orm import aliased 

def get_tournament():
    """Get or create the main tournament"""
    tournament = Tournament.query.first()
    if not tournament:
        tournament = Tournament(ranking_system='points_sum', prevent_duplicate_matches=False)
        db.session.add(tournament)
        db.session.commit()
    return tournament

# Initialize tournament after app context
tournament = None

@app.before_request
def before_request():
    """Initialize tournament before each request"""
    global tournament
    # Always refresh tournament from database to get latest changes
    tournament = get_tournament()

# Configuration de Flask-Login
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('admin'))

        flash('Nom d\'utilisateur ou mot de passe incorrect.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('ranking'))


@app.route('/team/<int:team_id>', methods=['GET', 'POST'])
def team_detail(team_id):
    team = Team.query.get(team_id)
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
            return redirect(url_for('team_detail', team_id=team.id))
        elif 'remove_player' in request.form:
            player_name = request.form.get('player_name')
            if player_name:
                if team.remove_player(player_name):
                    flash(f"Le joueur {player_name} a été retiré de l'équipe {team.name} avec succès.", 'success')
                else:
                    flash(f"Impossible de retirer le joueur {player_name} de l'équipe {team.name}.", 'error')
            return redirect(url_for('team_detail', team_name=team.id))

    team_matches = []
    for match in Match.query.filter(Match.score1.isnot(None)).all():
        if match.team1_id == team.id or match.team2_id == team.id:
            opponent = match.team2 if match.team1_id == team.id else match.team1
            score1 = match.score1 if match.team1_id == team.id else match.score2
            score2 = match.score2 if match.team1_id == team.id else match.score1
            team_matches.append({
                'opponent': opponent.name,
                'score1': score1,
                'score2': score2,
                'date': match.date
            })

    return render_template('team_detail.html', team=team, matches=team_matches, is_admin=current_user.is_authenticated)


@app.route('/matches', methods=['GET', 'POST'])
def matches():
    if request.method == 'POST':
        if not current_user.is_authenticated:
            flash('Vous devez être connecté pour administrer le tournois.', 'error')
            return redirect(url_for('login'))
        
        if 'record_match' in request.form:
            match_id = request.form.get('match_id')
            if match_id:
                match = db.session.query(Match).get(match_id)
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
                    unplayed_matches.append({
                        'team1': match.team1.name,
                        'team2': match.team2.name,
                        'match_id': match.id
                    })

                played_matches = []
                for match in tournament.get_played_matches():
                    played_matches.append({
                        'team1': match.team1.name,
                        'team2': match.team2.name,
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
                        played_matches.append({
                            'team1': match.team1.name,
                            'team2': match.team2.name,
                            'score1': match.score1,
                            'score2': match.score2,
                            'date': match.date
                        })
                    
                    return render_template('matches.html', unplayed_matches=unplayed_matches, played_matches=played_matches, error=error)
                return redirect(url_for('matches'))

    # Récupérer les matchs non joués
    unplayed_matches = []
    matches = tournament.get_unplayed_matches()

    for index, match in enumerate(matches):
        unplayed_matches.append({
            'team1': match.team1.name,
            'team2': match.team2.name,
            'match_id': match.id,
            'table_number': match.table_number
        })

    # Récupérer les matchs joués
    played_matches = []
    for match in tournament.get_played_matches():
        played_matches.append({
            'team1': match.team1.name,
            'team2': match.team2.name,
            'score1': match.score1,
            'score2': match.score2,
            'table_number': match.table_number,
            'date': match.date

        })
    
    played_matches_sorted = sorted(played_matches, key=lambda x: x['date'], reverse=True)
    return render_template('matches.html', unplayed_matches=unplayed_matches, played_matches=played_matches_sorted, is_admin=current_user.is_authenticated, current_round = tournament.get_current_round())


@app.route('/ranking')
def ranking():
    global tournament
    
    # Récupérer le classement actuel
    teams = tournament.get_ranking() if tournament else Team.query.order_by(Team.points_for.desc()).all()

    # Récupérer les scores par tour
    teams_scores, round_numbers = tournament.get_scores_by_round() if tournament else ([], [])

    return render_template('ranking.html', teams=teams, teams_scores=teams_scores, round_numbers=round_numbers, tournament=tournament)


@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    global tournament
    
    if request.method == 'POST':
        if 'reset_tournament' in request.form:
            tournament.reset_tournament()
            flash("Le tournoi a été réinitialisé.", 'success')
            return redirect(url_for('admin'))

        elif 'start_tournament' in request.form:
            if len(tournament.get_teams()) % 2 != 0:
                flash("Le nombre d'équipes doit être pair pour commencer le tournoi.", 'error')
                return redirect(url_for('admin'))

            # Save prevent_duplicate_matches setting before starting
            prevent_duplicate = 'prevent_duplicate_matches' in request.form
            tournament_obj = Tournament.query.first()
            if tournament_obj:
                tournament_obj.prevent_duplicate_matches = prevent_duplicate
                db.session.commit()

            if not Match.query.first():
                if not tournament.generate_first_round_matches():
                    flash("Impossible de générer les matchs pour le premier tour.", 'error')
                    return redirect(url_for('admin'))
                flash("Les matchs du premier tour ont été générés aléatoirement avec succès.", 'success')
            else:
                if not tournament.generate_matches():
                    flash("Impossible de générer les matchs pour les tours suivants.", 'error')
                    return redirect(url_for('admin'))
                flash("Les matchs ont été générés selon le classement avec succès.", 'success')
            return redirect(url_for('matches'))

        elif 'add_team' in request.form:
            team_name = request.form.get('team_name')

            if not team_name:
                flash("Nom de l'equipe est obligatoires.", 'error')
                return redirect(url_for('admin'))

            if tournament.add_team(team_name):
                flash(f"L'équipe {team_name} a été ajoutée avec succès.", 'success')
            else:
                flash("Impossible d'ajouter l'équipe. Le tournoi a peut-être déjà commencé ou l'équipe existe déjà.", 'error')
            return redirect(url_for('admin'))
        
        elif 'remove_team' in request.form:
            team_name = request.form.get('remove_team')

            if not team_name:
                flash("Noms de l'équipe non spécifié.", 'error')
                return redirect(url_for('admin'))

            if tournament.remove_team(team_name):
                flash(f"L'équipe a été supprimée avec succès.", 'success')
            else:
                flash("Impossible de supprimer l'équipe. Le tournoi a peut-être déjà commencé ou l'équipe n'existe pas.", 'error')
            return redirect(url_for('admin'))
        
        elif 'update_settings' in request.form:
            ranking_system = request.form.get('ranking_system')
            if ranking_system in ['points_sum', 'soccer_style']:
                tournament_obj = Tournament.query.first()
                if tournament_obj:
                    tournament_obj.ranking_system = ranking_system
                    db.session.add(tournament_obj)
                    db.session.commit()
                    flash(f"Système de classement mis à jour.", 'success')
            return redirect(url_for('admin'))

    teams = tournament.get_teams()
    tournament_started = tournament.has_started()
    
    list_non_closed_matches = Match.query.filter(
        and_(
            Match.is_closed == False,
            Match.date.isnot(None)
        )
    ).all()
    matches_not_closed = []
    for match in list_non_closed_matches:
        matches_not_closed.append({
            'team1': match.team1.name,
            'team2': match.team2.name,
            'match_id': match.id
        })
    return render_template('admin.html', teams=teams, matches_not_closed=matches_not_closed, tournament=tournament, tournament_started=tournament_started)

@app.route('/update_match_result/<int:match_id>', methods=['POST'])
@login_required
def update_match_result(match_id):
    if request.method == 'POST':
        match = Match.query.get(match_id)
        score1 = int(request.form.get('score1'))
        score2 = int(request.form.get('score2'))
        if not match:
            flash("Match non trouvé.", 'error')
            return redirect(url_for('matches'))
        match.update_score(score1, score2)

    return redirect(url_for('matches'))  # Remplacez par le nom de votre route


@app.template_filter('get_item')
def get_item(dictionary, key):
    return dictionary.get(key, None)


if __name__ == '__main__':
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug)
