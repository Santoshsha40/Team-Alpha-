# CampusLoop

CampusLoop is a student-to-student borrowing board. The API serves the
frontend, so both parts run together.

## Start the project

Start the project from the `backend` folder:

```powershell
cd backend
python -m uvicorn main:app --reload --port 8000
```

Open `http://localhost:8000` in your browser. A small SQLite database is
created automatically the first time the API starts.

The demo login is:

- Email: `studenta@campus.edu`
- Password: `Student123!`

The API endpoint list is available at `http://localhost:8000/docs`.

