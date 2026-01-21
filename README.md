# Concour Belote Manager

A web application to organize and manage Belote card game tournaments. This tool helps organizers create teams, manage matches, track scores, and view real-time rankings.

## Features

- **Team Management**: Create and manage teams participating in the tournament
- **Match Organization**: Automatically generate match pairings and assign table numbers
- **Score Tracking**: Record match results and update team statistics in real-time
- **Live Ranking**: View current standings with points, wins, and point differentials
- **User Authentication**: Secure login system for tournament administrators
- **Match History**: Track all played and unplayed matches throughout the tournament
- **Database Persistence**: SQLAlchemy ORM with PostgreSQL support

## Tech Stack

- **Backend**: Flask (Python web framework)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Authentication**: Flask-Login
- **Database Migrations**: Flask-Migrate (Alembic)
- **Templating**: Jinja2
- **Deployment**: Gunicorn (production server)

## Installation

### Prerequisites
- Python 3.7+
- PostgreSQL database
- pip (Python package manager)

### Setup

1. Clone or download the project

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file with your configuration:
   ```
   SECRET_KEY=your_secret_key_here
   DATABASE_URL=postgresql://username:password@localhost/concour_belote
   FLASK_ENV=production
   ```

4. Initialize the database:
   ```bash
   python init_db.py
   ```

5. Apply migrations:
   ```bash
   flask db upgrade
   ```

6. Create an administrator user in the database:
   ```bash
   python
   >>> from app import app, db
   >>> from models.user import User
   >>> with app.app_context():
   ...     user = User(username='admin', password='your_password')
   ...     db.session.add(user)
   ...     db.session.commit()
   >>> exit()
   ```
   
   **Note**: The application does not provide a registration method. You must manually create users in the database using the above method.

7. Run the application:
   ```bash
   python app.py
   ```

   Or for production:
   ```bash
   gunicorn app:app
   ```

The application will be available at `http://localhost:5000`

## Usage

1. **Login**: Access the application and log in with your administrator credentials
2. **Add Teams**: Create teams that will participate in the tournament
3. **Create Matches**: Generate match pairings between teams
4. **Record Scores**: Input match results and scores
5. **View Rankings**: Monitor the tournament standings in real-time

## Project Structure

```
concour-belote-manager/
├── app.py                 # Main Flask application
├── config.py             # Configuration settings
├── extensions.py         # Flask extensions initialization
├── init_db.py            # Database initialization script
├── models.py             # Data models
├── requirements.txt      # Python dependencies
├── Procfile             # Heroku deployment configuration
├── migrations/          # Database migration files (Alembic)
├── models/              # SQLAlchemy model definitions
│   ├── tournament.py    # Tournament logic
│   ├── match.py         # Match model
│   ├── team.py          # Team and player models
│   └── user.py          # User authentication model
└── templates/           # HTML templates
    ├── base.html        # Base template
    ├── index.html       # Home page
    ├── login.html       # Login page
    ├── teams.html       # Teams management
    ├── matches.html     # Matches display
    ├── ranking.html     # Tournament standings
    ├── team_detail.html # Individual team details
    └── admin.html       # Admin panel
```

## Database Models

- **User**: Administrator accounts for tournament management
- **Team**: Teams participating in the tournament
- **Match**: Individual match records with scores and table assignments
- **Tournament**: Overall tournament logic and scoring

## Deployment

This application is ready for deployment on Heroku or similar platforms using the `Procfile` and `runtime.txt` configuration files.

### Environment Variables Required

- `SECRET_KEY`: Flask secret key for session management
- `DATABASE_URL`: PostgreSQL connection string

## License

All rights reserved.

## Support

For issues or questions about this application, please contact the development team.
