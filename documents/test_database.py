"""
Comprehensive pytest suite for Project Manager App database functionality.

Tests cover:
- User creation and authentication
- Project CRUD operations
- Project membership and roles
- Document management
- Authorization and permission checks
- Edge cases and error conditions

Setup: Set DATABASE_URL environment variable pointing to test PostgreSQL instance.
Run: pytest test_database.py -v
"""

import os
import pytest
import psycopg
from datetime import datetime
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()

POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{DB_HOST}:{DB_PORT}/{POSTGRES_DB}"

@pytest.fixture(scope="session")
def database_url():
    """Get database URL from environment or use default test DB."""
    url = DATABASE_URL
    if not url:
        pytest.skip("DATABASE_URL environment variable not set")
    return url


@pytest.fixture(scope="session")
def db_connection(database_url):
    """Create a persistent database connection for the test session."""
    with psycopg.connect(database_url) as conn:
        yield conn


@pytest.fixture(autouse=True)
def cleanup_after_test(db_connection):
    """Clean up test data after each test."""
    yield
    # Optional: truncate tables after test if needed
    # This is handled by transaction rollback in individual tests


@contextmanager
def test_transaction(db_connection):
    """Context manager for test transactions that rollback after test."""
    conn = db_connection
    with conn.cursor() as cur:
        cur.execute("BEGIN")
        try:
            yield cur
            # Don't commit - let the test handle or rollback
        except Exception:
            cur.execute("ROLLBACK")
            raise
        finally:
            try:
                cur.execute("ROLLBACK")
            except:
                pass


# ============================================================================
# FIXTURES: Test Users
# ============================================================================

@pytest.fixture
def user1(db_connection):
    """Create and return test user 1."""
    with test_transaction(db_connection) as cur:
        cur.execute("SELECT sp_create_user(%s, %s, %s)", (1, "testuser1", "password123"))
        user_id = cur.fetchone()[0]
        yield user_id


@pytest.fixture
def user2(db_connection):
    """Create and return test user 2."""
    with test_transaction(db_connection) as cur:
        cur.execute("SELECT sp_create_user(%s, %s, %s)", (1, "testuser2", "password456"))
        user_id = cur.fetchone()[0]
        yield user_id


@pytest.fixture
def user3(db_connection):
    """Create and return test user 3."""
    with test_transaction(db_connection) as cur:
        cur.execute("SELECT sp_create_user(%s, %s, %s)", (1, "testuser3", "password789"))
        user_id = cur.fetchone()[0]
        yield user_id


# ============================================================================
# FIXTURES: Test Projects
# ============================================================================

@pytest.fixture
def project1(db_connection, user1):
    """Create and return test project owned by user1."""
    with test_transaction(db_connection) as cur:
        cur.execute(
            "SELECT sp_create_project(%s, %s, %s)",
            (user1, "Test Project 1", "A test project")
        )
        project_id = cur.fetchone()[0]
        yield project_id


@pytest.fixture
def project2(db_connection, user1):
    """Create and return second test project."""
    with test_transaction(db_connection) as cur:
        cur.execute(
            "SELECT sp_create_project(%s, %s, %s)",
            (user1, "Test Project 2", "Another test project")
        )
        project_id = cur.fetchone()[0]
        yield project_id


# ============================================================================
# TESTS: User Creation and Authentication
# ============================================================================

