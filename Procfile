web: FLASK_APP=wsgi.py flask seed && gunicorn wsgi:app --bind 0.0.0.0:${PORT:-5000}
