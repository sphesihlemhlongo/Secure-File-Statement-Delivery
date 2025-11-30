import os

# Set dummy environment variables for testing
os.environ["SUPABASE_URL"] = "https://example.supabase.co"
os.environ["SUPABASE_KEY"] = "dummy_key"
os.environ["SECRET_KEY"] = "dummy_secret"
os.environ["SERVER_SELECTOR_SECRET"] = "dummy_selector_secret"
os.environ["DOWNLOAD_SECRET"] = "dummy_download_secret"
os.environ["Gemini"] = "dummy_gemini_key"

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import os
from datetime import datetime, timedelta

# Mock the dependencies before importing main
with patch('db.supabase') as mock_supabase, \
     patch('google.genai.Client') as mock_genai_client:
    from main import app, create_access_token, settings

client = TestClient(app)

# Mock Data
MOCK_USER_ID = "9001015009087"
MOCK_USER_NAME = "Test User"
MOCK_SELECTOR = "mock_selector"
MOCK_HASH = "mock_hash"
MOCK_TOKEN = "mock_jwt_token"

@pytest.fixture
def mock_db():
    with patch('main.supabase') as mock:
        # Create separate mocks for tables
        users_table = MagicMock()
        documents_table = MagicMock()
        
        def table_side_effect(name):
            if name == "users":
                return users_table
            if name == "documents":
                return documents_table
            return MagicMock()
            
        mock.table.side_effect = table_side_effect
        
        # Attach them to the mock object so tests can configure them
        mock.users_table = users_table
        mock.documents_table = documents_table
        
        yield mock

@pytest.fixture
def mock_fs():
    with patch('builtins.open', new_callable=MagicMock) as mock_open, \
         patch('os.path.exists') as mock_exists, \
         patch('os.makedirs') as mock_makedirs, \
         patch('os.remove') as mock_remove:
        yield mock_open, mock_exists, mock_makedirs, mock_remove

@pytest.fixture
def auth_headers():
    # Create a valid token for testing
    access_token = create_access_token(data={"sub": MOCK_SELECTOR})
    return {"Authorization": f"Bearer {access_token}"}

def test_register_user_success(mock_db):
    # Mock user check (user does not exist)
    mock_db.users_table.select.return_value.eq.return_value.execute.return_value.data = []
    
    # Mock user creation
    mock_db.users_table.insert.return_value.execute.return_value.data = [{
        "id": 1,
        "name": MOCK_USER_NAME,
        "id_selector": MOCK_SELECTOR,
        "id_hash": MOCK_HASH,
        "created_at": datetime.utcnow().isoformat()
    }]

    response = client.post("/api/register", json={
        "name": MOCK_USER_NAME,
        "id_number": MOCK_USER_ID
    })

    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"

def test_register_user_already_exists(mock_db):
    # Mock user check (user exists)
    mock_db.users_table.select.return_value.eq.return_value.execute.return_value.data = [{"id": 1}]

    response = client.post("/api/register", json={
        "name": MOCK_USER_NAME,
        "id_number": MOCK_USER_ID
    })

    assert response.status_code == 400
    assert response.json()["detail"] == "User already registered"

def test_login_success(mock_db):
    # Mock user lookup
    with patch('main.verify_password', return_value=True):
        mock_db.users_table.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [{
            "id": 1,
            "name": MOCK_USER_NAME,
            "id_selector": MOCK_SELECTOR,
            "id_hash": MOCK_HASH,
            "created_at": datetime.utcnow().isoformat()
        }]

        response = client.post("/api/login", data={
            "username": MOCK_USER_ID,
            "password": MOCK_USER_ID
        })

        assert response.status_code == 200
        assert "access_token" in response.json()

def test_login_invalid_credentials(mock_db):
    # Mock user lookup
    with patch('main.verify_password', return_value=False):
        mock_db.users_table.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [{
            "id": 1,
            "name": MOCK_USER_NAME,
            "id_selector": MOCK_SELECTOR,
            "id_hash": MOCK_HASH,
            "created_at": datetime.utcnow().isoformat()
        }]

        response = client.post("/api/login", data={
            "username": MOCK_USER_ID,
            "password": "wrong_password"
        })

        assert response.status_code == 401

