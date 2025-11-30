# Secure Statement Delivery

A secure file delivery system with a React frontend and FastAPI backend.

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

## Production Checklist

Before deploying to production, ensure the following:

1.  **Secrets Management**:
    *   Replace `SECRET_KEY`, `SERVER_SELECTOR_SECRET`, and `DOWNLOAD_SECRET` in `docker-compose.yml` (or your deployment env) with strong, random strings.
    *   Do not commit `.env` files or secrets to version control.
    *   Use a secrets manager (e.g., AWS Secrets Manager, HashiCorp Vault) if possible.

2.  **Database**:
    *   Use a managed PostgreSQL instance (e.g., RDS) instead of the containerized DB.
    *   Set a strong password for the database user.

3.  **HTTPS/TLS**:
    *   **Mandatory**: Serve the application over HTTPS. The download tokens and JWTs are sensitive.
    *   Configure a reverse proxy (Nginx, Traefik, or Load Balancer) to handle SSL termination.

4.  **Storage**:
    *   For scalability, switch from local disk storage (`uploads` volume) to an object store like AWS S3 or Azure Blob Storage.
    *   Update the backend to generate pre-signed URLs for downloads instead of streaming through the API.

5.  **Security**:
    *   Enable virus scanning for uploaded files (e.g., ClamAV).
    *   Rate limit API endpoints to prevent abuse.
    *   Set `ACCESS_TOKEN_EXPIRE_MINUTES` to a shorter duration (e.g., 15 mins) and implement refresh tokens if needed.

6.  **Monitoring**:
    *   Set up logging and monitoring (e.g., Prometheus, Grafana, ELK stack) to track errors and performance.
