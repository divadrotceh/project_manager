"""PostgreSQL schema setup for Project Manager App.

Usage:
    set DATABASE_URL=postgresql://user:password@localhost:5432/dbname
    python postgres_db_setup.py

Optional:
    python postgres_db_setup.py --print-sql
"""

from __future__ import annotations

import argparse
import os
import sys

from dotenv import load_dotenv

load_dotenv()  # Load env vars from .env file if present

try:
    import psycopg
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "Missing dependency 'psycopg'. Install it with: pip install psycopg[binary]"
    ) from exc


SCHEMA_SQL = r"""
BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TYPE project_role AS ENUM ('user', 'administrator');

CREATE TABLE IF NOT EXISTS app_user (
    u_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    u_name TEXT NOT NULL,
    u_pwd TEXT NOT NULL,
    u_created_at BIGINT NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT,
    u_updated_at BIGINT NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT,
    CONSTRAINT unq_app_user_u_name UNIQUE (u_name)
);

CREATE TABLE IF NOT EXISTS project (
    p_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    p_name TEXT NOT NULL,
    p_description TEXT,
    p_created_at BIGINT NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT,
    p_updated_at BIGINT NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT,
    CONSTRAINT unq_project_p_name UNIQUE (p_name)
);

CREATE TABLE IF NOT EXISTS project_access (
    p_id BIGINT NOT NULL REFERENCES project(p_id) ON DELETE CASCADE,
    u_id BIGINT NOT NULL REFERENCES app_user(u_id) ON DELETE CASCADE,
    pa_role project_role NOT NULL,
    granted_by_u_id BIGINT REFERENCES app_user(u_id) ON DELETE SET NULL,
    pa_created_at BIGINT NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT,
    pa_updated_at BIGINT NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT,
    PRIMARY KEY (p_id, u_id)
);

CREATE TABLE IF NOT EXISTS project_document (
    d_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    p_id BIGINT NOT NULL REFERENCES project(p_id) ON DELETE CASCADE,
    d_title TEXT NOT NULL,
    d_s3key TEXT NOT NULL,
    d_mime TEXT NOT NULL,
    d_uploaded_by_u_id BIGINT REFERENCES app_user(u_id) ON DELETE SET NULL,
    d_created_at BIGINT NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT,
    d_updated_at BIGINT NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT,
    CONSTRAINT unq_project_document_d_s3key UNIQUE (d_s3key)
);

COMMENT ON TABLE app_user IS 'Application users.';
COMMENT ON COLUMN app_user.u_name IS 'Unique username.';
COMMENT ON COLUMN app_user.u_pwd IS 'Password hash (pgcrypto crypt format).';

COMMENT ON TABLE project IS 'Projects managed by users.';

COMMENT ON TABLE project_access IS 'Membership relation between user and project, with project role.';
COMMENT ON COLUMN project_access.pa_role IS 'Role in project: user or administrator.';

COMMENT ON TABLE project_document IS 'Documents attached to projects.';
COMMENT ON COLUMN project_document.d_s3key IS 'S3 key/path for stored file.';

CREATE INDEX IF NOT EXISTS idx_project_access_u_id_p_id
    ON project_access (u_id, p_id);
CREATE INDEX IF NOT EXISTS idx_project_p_id
    ON project (p_id);
CREATE INDEX IF NOT EXISTS idx_project_document_p_id
    ON project_document (p_id);
CREATE INDEX IF NOT EXISTS idx_project_document_d_id
    ON project_document (d_id);
CREATE INDEX IF NOT EXISTS idx_username_trgm
    ON app_user USING gin (u_name gin_trgm_ops);
    
CREATE OR REPLACE FUNCTION fn_set_u_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.u_updated_at := EXTRACT(EPOCH FROM NOW())::BIGINT;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION fn_set_p_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.p_updated_at := EXTRACT(EPOCH FROM NOW())::BIGINT;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION fn_set_pa_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.pa_updated_at := EXTRACT(EPOCH FROM NOW())::BIGINT;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION fn_set_d_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.d_updated_at := EXTRACT(EPOCH FROM NOW())::BIGINT;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_app_user_bu_set_updated_at ON app_user;
CREATE TRIGGER trg_app_user_bu_set_updated_at
BEFORE UPDATE ON app_user
FOR EACH ROW
EXECUTE FUNCTION fn_set_u_updated_at();

DROP TRIGGER IF EXISTS trg_project_bu_set_updated_at ON project;
CREATE TRIGGER trg_project_bu_set_updated_at
BEFORE UPDATE ON project
FOR EACH ROW
EXECUTE FUNCTION fn_set_p_updated_at();

DROP TRIGGER IF EXISTS trg_project_access_bu_set_updated_at ON project_access;
CREATE TRIGGER trg_project_access_bu_set_updated_at
BEFORE UPDATE ON project_access
FOR EACH ROW
EXECUTE FUNCTION fn_set_pa_updated_at();

DROP TRIGGER IF EXISTS trg_project_document_bu_set_updated_at ON project_document;
CREATE TRIGGER trg_project_document_bu_set_updated_at
BEFORE UPDATE ON project_document
FOR EACH ROW
EXECUTE FUNCTION fn_set_d_updated_at();

CREATE OR REPLACE FUNCTION fn_project_role(p_u_id BIGINT, p_p_id BIGINT)
RETURNS project_role
LANGUAGE plpgsql
AS $$
DECLARE
    v_role project_role;
BEGIN
    SELECT pa.pa_role
      INTO v_role
      FROM project_access pa
     WHERE pa.u_id = p_u_id
       AND pa.p_id = p_p_id;

    RETURN v_role;
END;
$$;

CREATE OR REPLACE FUNCTION fn_require_project_member(p_requester_u_id BIGINT, p_p_id BIGINT)
RETURNS VOID
LANGUAGE plpgsql
AS $$
DECLARE
    v_role project_role;
BEGIN
    v_role := fn_project_role(p_requester_u_id, p_p_id);

    IF v_role IS NULL THEN
        RAISE EXCEPTION 'User % does not belong to project %', p_requester_u_id, p_p_id
            USING ERRCODE = '42501';
    END IF;
END;
$$;

CREATE OR REPLACE FUNCTION fn_require_project_admin(p_requester_u_id BIGINT, p_p_id BIGINT)
RETURNS VOID
LANGUAGE plpgsql
AS $$
DECLARE
    v_role project_role;
BEGIN
    v_role := fn_project_role(p_requester_u_id, p_p_id);

    IF v_role IS DISTINCT FROM 'administrator' THEN
        RAISE EXCEPTION 'User % is not administrator on project %', p_requester_u_id, p_p_id
            USING ERRCODE = '42501';
    END IF;
END;
$$;

CREATE OR REPLACE FUNCTION fn_prevent_last_admin_removal()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_admin_count BIGINT;
BEGIN
    IF OLD.pa_role <> 'administrator' THEN
        RETURN COALESCE(NEW, OLD);
    END IF;

    SELECT COUNT(*)
      INTO v_admin_count
      FROM project_access pa
     WHERE pa.p_id = OLD.p_id
       AND pa.pa_role = 'administrator'
       AND pa.u_id <> OLD.u_id;

    IF v_admin_count = 0 THEN
        RAISE EXCEPTION 'Project % must have at least one administrator', OLD.p_id
            USING ERRCODE = '23514';
    END IF;

    RETURN COALESCE(NEW, OLD);
END;
$$;

DROP TRIGGER IF EXISTS trg_project_access_bd_prevent_last_admin ON project_access;
CREATE TRIGGER trg_project_access_bd_prevent_last_admin
BEFORE DELETE ON project_access
FOR EACH ROW
EXECUTE FUNCTION fn_prevent_last_admin_removal();

DROP TRIGGER IF EXISTS trg_project_access_bu_prevent_last_admin ON project_access;
CREATE TRIGGER trg_project_access_bu_prevent_last_admin
BEFORE UPDATE OF pa_role ON project_access
FOR EACH ROW
WHEN (OLD.pa_role = 'administrator' AND NEW.pa_role <> 'administrator')
EXECUTE FUNCTION fn_prevent_last_admin_removal();

CREATE OR REPLACE FUNCTION sp_create_user(
    p_requester_u_id BIGINT,
    p_u_name TEXT,
    p_plain_pwd TEXT
)
RETURNS BIGINT
LANGUAGE plpgsql
AS $$
DECLARE
    v_user_id BIGINT;
BEGIN
    INSERT INTO app_user (u_name, u_pwd)
    VALUES (p_u_name, crypt(p_plain_pwd, gen_salt('bf')))
    RETURNING u_id INTO v_user_id;

    RETURN v_user_id;
END;
$$;

CREATE OR REPLACE FUNCTION sp_check_u_pwd(
    p_u_id BIGINT,
    p_plain_pwd TEXT
)
RETURNS BOOLEAN
LANGUAGE SQL
AS $$
    SELECT EXISTS (
        SELECT 1
          FROM app_user u
         WHERE u.u_id = p_u_id
           AND u.u_pwd = crypt(p_plain_pwd, u.u_pwd)
    );
$$;

CREATE OR REPLACE FUNCTION sp_create_project(
    p_requester_u_id BIGINT,
    p_name TEXT,
    p_description TEXT
)
RETURNS BIGINT
LANGUAGE plpgsql
AS $$
DECLARE
    v_project_id BIGINT;
BEGIN
    INSERT INTO project (p_name, p_description)
    VALUES (p_name, p_description)
    RETURNING p_id INTO v_project_id;

    INSERT INTO project_access (p_id, u_id, pa_role, granted_by_u_id)
    VALUES (v_project_id, p_requester_u_id, 'administrator', p_requester_u_id);

    RETURN v_project_id;
END;
$$;

CREATE OR REPLACE FUNCTION sp_get_projects_by_u_id(
    p_requester_u_id BIGINT,
    p_target_u_id BIGINT
)
RETURNS TABLE (
    p_id BIGINT,
    p_name TEXT,
    p_description TEXT,
    pa_role project_role,
    p_created_at BIGINT,
    p_updated_at BIGINT
)
LANGUAGE plpgsql
AS $$
BEGIN
    IF p_requester_u_id <> p_target_u_id THEN
        RAISE EXCEPTION 'Cannot read projects of another user'
            USING ERRCODE = '42501';
    END IF;

    RETURN QUERY
    SELECT p.p_id, p.p_name, p.p_description, pa.pa_role, p.p_created_at, p.p_updated_at
      FROM project p
      JOIN project_access pa
        ON pa.p_id = p.p_id
     WHERE pa.u_id = p_target_u_id
     ORDER BY p.p_updated_at DESC;
END;
$$;

CREATE OR REPLACE FUNCTION sp_get_project_details(
    p_requester_u_id BIGINT,
    p_p_id BIGINT
)
RETURNS TABLE (
    p_id BIGINT,
    p_name TEXT,
    p_description TEXT,
    p_created_at BIGINT,
    p_updated_at BIGINT
)
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM fn_require_project_member(p_requester_u_id, p_p_id);

    RETURN QUERY
    SELECT p.p_id, p.p_name, p.p_description, p.p_created_at, p.p_updated_at
      FROM project p
     WHERE p.p_id = p_p_id;
END;
$$;

CREATE OR REPLACE FUNCTION sp_update_project(
    p_requester_u_id BIGINT,
    p_p_id BIGINT,
    p_name TEXT,
    p_description TEXT
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM fn_require_project_member(p_requester_u_id, p_p_id);

    UPDATE project p
       SET p_name = COALESCE(p_name, p.p_name),
           p_description = COALESCE(p_description, p.p_description)
     WHERE p.p_id = p_p_id;
END;
$$;

CREATE OR REPLACE FUNCTION sp_delete_project(
    p_requester_u_id BIGINT,
    p_p_id BIGINT
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM fn_require_project_admin(p_requester_u_id, p_p_id);

    DELETE FROM project p
     WHERE p.p_id = p_p_id;
END;
$$;

CREATE OR REPLACE FUNCTION sp_get_documents(
    p_requester_u_id BIGINT,
    p_p_id BIGINT
)
RETURNS TABLE (
    d_id BIGINT,
    p_id BIGINT,
    d_s3key TEXT,
    d_title TEXT,
    d_mime TEXT,
    d_uploaded_by_u_id BIGINT,
    d_created_at BIGINT,
    d_updated_at BIGINT
)
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM fn_require_project_member(p_requester_u_id, p_p_id);

    RETURN QUERY
    SELECT d.d_id, d.p_id, d.d_s3key, d.d_title, d.d_mime, d.d_uploaded_by_u_id, d.d_created_at, d.d_updated_at
      FROM project_document d
     WHERE d.p_id = p_p_id
     ORDER BY d.d_created_at DESC;
END;
$$;

CREATE OR REPLACE FUNCTION sp_upsert_document(
    p_requester_u_id BIGINT,
    p_p_id BIGINT,
    p_d_id BIGINT,
    p_d_s3key TEXT,
    p_d_title TEXT,
    p_d_mime TEXT
)
RETURNS BIGINT
LANGUAGE plpgsql
AS $$
DECLARE
    v_document_id BIGINT;
BEGIN
    PERFORM fn_require_project_member(p_requester_u_id, p_p_id);

    IF p_d_id IS NULL THEN
        INSERT INTO project_document (p_id, d_s3key, d_title, d_mime, d_uploaded_by_u_id)
        VALUES (p_p_id, p_d_s3key, p_d_title, p_d_mime, p_requester_u_id)
        RETURNING d_id INTO v_document_id;
    ELSE
        UPDATE project_document d
           SET d_s3key = COALESCE(p_d_s3key, d.d_s3key),
               d_title = COALESCE(p_d_title, d.d_title),
               d_mime = COALESCE(p_d_mime, d.d_mime)
         WHERE d.d_id = p_d_id
           AND d.p_id = p_p_id
        RETURNING d_id INTO v_document_id;
    END IF;

    RETURN v_document_id;
END;
$$;

CREATE OR REPLACE FUNCTION sp_remove_document(
    p_requester_u_id BIGINT,
    p_p_id BIGINT,
    p_d_id BIGINT
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM fn_require_project_member(p_requester_u_id, p_p_id);

    DELETE FROM project_document d
     WHERE d.d_id = p_d_id
       AND d.p_id = p_p_id;
END;
$$;

CREATE OR REPLACE FUNCTION sp_change_role(
    p_requester_u_id BIGINT,
    p_p_id BIGINT,
    p_target_u_id BIGINT,
    p_new_role project_role
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM fn_require_project_admin(p_requester_u_id, p_p_id);

    INSERT INTO project_access (p_id, u_id, pa_role, granted_by_u_id)
    VALUES (p_p_id, p_target_u_id, p_new_role, p_requester_u_id)
    ON CONFLICT (p_id, u_id)
    DO UPDATE
       SET pa_role = EXCLUDED.pa_role,
           granted_by_u_id = EXCLUDED.granted_by_u_id;
END;
$$;

COMMIT;
"""

POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

def apply_schema(database_url: str) -> None:
    """Apply all DDL/DML in SCHEMA_SQL in a single transaction."""
    try:
        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(SCHEMA_SQL)
    except Exception as e:
            print(f"Error occurred while executing schema SQL: {e}")
            print(f"Error occurred while executing schema SQL: {e}")
            print("Validate your DATABASE_URL and ensure the database server is running and accessible.")
            print(f"user: {POSTGRES_USER}, host: {DB_HOST}, port: {DB_PORT}, db: {POSTGRES_DB}")
            raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize PostgreSQL schema for Project Manager App")
    parser.add_argument(
        "--database-url",
        default=f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{DB_HOST}:{DB_PORT}/{POSTGRES_DB}",
        help="PostgreSQL URL. Defaults to env var DATABASE_URL.",
    )
    parser.add_argument(
        "--print-sql",
        action="store_true",
        help="Print SQL instead of executing it.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.print_sql:
        print(SCHEMA_SQL)
        return 0

    apply_schema(args.database_url)
    print("Schema applied successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
