# Secure Statement Delivery

A secure file delivery system with a React frontend and FastAPI backend.

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for a detailed overview of the system components and data flow.

## Quick Start (Docker)

1.  **Prerequisites**: Ensure Docker and Docker Compose are installed.

2.  **Run the application**:
    ```bash
    docker-compose up --build
    ```

3.  **Access the services**:
    *   **Frontend**: http://localhost:3000
    *   **Backend API**: http://localhost:8000
    *   **API Docs**: http://localhost:8000/docs

## Local Development (Manual)

If you prefer to run the services locally without Docker:

### Prerequisites
*   Python 3.9+
*   Node.js 18+
*   PostgreSQL (a Supabase project)

### 1. Backend Setup
1.  Navigate to the backend directory:
    ```bash
    cd Backend
    ```
2.  Create a virtual environment and activate it:
    ```bash
    python -m venv venv
    # Windows
    .\venv\Scripts\activate
    # Linux/Mac
    source venv/bin/activate
    ```
3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4.  Configure Environment:
    *   Copy `.env.example` to `.env`.
    *   Update `DATABASE_URL` to point to your local Postgres or Supabase instance.
    *   Set `Gemini` API key in `.env`.
5.  Run the server:
    ```bash
    uvicorn main:app --reload
    ```

### 2. Frontend Setup
1.  Navigate to the frontend directory:
    ```bash
    cd frontend
    ```
2.  Install dependencies:
    ```bash
    npm install
    ```
3.  Run the development server:
    ```bash
    npm run dev
    ```
4.  Access the app at `http://localhost:5173` (or the port shown in terminal).

## Manual Verification (Smoke Test)

## Manual Verification (Smoke Test)

You can verify the backend endpoints using `curl` or the Swagger UI at `/docs`.

### 1. Register
```bash
curl -X POST "http://localhost:8000/api/register" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test User", "id_number": "9001015009087"}'
```
*Response: `{"access_token": "...", "token_type": "bearer"}`*

### 2. Login
```bash
curl -X POST "http://localhost:8000/api/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=9001015009087&password=9001015009087"
```
*Response: `{"access_token": "...", "token_type": "bearer"}`*

### 3. Upload Document
Replace `<TOKEN>` with the access token from login.
```bash
# Create a dummy PDF
echo "dummy content" > test.pdf

curl -X POST "http://localhost:8000/api/documents" \
  -H "Authorization: Bearer <TOKEN>" \
  -F "file=@test.pdf;type=application/pdf"
```

### 4. List Documents
```bash
curl -X GET "http://localhost:8000/api/documents" \
  -H "Authorization: Bearer <TOKEN>"
```
*Response: `[{"id": 1, "filename": "test.pdf", ...}]`*

### 5. Request Download Token
Replace `<DOC_ID>` with the ID from the list.
```bash
curl -X POST "http://localhost:8000/api/documents/<DOC_ID>/token" \
  -H "Authorization: Bearer <TOKEN>"
```
*Response: `{"token": "...", "expires_in": 180}`*

### 6. Download File
Replace `<DOWNLOAD_TOKEN>` with the token received.
```bash
curl -v -X GET "http://localhost:8000/api/download?token=<DOWNLOAD_TOKEN>" \
  --output downloaded.pdf
```
