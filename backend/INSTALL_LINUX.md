# Backend – Installation on Linux

## Prerequisites
- **Python 3.11+** (use `python3 --version`)
- **git** (optional, for cloning)
- **make** (optional, for convenience scripts)
- **PostgreSQL** client libraries (`libpq-dev` on Debian/Ubuntu)

## Step‑by‑step
```bash
# 1. Clone the repo (if not already)
git clone https://github.com/yourusername/apivendas.git
cd apivendas/backend

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env – set at least the database URL and WhatsApp vars
nano .env

# 5. Start PostgreSQL (if using bundled binary)
./pgsql/pgsql/bin/postgres -D "$(pwd)/../pgsql/data" -p 5432 &
# Or use your system's PostgreSQL service

# 6. Apply migrations and create a superuser
python manage.py migrate
python manage.py createsuperuser

# 7. Run the development server
python manage.py runserver 0.0.0.0:8000
```
The API will be reachable at `http://localhost:8000/`.

## Tips for Linux
- Install `psycopg2-binary` if the native `psycopg2` fails: `pip install psycopg2-binary`.
- To stop the bundled PostgreSQL daemon: `pkill -f postgres`.
- For production, consider using a systemd service for PostgreSQL and a gunicorn/Uvicorn server for Django.