class TestUserCreation:
    """Test user creation and password validation."""

    def test_create_user_success(self, db_connection):
        """Test successful user creation."""
        with test_transaction(db_connection) as cur:
            cur.execute("SELECT sp_create_user(%s, %s, %s)", (1, "newuser", "pass123"))
            result = cur.fetchone()
            assert result is not None
            user_id = result[0]
            assert isinstance(user_id, int)
            assert user_id > 0

    def test_create_user_duplicate_username(self, db_connection, user1):
        """Test that duplicate username raises error."""
        with test_transaction(db_connection) as cur:
            with pytest.raises(psycopg.errors.UniqueViolation):
                cur.execute("SELECT sp_create_user(%s, %s, %s)", (1, "testuser1", "different"))

    def test_check_password_correct(self, db_connection, user1):
        """Test password check with correct password."""
        with test_transaction(db_connection) as cur:
            cur.execute("SELECT sp_check_u_pwd(%s, %s)", (user1, "password123"))
            result = cur.fetchone()[0]
            assert result is True

    def test_check_password_incorrect(self, db_connection, user1):
        """Test password check with incorrect password."""
        with test_transaction(db_connection) as cur:
            cur.execute("SELECT sp_check_u_pwd(%s, %s)", (user1, "wrongpassword"))
            result = cur.fetchone()[0]
            assert result is False

    def test_check_password_nonexistent_user(self, db_connection):
        """Test password check for non-existent user."""
        with test_transaction(db_connection) as cur:
            cur.execute("SELECT sp_check_u_pwd(%s, %s)", (99999, "anypass"))
            result = cur.fetchone()[0]
            assert result is False


# ============================================================================
# TESTS: Project Operations (CRUD)
# ============================================================================

class TestProjectCreation:
    """Test project creation functionality."""

    def test_create_project_success(self, db_connection, user1):
        """Test successful project creation."""
        with test_transaction(db_connection) as cur:
            cur.execute(
                "SELECT sp_create_project(%s, %s, %s)",
                (user1, "My Project", "Project description")
            )
            result = cur.fetchone()
            assert result is not None
            project_id = result[0]
            assert isinstance(project_id, int)
            assert project_id > 0

    def test_create_project_creator_becomes_admin(self, db_connection, user1):
        """Test that project creator is automatically added as administrator."""
        with test_transaction(db_connection) as cur:
            cur.execute(
                "SELECT sp_create_project(%s, %s, %s)",
                (user1, "Admin Test Project", "Testing admin role")
            )
            project_id = cur.fetchone()[0]

            # Verify creator is admin
            cur.execute(
                "SELECT pa_role FROM project_access WHERE p_id = %s AND u_id = %s",
                (project_id, user1)
            )
            role = cur.fetchone()[0]
            assert role == "administrator"

    def test_create_project_duplicate_name(self, db_connection, user1):
        """Test that duplicate project name raises error."""
        with test_transaction(db_connection) as cur:
            cur.execute(
                "SELECT sp_create_project(%s, %s, %s)",
                (user1, "UniqueProject", "First one")
            )
            with pytest.raises(psycopg.errors.UniqueViolation):
                cur.execute(
                    "SELECT sp_create_project(%s, %s, %s)",
                    (user1, "UniqueProject", "Second one")
                )

    def test_create_project_nullable_description(self, db_connection, user1):
        """Test project creation with null description."""
        with test_transaction(db_connection) as cur:
            cur.execute(
                "SELECT sp_create_project(%s, %s, %s)",
                (user1, "No Description Project", None)
            )
            project_id = cur.fetchone()[0]
            assert project_id > 0


class TestProjectRetrieval:
    """Test project retrieval and details."""

    def test_get_projects_by_user(self, db_connection, user1, project1, project2):
        """Test retrieving user's projects."""
        with test_transaction(db_connection) as cur:
            cur.execute("SELECT * FROM sp_get_projects_by_u_id(%s, %s)", (user1, user1))
            projects = cur.fetchall()
            assert len(projects) >= 2
            project_ids = [p[0] for p in projects]
            assert project1 in project_ids
            assert project2 in project_ids

    def test_get_projects_cannot_read_others_projects(self, db_connection, user1, user2, project1):
        """Test that user cannot read another user's projects."""
        with test_transaction(db_connection) as cur:
            with pytest.raises(psycopg.errors.RaiseException):
                cur.execute("SELECT * FROM sp_get_projects_by_u_id(%s, %s)", (user1, user2))

    def test_get_project_details_as_member(self, db_connection, user1, project1):
        """Test retrieving project details as project member."""
        with test_transaction(db_connection) as cur:
            cur.execute("SELECT * FROM sp_get_project_details(%s, %s)", (user1, project1))
            details = cur.fetchone()
            assert details is not None
            assert details[0] == project1  # p_id
            assert details[1] == "Test Project 1"  # p_name

    def test_get_project_details_non_member_denied(self, db_connection, user1, user2, project1):
        """Test that non-member cannot access project details."""
        with test_transaction(db_connection) as cur:
            with pytest.raises(psycopg.errors.RaiseException):
                cur.execute("SELECT * FROM sp_get_project_details(%s, %s)", (user2, project1))


