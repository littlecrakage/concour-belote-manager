# Concour Belote Manager

A web application to organize and manage Belote card game tournaments. This tool helps organizers create teams, manage matches, track scores, and view real-time rankings.

## Features

- **Team Management**: Create and manage teams participating in the tournament
- **Match Organization**: Automatically generate match pairings and assign table numbers
- **Score Tracking**: Record match results and update team statistics in real-time
- **Live Ranking**: View current standings with points, wins, and point differentials
- **User Authentication**: Secure login system for tournament administrators
- **Match History**: Track all played and unplayed matches throughout the tournament
- **Configurable Tournament**: Choose between different ranking systems
- **Info Panels**: Customizable information panels via JSON configuration

## Tech Stack

- **Backend**: Flask (Python)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Authentication**: Flask-Login
- **Database Migrations**: Flask-Migrate (Alembic)
- **Templating**: Jinja2
- **Deployment**: Gunicorn (production server)

---

## Installation

### Prerequisites

- **Python 3.9+** (check with `python --version`)
- **PostgreSQL** database installed and running
- **pip** (Python package manager)

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd concour-belote-manager
```

### Step 2: Create a Virtual Environment (Recommended)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

Create a `.env` file in the project root with the following variables:

```env
SECRET_KEY=your_secret_key_here
DATABASE_URL=postgresql://username:password@localhost:5432/concour_belote
FLASK_DEBUG=True
```

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | A secure random string for session encryption |
| `DATABASE_URL` | PostgreSQL connection string |
| `FLASK_DEBUG` | Set to `True` for development, `False` for production |

> **Tip**: Generate a secure secret key with: `python -c "import secrets; print(secrets.token_hex(32))"`

### Step 5: Set Up the Database

1. **Create the PostgreSQL database**:
   ```bash
   # Connect to PostgreSQL
   psql -U postgres
   
   # Create database
   CREATE DATABASE concour_belote;
   \q
   ```

2. **Initialize and migrate the database**:
   ```bash
   python init_db.py
   flask db upgrade
   ```

### Step 6: Create an Admin User

The application doesn't have a registration page. Create an admin user using the provided script:

```bash
python create_user.py
```

Or manually via Python (with SHA256 password encryption):

```bash
python
>>> from app import app, db
>>> from models.user import User
>>> from werkzeug.security import generate_password_hash
>>> with app.app_context():
...     hashed_password = generate_password_hash('your_secure_password', method='sha256')
...     user = User(username='admin', password=hashed_password)
...     db.session.add(user)
...     db.session.commit()
>>> exit()
```

> **Important**: Always use `generate_password_hash()` to encrypt passwords. Never store plain text passwords in the database.

### Step 7: Run the Application

**Development mode:**
```bash
python app.py
```

**Production mode (with Gunicorn):**
```bash
gunicorn app:app
```

The application will be available at **http://localhost:5000**

---

## Usage

### Getting Started

1. **Login**: Navigate to `/login` and enter your admin credentials
2. **Access Admin Panel**: After login, you'll be redirected to the admin panel

### Managing a Tournament

1. **Add Teams**: Create teams with their player names
2. **Generate Matches**: Use the admin panel to create match pairings for each round
3. **Assign Tables**: Matches are automatically assigned table numbers
4. **Record Scores**: Enter scores for completed matches
5. **View Rankings**: Check the live standings at `/ranking`

### Pages Overview

| Page | URL | Description |
|------|-----|-------------|
| Home | `/` | Welcome page and quick access |
| Login | `/login` | Admin authentication |
| Admin | `/admin` | Tournament management panel |
| Matches | `/matches` | View all matches by round |
| Ranking | `/ranking` | Live tournament standings |
| Team Detail | `/team/<id>` | Individual team statistics |

---

## Configuration

### Info Panels

Customize information panels displayed on pages by editing `info_panels.json`:

```json
{
  "panel_name": {
    "title": "Panel Title",
    "content": "Panel content here"
  }
}
```

See `INFO_PANELS_README.md` for detailed configuration options.

### Tournament Settings

Tournament settings (ranking system, duplicate match prevention) can be configured through the admin interface or directly in the database.

---

## Project Structure

```
concour-belote-manager/
├── app.py                 # Main Flask application
├── config.py              # Configuration settings
├── extensions.py          # Flask extensions initialization
├── init_db.py             # Database initialization script
├── create_user.py         # Admin user creation script
├── info_panels.json       # Info panels configuration
├── requirements.txt       # Python dependencies
├── Procfile               # Heroku deployment configuration
├── runtime.txt            # Python version for deployment
├── migrations/            # Database migration files (Alembic)
├── models/                # SQLAlchemy model definitions
│   ├── tournament.py      # Tournament model and logic
│   ├── match.py           # Match model
│   ├── team.py            # Team and Player models
│   └── user.py            # User authentication model
└── templates/             # HTML templates (Jinja2)
    ├── base.html          # Base template
    ├── index.html         # Home page
    ├── login.html         # Login page
    ├── admin.html         # Admin panel
    ├── matches.html       # Matches display
    ├── ranking.html       # Tournament standings
    └── team_detail.html   # Team details
```

---

## Database Models

| Model | Description |
|-------|-------------|
| **User** | Administrator accounts for authentication |
| **Team** | Teams with player information and statistics |
| **Match** | Match records with scores, rounds, and table assignments |
| **Tournament** | Tournament configuration and settings |

---

## Deployment

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | Yes | Flask secret key for sessions |
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `FLASK_DEBUG` | No | Enable debug mode (default: False) |

---

## Troubleshooting

### Common Issues

**Database connection error:**
- Verify PostgreSQL is running
- Check your `DATABASE_URL` format
- Ensure the database exists

**Migration errors:**
```bash
flask db stamp head
flask db migrate
flask db upgrade
```

**Missing dependencies:**
```bash
pip install -r requirements.txt --upgrade
```

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
