import os
import subprocess
import sys

from app import create_app, db


def run_flask(args):
    env = os.environ.copy()
    env["FLASK_APP"] = "wsgi.py"
    result = subprocess.run(["flask", *args], env=env, check=False)
    return result.returncode


def main():
    if len(sys.argv) < 2:
        print("Usage: python manage.py <migrate|setup_production|collectstatic>")
        return 1

    command = sys.argv[1]

    if command == "migrate":
        # For fresh Railway environments using SQLite, historical Alembic
        # migrations can fail due ordering assumptions. Create current schema.
        app = create_app()
        with app.app_context():
            db.create_all()
        return 0
    if command == "setup_production":
        return run_flask(["seed"])
    if command == "collectstatic":
        # Flask app serves static files directly; no collection step required.
        return 0

    print(f"Unknown command: {command}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