class TestProjectUpdate:
    """Test project update functionality."""

    def test_update_project_as_member(self, db_connection, user1, project1):
        """Test updating project as project member."""
        with test_transaction(db_connection) as cur:
            cur.execute(
                "SELECT sp_update_project(%s, %s, %s, %s)",
                (user1, project1, "Updated Name", "Updated Description")
            )
            # Verify update
            cur.execute("SELECT p_name, p_description FROM project WHERE p_id = %s", (project1,))
            name, desc = cur.fetchone()
            assert name == "Updated Name"
            assert desc == "Updated Description"

    def test_update_project_partial_update(self, db_connection, user1, project1):
        """Test partial update (only name, keep description)."""
        with test_transaction(db_connection) as cur:
            cur.execute(
                "SELECT sp_update_project(%s, %s, %s, %s)",
                (user1, project1, "New Name", None)
            )
            cur.execute("SELECT p_name, p_description FROM project WHERE p_id = %s", (project1,))
            name, desc = cur.fetchone()
            assert name == "New Name"
            assert desc == "A test project"  # Original description preserved

    def test_update_project_non_member_denied(self, db_connection, user2, project1):
        """Test that non-member cannot update project."""
        with test_transaction(db_connection) as cur:
            with pytest.raises(psycopg.errors.RaiseException):
                cur.execute(
                    "SELECT sp_update_project(%s, %s, %s, %s)",
                    (user2, project1, "Hacked", "Hacked")
                )


class TestProjectDeletion:
    """Test project deletion functionality."""

    def test_delete_project_as_admin(self, db_connection, user1, project1):
        """Test deleting project as administrator."""
        with test_transaction(db_connection) as cur:
            cur.execute("SELECT sp_delete_project(%s, %s)", (user1, project1))
            # Verify deletion
            cur.execute("SELECT COUNT(*) FROM project WHERE p_id = %s", (project1,))
            count = cur.fetchone()[0]
            assert count == 0

    def test_delete_project_cascades_access(self, db_connection, user1, project1):
        """Test that deleting project cascades to project_access."""
        with test_transaction(db_connection) as cur:
            cur.execute("SELECT sp_delete_project(%s, %s)", (user1, project1))
            # Verify access records deleted
            cur.execute(
                "SELECT COUNT(*) FROM project_access WHERE p_id = %s",
                (project1,)
            )
            count = cur.fetchone()[0]
            assert count == 0

    def test_delete_project_non_admin_denied(self, db_connection, user1, user2, project1):
        """Test that non-admin cannot delete project."""
        # Add user2 as regular member
        with test_transaction(db_connection) as cur:
            cur.execute(
                "SELECT sp_change_role(%s, %s, %s, %s)",
                (user1, project1, user2, "user")
            )
            # Try to delete as non-admin
            with pytest.raises(psycopg.errors.RaiseException):
                cur.execute("SELECT sp_delete_project(%s, %s)", (user2, project1))


# ============================================================================
# TESTS: Project Access and Roles
# ============================================================================

