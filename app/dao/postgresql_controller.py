import os
import pytest
import psycopg
from dotenv import load_dotenv

load_dotenv()

POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{DB_HOST}:{DB_PORT}/{POSTGRES_DB}"
def db_connection(database_url = DATABASE_URL):
    """Create a persistent database connection for the session."""
    with psycopg.connect(database_url) as conn:
        yield conn

def create_new_user(conn, username, email, password):
    """Create a new user in the database."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO users (username, email, password) VALUES (%s, %s, %s) RETURNING id;",
            (username, email, password)
        )
        user_id = cur.fetchone()[0]
        conn.commit()
        return user_id