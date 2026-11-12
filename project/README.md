 Open PowerShell in the copied project folder and run:

   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   python -c "from API import app, db; app.app_context().push(); db.create_all()"
   python API.py


