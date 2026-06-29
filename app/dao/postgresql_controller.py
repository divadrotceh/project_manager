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


def create_new_user(conn, username,password):
    """Create a new user in the database."""
    with conn.cursor() as cur:
        cur.execute("SELECT sp_create_user(%s, %s)", (username, password))
        user_id = cur.fetchone()[0]
        conn.commit()
        return user_id


def create_new_project(conn, user_id, project_name, project_description=None):
    """Create a new project in the database."""
    with conn.cursor() as cur:
        cur.execute("SELECT sp_create_project(%s, %s, %s)", (user_id, project_name, project_description))
        project_id = cur.fetchone()[0]
        conn.commit()
        return project_id


def get_projects_by_user_id(conn, requester_user_id, user_id):
    """Retrieve projects associated with a specific user."""
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM sp_get_projects_by_user_id(%s, %s)", (requester_user_id, user_id))
        projects = cur.fetchall()
        return projects
    

def check_user_password(conn, username, password):
    """Check if the provided password matches the stored password for the user."""
    with conn.cursor() as cur:
        cur.execute("SELECT sp_check_u_pwd(%s, %s)", (username, password))
        result = cur.fetchone()
        return result[0] if result else False


def get_project_details(conn, requester_user_id, project_id):
    """Retrieve details of a specific project."""
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM sp_get_project_details(%s, %s)", (requester_user_id, project_id))
        project_details = cur.fetchone()
        return project_details
    

def update_project(conn, requester_user_id, project_id, new_name=None, new_description=None):
    """Update the name and/or description of a specific project."""
    with conn.cursor() as cur:
        cur.execute("SELECT sp_update_project(%s, %s, %s, %s)", (requester_user_id, project_id, new_name, new_description))
        updated_project_id = cur.fetchone()[0]
        conn.commit()
        return updated_project_id
    
    
def delete_project(conn, requester_user_id, project_id):
    """Delete a specific project."""
    with conn.cursor() as cur:
        cur.execute("SELECT sp_delete_project(%s, %s)", (requester_user_id, project_id))
        deleted_project_id = cur.fetchone()[0]
        conn.commit()
        return deleted_project_id


def get_documents(conn, requester_user_id, project_id):
    """Retrieve documents associated with a specific project."""
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM sp_get_documents(%s, %s)", (requester_user_id, project_id))
        documents = cur.fetchall()
        return documents


def change_user_role(conn, requester_user_id, project_id, target_user_id, new_role):
    """Change the role of a user in a specific project."""
    with conn.cursor() as cur:
        cur.execute("SELECT sp_change_role(%s, %s, %s, %s)", (requester_user_id, project_id, target_user_id, new_role))
        result = cur.fetchone()[0]
        conn.commit()
        return result


def upsert_document(conn, requester_user_id, project_id, document_id, s3_key, title, mime_type):
    """Insert or update a document in a specific project."""
    with conn.cursor() as cur:
        cur.execute("SELECT sp_upsert_document(%s, %s, %s, %s, %s, %s)", (requester_user_id, project_id, document_id, s3_key, title, mime_type))
        upserted_document_id = cur.fetchone()[0]
        conn.commit()
        return upserted_document_id
    

def remove_document(conn, requester_user_id, project_id, document_id):
    """Remove a document from a specific project."""
    with conn.cursor() as cur:
        cur.execute("SELECT sp_remove_document(%s, %s, %s)", (requester_user_id, project_id, document_id))
        removed_document_id = cur.fetchone()[0]
        conn.commit()
        return removed_document_id
