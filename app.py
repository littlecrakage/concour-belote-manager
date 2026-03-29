# app.py
from datetime import datetime, timedelta
import os
import json
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response
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

db_url = os.environ.get("DATABASE_URL")

if db_url:
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        db_url
        .replace("postgres://", "postgresql+psycopg2://", 1)
        .replace("postgresql://", "postgresql+psycopg2://", 1)
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

with app.app_context():
    db.create_all()

# Configuration de Flask-Login
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ── Auth decorator ────────────────────────────────────────────────────────────

from functools import wraps
def tournament_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        slug = kwargs.get('slug')
        tournament = Tournament.query.filter_by(slug=slug).first_or_404()
        if not current_user.is_authenticated:
            flash("Veuillez vous connecter.", 'error')
            return redirect(url_for('login', slug=slug))
        if current_user.tournament_id != tournament.id:
            flash("Accès refusé.", 'error')
            return redirect(url_for('login', slug=slug))
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def inject_globals():
    tournament = None  # default
    return dict(
        is_tournament_admin=is_tournament_admin,
        tournament=tournament
    )

@app.route('/', methods=['GET'])
def index():
    tournaments = Tournament.query.order_by(Tournament.created_at.desc()).all()
    return render_template('index.html', tournaments=tournaments)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            
            # If user is a tournament admin, redirect to their tournament
            if user.tournament_id:
                tournament = Tournament.query.get(user.tournament_id)
                if tournament:
                    return redirect(url_for('admin', slug=tournament.slug))
            
            # Future: regular users without a tournament go elsewhere
            return redirect(url_for('index'))

        flash("Nom d'utilisateur ou mot de passe incorrect.", 'error')

    return render_template('login.html')


@app.route('/logout')
def logout():
    # Grab tournament before logging out so we can redirect back to public page
    tournament = None
    if current_user.is_authenticated and current_user.tournament_id:
        tournament = Tournament.query.get(current_user.tournament_id)
    
    logout_user()
    
    if tournament:
        return redirect(url_for('ranking', slug=tournament.slug))
    return redirect(url_for('index'))


@app.route('/t/<slug>/team/<int:team_id>', methods=['GET', 'POST'])
def team_detail(team_id,slug):
    tournament = Tournament.query.filter_by(slug=slug).first_or_404()
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
            return redirect(url_for('team_detail', team_id=team.id, slug=slug))
        elif 'remove_player' in request.form:
            player_name = request.form.get('player_name')
            if player_name:
                if team.remove_player(player_name):
                    flash(f"Le joueur {player_name} a été retiré de l'équipe {team.name} avec succès.", 'success')
                else:
                    flash(f"Impossible de retirer le joueur {player_name} de l'équipe {team.name}.", 'error')
            return redirect(url_for('team_detail', team_id=team.id, slug=slug))

    team_matches = []
    for match in Match.query.filter(
        Match.tournament_id == tournament.id,
        Match.score1.isnot(None)).all():
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

    return render_template('team_detail.html',
    tournament=tournament,
    team=team,
    matches=team_matches
)


@app.route('/t/<slug>/matches', methods=['GET', 'POST'])
def matches(slug):
    tournament = Tournament.query.filter_by(slug=slug).first_or_404()
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
                return redirect(url_for('matches', slug=slug))
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

                return render_template('matches.html', tournament=tournament,  unplayed_matches=unplayed_matches, played_matches=played_matches, error=error, verify_belote_scores=tournament.verify_belote_scores)
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

                    return render_template('matches.html', tournament=tournament, unplayed_matches=unplayed_matches, played_matches=played_matches, error=error, verify_belote_scores=tournament.verify_belote_scores)
                return redirect(url_for('matches', slug=slug))

    # Récupérer les matchs non joués
    unplayed_matches = []
    matches = tournament.get_unplayed_matches()
    print(f"DEBUG tournament id: {tournament.id}")
    print(f"DEBUG unplayed matches from db: {matches}")
    print(f"DEBUG count: {len(matches)}")

    for index, match in enumerate(matches):
        print(f"DEBUG match {index}: {match.id}, team1: {match.team1_id}, team2: {match.team2_id}, score1: {match.score1}")
        unplayed_matches.append({
            'team1': match.team1.name,
            'team2': match.team2.name,
            'team1_id': match.team1.id,
            'team2_id': match.team2.id,
            'match_id': match.id,
            'table_number': match.table_number
        })
    print(f"DEBUG unplayed_matches list: {unplayed_matches}")

    # Récupérer les matchs joués
    played_matches = []
    for match in tournament.get_played_matches():
        played_matches.append({
            'team1': match.team1.name,
            'team2': match.team2.name,
            'team1_id': match.team1.id,
            'team2_id': match.team2.id,
            'score1': match.score1,
            'score2': match.score2,
            'table_number': match.table_number,
            'date': match.date
        })
    
    played_matches_sorted = sorted(played_matches, key=lambda x: x['date'], reverse=True)
    return render_template('matches.html',
    tournament=tournament,
    unplayed_matches=unplayed_matches,
    played_matches=played_matches_sorted,
    current_round=tournament.get_current_round(),
    verify_belote_scores=tournament.verify_belote_scores
)