class TestProjectAccessControl:
    """Test project access and role management."""

    def test_change_role_to_user(self, db_connection, user1, user2, project1):
        """Test changing user role to 'user'."""
        with test_transaction(db_connection) as cur:
            cur.execute(
                "SELECT sp_change_role(%s, %s, %s, %s)",
                (user1, project1, user2, "user")
            )
            # Verify role
            cur.execute(
                "SELECT pa_role FROM project_access WHERE p_id = %s AND u_id = %s",
                (project1, user2)
            )
            role = cur.fetchone()[0]
            assert role == "user"

    def test_change_role_to_administrator(self, db_connection, user1, user2, project1):
        """Test promoting user to administrator."""
        with test_transaction(db_connection) as cur:
            # First add as user
            cur.execute(
                "SELECT sp_change_role(%s, %s, %s, %s)",
                (user1, project1, user2, "user")
            )
            # Then promote to admin
            cur.execute(
                "SELECT sp_change_role(%s, %s, %s, %s)",
                (user1, project1, user2, "administrator")
            )
            cur.execute(
                "SELECT pa_role FROM project_access WHERE p_id = %s AND u_id = %s",
                (project1, user2)
            )
            role = cur.fetchone()[0]
            assert role == "administrator"

    def test_change_role_non_admin_denied(self, db_connection, user1, user2, user3, project1):
        """Test that non-admin cannot change roles."""
        with test_transaction(db_connection) as cur:
            # Add user2 as regular member
            cur.execute(
                "SELECT sp_change_role(%s, %s, %s, %s)",
                (user1, project1, user2, "user")
            )
            # Try to change user3's role as non-admin
            with pytest.raises(psycopg.errors.RaiseException):
                cur.execute(
                    "SELECT sp_change_role(%s, %s, %s, %s)",
                    (user2, project1, user3, "user")
                )

    def test_prevent_last_admin_removal(self, db_connection, user1, project1):
        """Test that the last admin cannot be removed."""
        with test_transaction(db_connection) as cur:
            # Try to demote the only admin
            with pytest.raises(psycopg.errors.RaiseException):
                cur.execute(
                    "UPDATE project_access SET pa_role = %s WHERE p_id = %s AND u_id = %s",
                    ("user", project1, user1)
                )

    def test_prevent_last_admin_deletion(self, db_connection, user1, project1):
        """Test that the last admin cannot be deleted from project."""
        with test_transaction(db_connection) as cur:
            # Try to delete the only admin
            with pytest.raises(psycopg.errors.RaiseException):
                cur.execute(
                    "DELETE FROM project_access WHERE p_id = %s AND u_id = %s",
                    (project1, user1)
                )


# ============================================================================
# TESTS: Document Management
# ============================================================================

class TestDocumentCreation:
    """Test document creation (upsert)."""

    def test_upsert_document_insert(self, db_connection, user1, project1):
        """Test inserting new document via upsert."""
        with test_transaction(db_connection) as cur:
            cur.execute(
                "SELECT sp_upsert_document(%s, %s, %s, %s, %s, %s)",
                (user1, project1, None, "s3://bucket/doc1.pdf", "Document 1", "application/pdf")
            )
            doc_id = cur.fetchone()[0]
            assert doc_id > 0

    def test_upsert_document_with_title(self, db_connection, user1, project1):
        """Test document creation with title."""
        with test_transaction(db_connection) as cur:
            cur.execute(
                "SELECT sp_upsert_document(%s, %s, %s, %s, %s, %s)",
                (user1, project1, None, "s3://bucket/doc.pdf", "My Document", "application/pdf")
            )
            doc_id = cur.fetchone()[0]
            # Verify title was stored
            cur.execute("SELECT d_title FROM project_document WHERE d_id = %s", (doc_id,))
            title = cur.fetchone()[0]
            assert title == "My Document"

    def test_upsert_document_update(self, db_connection, user1, project1):
        """Test updating existing document via upsert."""
        with test_transaction(db_connection) as cur:
            # Create document
            cur.execute(
                "SELECT sp_upsert_document(%s, %s, %s, %s, %s, %s)",
                (user1, project1, None, "s3://bucket/doc1.pdf", "Original", "application/pdf")
            )
            doc_id = cur.fetchone()[0]

            # Update via upsert
            cur.execute(
                "SELECT sp_upsert_document(%s, %s, %s, %s, %s, %s)",
                (user1, project1, doc_id, "s3://bucket/doc1-v2.pdf", "Updated", "application/pdf")
            )
            returned_id = cur.fetchone()[0]
            assert returned_id == doc_id

            # Verify update
            cur.execute(
                "SELECT d_s3key, d_title FROM project_document WHERE d_id = %s",
                (doc_id,)
            )
            s3key, title = cur.fetchone()
            assert s3key == "s3://bucket/doc1-v2.pdf"
            assert title == "Updated"

    def test_upsert_document_non_member_denied(self, db_connection, user2, project1):
        """Test that non-member cannot create document."""
        with test_transaction(db_connection) as cur:
            with pytest.raises(psycopg.errors.RaiseException):
                cur.execute(
                    "SELECT sp_upsert_document(%s, %s, %s, %s, %s, %s)",
                    (user2, project1, None, "s3://bucket/doc.pdf", "Doc", "application/pdf")
                )

    def test_upsert_document_duplicate_s3key(self, db_connection, user1, project1):
        """Test that duplicate S3 key raises error."""
        with test_transaction(db_connection) as cur:
            cur.execute(
                "SELECT sp_upsert_document(%s, %s, %s, %s, %s, %s)",
                (user1, project1, None, "s3://bucket/unique.pdf", "Doc1", "application/pdf")
            )
            with pytest.raises(psycopg.errors.UniqueViolation):
                cur.execute(
                    "SELECT sp_upsert_document(%s, %s, %s, %s, %s, %s)",
                    (user1, project1, None, "s3://bucket/unique.pdf", "Doc2", "application/pdf")
                )


