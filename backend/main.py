from datetime import date, datetime, timezone
from pathlib import Path
import sqlite3
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator


DATABASE_PATH = Path(__file__).with_name("campusloop.db")
DEMO_EMAIL = "studenta@campus.edu"
DEMO_PASSWORD = "Student123!"
DEMO_TOKEN = "campusloop-demo-token"

app = FastAPI(title="CampusLoop API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8001",
        "http://127.0.0.1:8001",
        "null",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LoginPayload(BaseModel):
    email: str
    password: str


class ResourcePayload(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(min_length=2, max_length=500)
    category_id: int
    condition: str = Field(default="GOOD", max_length=30)
    pickup_location: str = Field(min_length=2, max_length=160)
    optional_deposit: float = Field(default=0, ge=0)


class BorrowRequestPayload(BaseModel):
    resource_id: int
    requested_from: date
    requested_until: date
    message: str = Field(default="No note added", max_length=500)

    @field_validator("requested_until")
    @classmethod
    def end_date_must_follow_start(cls, value: date, info):
        start_date = info.data.get("requested_from")
        if start_date and value < start_date:
            raise ValueError("requested_until must be on or after requested_from")
        return value


def connect_db() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def initialize_database() -> None:
    with connect_db() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                full_name TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS categories (
                category_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS resources (
                resource_id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER NOT NULL REFERENCES users(user_id),
                category_id INTEGER NOT NULL REFERENCES categories(category_id),
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                condition TEXT NOT NULL,
                pickup_location TEXT NOT NULL,
                optional_deposit REAL NOT NULL DEFAULT 0,
                availability_status TEXT NOT NULL DEFAULT 'AVAILABLE',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS borrow_requests (
                request_id INTEGER PRIMARY KEY AUTOINCREMENT,
                resource_id INTEGER NOT NULL REFERENCES resources(resource_id),
                requester_id INTEGER NOT NULL REFERENCES users(user_id),
                requested_from TEXT NOT NULL,
                requested_until TEXT NOT NULL,
                message TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'PENDING',
                created_at TEXT NOT NULL
            );
            """
        )

        user = connection.execute(
            "SELECT user_id FROM users WHERE email = ?", (DEMO_EMAIL,)
        ).fetchone()
        if user is None:
            connection.execute(
                "INSERT INTO users (email, password, full_name) VALUES (?, ?, ?)",
                (DEMO_EMAIL, DEMO_PASSWORD, "Santosh Shah"),
            )
        connection.execute(
            "INSERT OR IGNORE INTO users (email, password, full_name) VALUES (?, ?, ?)",
            ("studentb@campus.edu", "Student123!", "Maya Patel"),
        )

        category_names = ["Study", "Tech", "Outdoors", "Creative"]
        for category_name in category_names:
            connection.execute(
                "INSERT OR IGNORE INTO categories (name, description) VALUES (?, ?)",
                (category_name, f"{category_name} items shared by students"),
            )

        resource_count = connection.execute(
            "SELECT COUNT(*) AS count FROM resources"
        ).fetchone()["count"]
        if resource_count == 0:
            owner_id = connection.execute(
                "SELECT user_id FROM users WHERE email = ?", ("studentb@campus.edu",)
            ).fetchone()["user_id"]
            categories = {
                row["name"]: row["category_id"]
                for row in connection.execute("SELECT category_id, name FROM categories")
            }
            seed_resources = [
                ("Scientific Calculator", "Reliable calculator for exams and lab work.", "Study", "Engineering library", "GOOD"),
                ("Graph Paper Pack", "A fresh pack of graph paper for problem sets.", "Study", "Student union desk", "GOOD"),
                ("USB-C Charger", "65W charger with a two-metre cable.", "Tech", "North residence lobby", "GOOD"),
                ("Instant Camera", "Includes a partial pack of film.", "Creative", "Arts building, room 104", "GOOD"),
                ("Camping Stove", "Compact stove for weekend trips.", "Outdoors", "Sports centre entrance", "GOOD"),
                ("Noise Cancelling Headphones", "Comfortable over-ear headphones.", "Tech", "Science quad cafe", "GOOD"),
            ]
            connection.executemany(
                """INSERT INTO resources
                (owner_id, category_id, name, description, condition, pickup_location, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                [
                    (owner_id, categories[category], name, description, condition, location, now())
                    for name, description, category, location, condition in seed_resources
                ],
            )


def current_user(authorization: Optional[str] = Header(default=None)) -> sqlite3.Row:
    if authorization != f"Bearer {DEMO_TOKEN}":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in required")
    with connect_db() as connection:
        user = connection.execute(
            "SELECT * FROM users WHERE email = ?", (DEMO_EMAIL,)
        ).fetchone()
    if user is None:
        raise HTTPException(status_code=401, detail="User account not found")
    return user


def resource_response(row: sqlite3.Row) -> dict:
    return {
        "resource_id": row["resource_id"],
        "owner_id": row["owner_id"],
        "owner_name": row["owner_name"],
        "category_id": row["category_id"],
        "category_name": row["category_name"],
        "name": row["name"],
        "description": row["description"],
        "condition": row["condition"],
        "pickup_location": row["pickup_location"],
        "optional_deposit": row["optional_deposit"],
        "availability_status": row["availability_status"],
        "created_at": row["created_at"],
    }


RESOURCE_QUERY = """
    SELECT r.*, u.full_name AS owner_name, c.name AS category_name
    FROM resources r
    JOIN users u ON u.user_id = r.owner_id
    JOIN categories c ON c.category_id = r.category_id
"""


@app.on_event("startup")
def on_startup() -> None:
    initialize_database()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/v1/auth/login")
def login(payload: LoginPayload) -> dict:
    with connect_db() as connection:
        user = connection.execute(
            "SELECT * FROM users WHERE email = ? AND password = ?",
            (payload.email, payload.password),
        ).fetchone()
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {
        "access_token": DEMO_TOKEN,
        "token_type": "bearer",
        "user_id": user["user_id"],
        "full_name": user["full_name"],
    }


@app.get("/api/v1/resources/categories")
def list_categories() -> list[dict]:
    with connect_db() as connection:
        rows = connection.execute(
            "SELECT category_id, name, description FROM categories ORDER BY category_id"
        ).fetchall()
    return [dict(row) for row in rows]


@app.get("/api/v1/resources")
def list_resources() -> list[dict]:
    with connect_db() as connection:
        rows = connection.execute(
            RESOURCE_QUERY + " ORDER BY r.created_at DESC"
        ).fetchall()
    return [resource_response(row) for row in rows]


@app.post("/api/v1/resources", status_code=201)
def create_resource(payload: ResourcePayload, user: sqlite3.Row = Depends(current_user)) -> dict:
    with connect_db() as connection:
        category = connection.execute(
            "SELECT category_id FROM categories WHERE category_id = ?", (payload.category_id,)
        ).fetchone()
        if category is None:
            raise HTTPException(status_code=400, detail="Category not found")
        cursor = connection.execute(
            """INSERT INTO resources
            (owner_id, category_id, name, description, condition, pickup_location, optional_deposit, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user["user_id"], payload.category_id, payload.name.strip(), payload.description.strip(),
             payload.condition.upper(), payload.pickup_location.strip(), payload.optional_deposit, now()),
        )
        row = connection.execute(
            RESOURCE_QUERY + " WHERE r.resource_id = ?", (cursor.lastrowid,)
        ).fetchone()
    return resource_response(row)


@app.get("/api/v1/borrow-requests")
def list_borrow_requests(user: sqlite3.Row = Depends(current_user)) -> list[dict]:
    with connect_db() as connection:
        rows = connection.execute(
            """SELECT br.*, r.name AS resource_name
            FROM borrow_requests br
            JOIN resources r ON r.resource_id = br.resource_id
            WHERE br.requester_id = ?
            ORDER BY br.created_at DESC""",
            (user["user_id"],),
        ).fetchall()
    return [dict(row) for row in rows]


@app.post("/api/v1/borrow-requests", status_code=201)
def create_borrow_request(
    payload: BorrowRequestPayload, user: sqlite3.Row = Depends(current_user)
) -> dict:
    if payload.requested_from < date.today():
        raise HTTPException(status_code=400, detail="The requested start date cannot be in the past")

    with connect_db() as connection:
        resource = connection.execute(
            "SELECT * FROM resources WHERE resource_id = ?", (payload.resource_id,)
        ).fetchone()
        if resource is None:
            raise HTTPException(status_code=404, detail="Resource not found")
        if resource["owner_id"] == user["user_id"]:
            raise HTTPException(status_code=400, detail="You cannot request your own listing")
        if resource["availability_status"] != "AVAILABLE":
            raise HTTPException(status_code=409, detail="This item is currently unavailable")

        duplicate = connection.execute(
            """SELECT request_id FROM borrow_requests
            WHERE resource_id = ? AND requester_id = ? AND status = 'PENDING'""",
            (payload.resource_id, user["user_id"]),
        ).fetchone()
        if duplicate is not None:
            raise HTTPException(status_code=409, detail="You already have a pending request for this item")

        cursor = connection.execute(
            """INSERT INTO borrow_requests
            (resource_id, requester_id, requested_from, requested_until, message, created_at)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (payload.resource_id, user["user_id"], payload.requested_from.isoformat(),
             payload.requested_until.isoformat(), payload.message.strip(), now()),
        )
        row = connection.execute(
            """SELECT br.*, r.name AS resource_name
            FROM borrow_requests br JOIN resources r ON r.resource_id = br.resource_id
            WHERE br.request_id = ?""",
            (cursor.lastrowid,),
        ).fetchone()
    return dict(row)


app.mount(
    "/",
    StaticFiles(directory=Path(__file__).resolve().parent.parent / "frontend", html=True),
    name="frontend",
)