@app.route('/t/<slug>/ranking')
def ranking(slug):
    tournament = Tournament.query.filter_by(slug=slug).first_or_404()

    teams = tournament.get_ranking()
    teams_scores, round_numbers = tournament.get_scores_by_round()

    return render_template('ranking.html',
                           tournament=tournament,
                           teams=teams,
                           teams_scores=teams_scores,
                           round_numbers=round_numbers)


@app.route('/t/<slug>/admin', methods=['GET', 'POST'])
@tournament_admin_required
def admin(slug):
    tournament = Tournament.query.filter_by(slug=slug).first_or_404()

    if request.method == 'POST':
        if 'reset_tournament' in request.form:
            tournament.reset_tournament()
            flash("Le tournoi a été réinitialisé.", 'success')
            return redirect(url_for('admin', slug=slug))

        elif 'start_tournament' in request.form:
            if len(tournament.get_teams()) % 2 != 0:
                flash("Le nombre d'équipes doit être pair pour commencer le tournoi.", 'error')
                return redirect(url_for('admin', slug=slug))

            prevent_duplicate = 'prevent_duplicate_matches' in request.form
            tournament.prevent_duplicate_matches = prevent_duplicate
            tournament.verify_belote_scores = 'verify_belote_scores' in request.form
            pairing_system = request.form.get('pairing_system', 'ranked')
            if pairing_system in ('ranked', 'random'):
                tournament.pairing_system = pairing_system
            db.session.commit()

            if not Match.query.filter_by(tournament_id=tournament.id).first():
                if not tournament.generate_first_round_matches():
                    flash("Impossible de générer les matchs pour le premier tour.", 'error')
                    return redirect(url_for('admin', slug=slug))
                flash("Les matchs du premier tour ont été générés aléatoirement avec succès.", 'success')
            else:
                flash("Le premier tour a deja été lancé", 'error')
                return redirect(url_for('admin', slug=slug))
            return redirect(url_for('matches', slug=slug))

        elif 'add_team' in request.form:
            team_name = request.form.get('team_name')
            if not team_name:
                flash("Nom de l'equipe est obligatoires.", 'error')
                return redirect(url_for('admin', slug=slug))

            if tournament.add_team(team_name):
                new_team = Team.query.filter_by(name=team_name, tournament_id=tournament.id).first()
                flash(f"L'équipe {team_name} (N°{new_team.id}) a été ajoutée avec succès.", 'success')
            else:
                flash("Impossible d'ajouter l'équipe. Le tournoi a peut-être déjà commencé ou l'équipe existe déjà.", 'error')
            return redirect(url_for('admin', slug=slug))

        elif 'remove_team' in request.form:
            team_id = request.form.get('remove_team')  # ← was 'team_id'
            if not team_id:
                flash("Équipe non spécifiée.", 'error')
                return redirect(url_for('admin', slug=slug))

            if tournament.remove_team(team_id):
                flash("L'équipe a été supprimée avec succès.", 'success')
            else:
                flash("Impossible de supprimer l'équipe.", 'error')
            return redirect(url_for('admin', slug=slug))


        elif 'update_settings' in request.form:
            ranking_system = request.form.get('ranking_system')
            if ranking_system in ['points_sum', 'soccer_style']:
                tournament.ranking_system = ranking_system
                db.session.commit()
                flash("Système de classement mis à jour.", 'success')
            return redirect(url_for('admin', slug=slug))

    teams = tournament.get_teams()
    tournament_started = Match.query.filter_by(tournament_id=tournament.id).first() is not None

    list_non_closed_matches = Match.query.filter(
        and_(
            Match.is_closed == False,
            Match.date.isnot(None),
            Match.tournament_id == tournament.id
        )
    ).all()
    matches_not_closed = [
        {
            'team1': match.team1.name,
            'team2': match.team2.name,
            'match_id': match.id
        }
        for match in list_non_closed_matches
    ]

    return render_template('admin.html',
                           tournament=tournament,
                           teams=teams,
                           matches_not_closed=matches_not_closed,
                           tournament_started=tournament_started)

@app.route('/t/<slug>/update_match_result/<int:match_id>', methods=['POST'])
@tournament_admin_required
def update_match_result(slug, match_id):
    tournament = Tournament.query.filter_by(slug=slug).first_or_404()
    match = Match.query.filter_by(id=match_id, tournament_id=tournament.id).first()
    if not match:
        flash("Match non trouvé.", 'error')
        return redirect(url_for('matches', slug=slug))
    score1 = int(request.form.get('score1'))
    score2 = int(request.form.get('score2'))
    match.update_score(score1, score2)
    return redirect(url_for('matches', slug=slug))