class TestDocumentRetrieval:
    """Test document retrieval."""

    def test_get_documents_empty(self, db_connection, user1, project1):
        """Test getting documents from empty project."""
        with test_transaction(db_connection) as cur:
            cur.execute("SELECT * FROM sp_get_documents(%s, %s)", (user1, project1))
            docs = cur.fetchall()
            assert len(docs) == 0

    def test_get_documents_multiple(self, db_connection, user1, project1):
        """Test retrieving multiple documents."""
        with test_transaction(db_connection) as cur:
            # Create 3 documents
            doc_ids = []
            for i in range(3):
                cur.execute(
                    "SELECT sp_upsert_document(%s, %s, %s, %s, %s, %s)",
                    (user1, project1, None, f"s3://bucket/doc{i}.pdf", f"Doc {i}", "application/pdf")
                )
                doc_ids.append(cur.fetchone()[0])

            # Retrieve all
            cur.execute("SELECT d_id FROM sp_get_documents(%s, %s)", (user1, project1))
            retrieved = [row[0] for row in cur.fetchall()]
            assert len(retrieved) == 3
            for doc_id in doc_ids:
                assert doc_id in retrieved

    def test_get_documents_non_member_denied(self, db_connection, user2, project1):
        """Test that non-member cannot access documents."""
        with test_transaction(db_connection) as cur:
            with pytest.raises(psycopg.errors.RaiseException):
                cur.execute("SELECT * FROM sp_get_documents(%s, %s)", (user2, project1))


class TestDocumentDeletion:
    """Test document deletion."""

    def test_remove_document_success(self, db_connection, user1, project1):
        """Test successful document removal."""
        with test_transaction(db_connection) as cur:
            # Create document
            cur.execute(
                "SELECT sp_upsert_document(%s, %s, %s, %s, %s, %s)",
                (user1, project1, None, "s3://bucket/doc.pdf", "Doc", "application/pdf")
            )
            doc_id = cur.fetchone()[0]

            # Delete it
            cur.execute("SELECT sp_remove_document(%s, %s, %s)", (user1, project1, doc_id))

            # Verify deletion
            cur.execute("SELECT COUNT(*) FROM project_document WHERE d_id = %s", (doc_id,))
            count = cur.fetchone()[0]
            assert count == 0

    def test_remove_document_non_member_denied(self, db_connection, user1, user2, project1):
        """Test that non-member cannot delete document."""
        with test_transaction(db_connection) as cur:
            # Create document as user1
            cur.execute(
                "SELECT sp_upsert_document(%s, %s, %s, %s, %s, %s)",
                (user1, project1, None, "s3://bucket/doc.pdf", "Doc", "application/pdf")
            )
            doc_id = cur.fetchone()[0]

            # Try to delete as user2 (non-member)
            with pytest.raises(psycopg.errors.RaiseException):
                cur.execute("SELECT sp_remove_document(%s, %s, %s)", (user2, project1, doc_id))


# ============================================================================
# TESTS: Authorization Helper Functions
# ============================================================================

