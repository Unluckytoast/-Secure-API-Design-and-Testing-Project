 Open PowerShell in the  project folder and run:

   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   python -c "from API import app, db; app.app_context().push(); db.create_all()"
   python API.py

Token Library
   .\.venv\Scripts\python.exe -m pip install Flask-JWT-Extended


This creates a temporary secret for that terminal session. Generating a new one later will invalidate existing tokens.
$env:JWT_SECRET_KEY = .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"