@app.route('/new-tournament', methods=['GET', 'POST'])
def new_tournament():
    if request.method == 'POST':
        name = request.form.get('name')
        slug = request.form.get('slug').lower().strip()
        admin_username = request.form.get('admin_username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Validation
        if not all([name, slug, admin_username, password]):
            flash("Tous les champs sont obligatoires.", 'error')
            return render_template('new_tournament.html')

        if password != confirm_password:
            flash("Les mots de passe ne correspondent pas.", 'error')
            return render_template('new_tournament.html')

        if Tournament.query.filter_by(slug=slug).first():
            flash("Cet identifiant de tournoi est déjà pris.", 'error')
            return render_template('new_tournament.html')

        if User.query.filter_by(username=admin_username).first():
            flash("Ce nom d'utilisateur est déjà pris.", 'error')
            return render_template('new_tournament.html')

        # Create tournament first
        tournament = Tournament(
            slug=slug,
            name=name,
            ranking_system='points_sum',
            prevent_duplicate_matches=False
        )
        db.session.add(tournament)
        db.session.flush()  # get tournament.id without full commit

        # Create linked admin user
        admin_user = User(
            username=admin_username,
            tournament_id=tournament.id
        )
        admin_user.set_password(password)
        db.session.add(admin_user)
        db.session.commit()

        flash(f"Tournoi '{name}' créé avec succès!", 'success')
        return redirect(url_for('login', slug=slug))

    return render_template('new_tournament.html')

# ── Helpers ───────────────────────────────────────────────────────────────────

def is_tournament_admin(tournament):
    if tournament is None:   
        return False
    return (
        current_user.is_authenticated and
        current_user.tournament_id == tournament.id
    )


@app.template_filter('get_item')
def get_item(dictionary, key):
    return dictionary.get(key, None)


# ── Export ─────────────────────────────────────────────────────────────────────

@app.route('/t/<slug>/export/json')
def export_json(slug):
    """Export the full tournament state as a downloadable JSON file."""
    tournament = Tournament.query.filter_by(slug=slug).first_or_404()
    teams = tournament.get_ranking()
    played_matches = tournament.get_played_matches()
    teams_scores, round_numbers = tournament.get_scores_by_round()

    # Build team data
    teams_data = []
    for rank, team in enumerate(teams, start=1):
        team_dict = {
            'rank': rank,
            'name': team.name,
            'players': [p.name for p in team.players],
            'matches_played': team.matches_played,
            'points_for': team.points_for,
            'points_against': team.points_against,
            'point_difference': team.points_for - team.points_against,
        }
        if tournament.ranking_system == 'soccer_style':
            team_dict['soccer_points'] = getattr(team, 'soccer_points', 0)
        teams_data.append(team_dict)

    # Build match history
    matches_data = []
    for match in sorted(played_matches, key=lambda m: (m.round_number or 0, m.id)):
        matches_data.append({
            'round': match.round_number,
            'table': match.table_number,
            'team1': match.team1.name,
            'team2': match.team2.name,
            'score1': match.score1,
            'score2': match.score2,
            'date': match.date,
        })

    export = {
        'tournament': {
            'name': tournament.name,
            'slug': tournament.slug,
            'ranking_system': tournament.ranking_system,
            'created_at': tournament.created_at.isoformat() if tournament.created_at else None,
            'total_rounds': tournament.get_current_round(),
        },
        'ranking': teams_data,
        'matches': matches_data,
        'exported_at': datetime.utcnow().isoformat(),
    }

    json_str = json.dumps(export, ensure_ascii=False, indent=2)
    return Response(
        json_str,
        mimetype='application/json',
        headers={'Content-Disposition': f'attachment; filename="tournoi-{tournament.slug}.json"'}
    )


@app.route('/t/<slug>/export')
def export_html(slug):
    """Render a self-contained printable HTML page with the full tournament state."""
    tournament = Tournament.query.filter_by(slug=slug).first_or_404()
    teams = tournament.get_ranking()
    played_matches = tournament.get_played_matches()
    teams_scores, round_numbers = tournament.get_scores_by_round()

    # Sort matches by round then table
    played_matches_sorted = sorted(played_matches, key=lambda m: (m.round_number or 0, m.table_number or 0))

    return render_template('export.html',
                           tournament=tournament,
                           teams=teams,
                           teams_scores=teams_scores,
                           round_numbers=round_numbers,
                           played_matches=played_matches_sorted)

@app.cli.command("cleanup_expired")
def cleanup_expired():
    """Delete tournaments older than 2 weeks."""
    from models.tournament import Tournament
    expired = Tournament.query.filter(
        Tournament.created_at < datetime.timezone.utc - timedelta(weeks=2)
    ).all()
    
    count = len(expired)
    for tournament in expired:
        db.session.delete(tournament)
    
    db.session.commit()
    print(f"Deleted {count} expired tournaments.")


if __name__ == '__main__':
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug)