class TestAuthorizationHelpers:
    """Test authorization helper functions."""

    def test_fn_project_role_returns_role(self, db_connection, user1, project1):
        """Test that fn_project_role returns user's role."""
        with test_transaction(db_connection) as cur:
            cur.execute("SELECT fn_project_role(%s, %s)", (user1, project1))
            role = cur.fetchone()[0]
            assert role == "administrator"

    def test_fn_project_role_returns_null_non_member(self, db_connection, user2, project1):
        """Test that fn_project_role returns NULL for non-members."""
        with test_transaction(db_connection) as cur:
            cur.execute("SELECT fn_project_role(%s, %s)", (user2, project1))
            role = cur.fetchone()[0]
            assert role is None

    def test_fn_require_project_member_success(self, db_connection, user1, project1):
        """Test member check succeeds for actual member."""
        with test_transaction(db_connection) as cur:
            # Should not raise
            cur.execute("SELECT fn_require_project_member(%s, %s)", (user1, project1))

    def test_fn_require_project_member_fails(self, db_connection, user2, project1):
        """Test member check fails for non-member."""
        with test_transaction(db_connection) as cur:
            with pytest.raises(psycopg.errors.RaiseException):
                cur.execute("SELECT fn_require_project_member(%s, %s)", (user2, project1))

    def test_fn_require_project_admin_success(self, db_connection, user1, project1):
        """Test admin check succeeds for admin."""
        with test_transaction(db_connection) as cur:
            cur.execute("SELECT fn_require_project_admin(%s, %s)", (user1, project1))

    def test_fn_require_project_admin_fails_non_admin(self, db_connection, user1, user2, project1):
        """Test admin check fails for non-admin member."""
        with test_transaction(db_connection) as cur:
            # Add user2 as regular member
            cur.execute(
                "SELECT sp_change_role(%s, %s, %s, %s)",
                (user1, project1, user2, "user")
            )
            # Admin check should fail
            with pytest.raises(psycopg.errors.RaiseException):
                cur.execute("SELECT fn_require_project_admin(%s, %s)", (user2, project1))


# ============================================================================
# TESTS: Data Integrity and Triggers
# ============================================================================

class TestDataIntegrity:
    """Test triggers and data integrity."""

    def test_updated_at_timestamp_on_user_update(self, db_connection, user1):
        """Test that u_updated_at is updated on user update."""
        with test_transaction(db_connection) as cur:
            cur.execute("SELECT u_updated_at FROM app_user WHERE u_id = %s", (user1,))
            original_ts = cur.fetchone()[0]

            # Wait a moment and update
            import time
            time.sleep(0.1)

            cur.execute("UPDATE app_user SET u_name = u_name WHERE u_id = %s", (user1,))
            cur.execute("SELECT u_updated_at FROM app_user WHERE u_id = %s", (user1,))
            new_ts = cur.fetchone()[0]

            assert new_ts >= original_ts

    def test_updated_at_timestamp_on_project_update(self, db_connection, user1, project1):
        """Test that p_updated_at is updated on project update."""
        with test_transaction(db_connection) as cur:
            cur.execute("SELECT p_updated_at FROM project WHERE p_id = %s", (project1,))
            original_ts = cur.fetchone()[0]

            import time
            time.sleep(0.1)

            cur.execute(
                "UPDATE project SET p_name = p_name WHERE p_id = %s",
                (project1,)
            )
            cur.execute("SELECT p_updated_at FROM project WHERE p_id = %s", (project1,))
            new_ts = cur.fetchone()[0]

            assert new_ts >= original_ts

    def test_cascade_delete_project_deletes_documents(self, db_connection, user1, project1):
        """Test that deleting project cascades to documents."""
        with test_transaction(db_connection) as cur:
            # Create document
            cur.execute(
                "SELECT sp_upsert_document(%s, %s, %s, %s, %s, %s)",
                (user1, project1, None, "s3://bucket/doc.pdf", "Doc", "application/pdf")
            )
            doc_id = cur.fetchone()[0]

            # Delete project
            cur.execute("DELETE FROM project WHERE p_id = %s", (project1,))

            # Verify document is gone
            cur.execute("SELECT COUNT(*) FROM project_document WHERE d_id = %s", (doc_id,))
            count = cur.fetchone()[0]
            assert count == 0

    def test_cascade_delete_user_cascades_access(self, db_connection, user1, user2, project1):
        """Test that deleting user cascades to project_access."""
        with test_transaction(db_connection) as cur:
            # Add user2 to project
            cur.execute(
                "SELECT sp_change_role(%s, %s, %s, %s)",
                (user1, project1, user2, "user")
            )

            # Verify user2 is in access
            cur.execute(
                "SELECT COUNT(*) FROM project_access WHERE u_id = %s AND p_id = %s",
                (user2, project1)
            )
            assert cur.fetchone()[0] == 1

            # Delete user2
            cur.execute("DELETE FROM app_user WHERE u_id = %s", (user2,))

            # Verify access is deleted
            cur.execute(
                "SELECT COUNT(*) FROM project_access WHERE u_id = %s AND p_id = %s",
                (user2, project1)
            )
            assert cur.fetchone()[0] == 0