def test_upload_document_success(mock_db, mock_fs, auth_headers):
    mock_open, mock_exists, _, _ = mock_fs
    
    # Mock user lookup for auth
    mock_db.users_table.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [{
        "id": 1,
        "name": MOCK_USER_NAME,
        "id_selector": MOCK_SELECTOR,
        "id_hash": MOCK_HASH,
        "created_at": datetime.utcnow().isoformat()
    }]

    # Mock document insert
    mock_db.documents_table.insert.return_value.execute.return_value.data = [{
        "id": 101,
        "filename": "test.pdf",
        "filepath": "/app/uploads/test.pdf",
        "owner_id": 1,
        "uploaded_at": datetime.utcnow().isoformat()
    }]

    # Mock file system
    mock_exists.return_value = True

    files = {'file': ('test.pdf', b'%PDF-1.4 content', 'application/pdf')}
    response = client.post("/api/documents", files=files, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test.pdf"
    assert data["id"] == 101

def test_upload_document_invalid_type(mock_db, auth_headers):
    # Mock user lookup for auth
    mock_db.users_table.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [{
        "id": 1,
        "name": MOCK_USER_NAME,
        "id_selector": MOCK_SELECTOR,
        "id_hash": MOCK_HASH,
        "created_at": datetime.utcnow().isoformat()
    }]

    files = {'file': ('test.txt', b'text content', 'text/plain')}
    response = client.post("/api/documents", files=files, headers=auth_headers)

    assert response.status_code == 400
    assert response.json()["detail"] == "Only PDF files are allowed"

def test_request_download_token_success(mock_db, auth_headers):
    # Mock user lookup for auth
    mock_db.users_table.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [{
        "id": 1,
        "name": MOCK_USER_NAME,
        "id_selector": MOCK_SELECTOR,
        "id_hash": MOCK_HASH,
        "created_at": datetime.utcnow().isoformat()
    }]

    # Mock document lookup (note double eq)
    mock_db.documents_table.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [{
        "id": 101,
        "filename": "test.pdf",
        "filepath": "/app/uploads/test.pdf",
        "owner_id": 1,
        "uploaded_at": datetime.utcnow().isoformat()
    }]

    response = client.post("/api/documents/101/token", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert "expires_in" in data
    assert data["expires_in"] == 180

def test_download_document_success(mock_db, mock_fs):
    mock_open, mock_exists, _, _ = mock_fs
    
    # 1. Generate a valid token first
    from main import make_download_token
    token = make_download_token(101, 1)

    # 2. Mock document lookup (note double eq)
    mock_db.documents_table.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [{
        "id": 101,
        "filename": "test.pdf",
        "filepath": "/app/uploads/test.pdf",
        "owner_id": 1,
        "uploaded_at": datetime.utcnow().isoformat()
    }]

    # 3. Mock file existence and read
    mock_exists.return_value = True
    mock_open.return_value.__enter__.return_value.read.return_value = b'%PDF-1.4 content'
    # For streaming response, we need to mock iteration
    mock_open.return_value.__enter__.return_value.__iter__.return_value = [b'%PDF-1.4 content']

    response = client.get(f"/api/download?token={token}")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == 'attachment; filename="test.pdf"'

def test_chat_endpoint(mock_db, auth_headers):
    # Mock user lookup for auth (optional but good to have context)
    mock_db.users_table.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [{
        "id": 1,
        "name": MOCK_USER_NAME,
        "id_selector": MOCK_SELECTOR,
        "id_hash": MOCK_HASH,
        "created_at": datetime.utcnow().isoformat()
    }]

    # Mock the GenAI client call
    # We need to patch the client instance on the main module
    with patch('main.client.models.generate_content') as mock_generate:
        mock_generate.return_value.text = "Hello! I can help you with security."
        
        response = client.post("/api/chat", json={"message": "Hi"}, headers=auth_headers)
        
        assert response.status_code == 200
        assert response.json()["response"] == "Hello! I can help you with security."

def test_download_document_invalid_token():
    response = client.get("/api/download?token=invalid_token")
    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid or expired token"