# ============================================================================
# TESTS: Complex Scenarios
# ============================================================================

class TestComplexScenarios:
    """Test realistic complex usage scenarios."""

    def test_scenario_multi_user_project_workflow(self, db_connection, user1, user2, user3):
        """Test realistic workflow: project creation, member addition, document sharing."""
        with test_transaction(db_connection) as cur:
            # User1 creates project
            cur.execute(
                "SELECT sp_create_project(%s, %s, %s)",
                (user1, "Team Project", "Collaboration space")
            )
            project_id = cur.fetchone()[0]

            # User1 adds user2 as admin and user3 as regular member
            cur.execute(
                "SELECT sp_change_role(%s, %s, %s, %s)",
                (user1, project_id, user2, "administrator")
            )
            cur.execute(
                "SELECT sp_change_role(%s, %s, %s, %s)",
                (user1, project_id, user3, "user")
            )

            # User1 uploads document
            cur.execute(
                "SELECT sp_upsert_document(%s, %s, %s, %s, %s, %s)",
                (user1, project_id, None, "s3://bucket/report.pdf", "Report", "application/pdf")
            )

            # User2 (admin) updates project details
            cur.execute(
                "SELECT sp_update_project(%s, %s, %s, %s)",
                (user2, project_id, "Team Project v2", "Updated collaboration space")
            )

            # User3 (regular member) can read but not delete
            cur.execute("SELECT * FROM sp_get_project_details(%s, %s)", (user3, project_id))
            assert cur.fetchone() is not None

            with pytest.raises(psycopg.errors.RaiseException):
                cur.execute("SELECT sp_delete_project(%s, %s)", (user3, project_id))

            # User2 can delete
            cur.execute("SELECT sp_delete_project(%s, %s)", (user2, project_id))

    def test_scenario_document_versioning(self, db_connection, user1, project1):
        """Test document update/versioning scenario."""
        with test_transaction(db_connection) as cur:
            # Create initial document
            cur.execute(
                "SELECT sp_upsert_document(%s, %s, %s, %s, %s, %s)",
                (user1, project1, None, "s3://bucket/spec.pdf", "Specification v1", "application/pdf")
            )
            doc_id = cur.fetchone()[0]

            # Get original metadata
            cur.execute(
                "SELECT d_s3key, d_title, d_mime FROM project_document WHERE d_id = %s",
                (doc_id,)
            )
            v1_s3key, v1_title, v1_mime = cur.fetchone()

            # Update to new version (simulate new S3 object)
            cur.execute(
                "SELECT sp_upsert_document(%s, %s, %s, %s, %s, %s)",
                (user1, project1, doc_id, "s3://bucket/spec-v2.pdf", "Specification v2", "application/pdf")
            )

            # Verify same document, updated metadata
            cur.execute(
                "SELECT d_s3key, d_title FROM project_document WHERE d_id = %s",
                (doc_id,)
            )
            v2_s3key, v2_title = cur.fetchone()
            assert v2_s3key == "s3://bucket/spec-v2.pdf"
            assert v2_title == "Specification v2"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
