# Testing Strategy

This document outlines the testing strategy for the Secure Statement Delivery application, including manual smoke tests, automated test plans, and end-to-end scenarios.

## 1. Manual Smoke Tests (Curl Sequences)

These tests verify the core functionality of the API using `curl`. Ensure the backend is running at `http://localhost:8000`.

### Authentication Flow
1.  **Register**:
    ```bash
    curl -X POST "http://localhost:8000/api/register" -H "Content-Type: application/json" -d '{"name": "Test User", "id_number": "9001015009087"}'
    ```
    *Expected*: 200 OK, returns `access_token`.

2.  **Login**:
    ```bash
    curl -X POST "http://localhost:8000/api/login" -H "Content-Type: application/x-www-form-urlencoded" -d "username=9001015009087&password=9001015009087"
    ```
    *Expected*: 200 OK, returns `access_token`.

### Document Flow
*Requires `ACCESS_TOKEN` from login.*

3.  **Upload PDF**:
    ```bash
    curl -X POST "http://localhost:8000/api/documents" -H "Authorization: Bearer $ACCESS_TOKEN" -F "file=@test.pdf;type=application/pdf"
    ```
    *Expected*: 200 OK, returns document metadata.

4.  **List Documents**:
    ```bash
    curl -X GET "http://localhost:8000/api/documents" -H "Authorization: Bearer $ACCESS_TOKEN"
    ```
    *Expected*: 200 OK, JSON list of documents.

5.  **Get Download Token**:
    ```bash
    curl -X POST "http://localhost:8000/api/documents/1/token" -H "Authorization: Bearer $ACCESS_TOKEN"
    ```
    *Expected*: 200 OK, returns `token`.

6.  **Download File**:
    ```bash
    curl -v "http://localhost:8000/api/download?token=$DOWNLOAD_TOKEN" --output downloaded.pdf
    ```
    *Expected*: 200 OK, file content streamed.

## 2. Automated Test Plan (Future Work)

### Unit Tests (`pytest`)
*   **Models**: Verify `User` and `Document` creation and constraints.
*   **Utils**: Test `create_selector` (determinism), `verify_download_token` (expiry, signature).
*   **Auth**: Test password hashing and JWT generation.

### Integration Tests (`pytest` + `TestClient`)
*   **Register/Login**: Verify duplicate registration fails, invalid ID format fails.
*   **Upload**: Verify non-PDFs are rejected, file size limits are enforced.
*   **Download**: Verify expired tokens are rejected, tokens for wrong user/doc are rejected.

### End-to-End (E2E) Tests (Cypress/Playwright)
*   **User Journey**: Register -> Login -> Dashboard -> Upload -> Download.
*   **Error Handling**: Verify UI displays errors for invalid login or upload failures.

## 3. Security Test Cases
*   **SQL Injection**: Attempt to inject SQL in login fields (should fail due to ORM).
*   **Path Traversal**: Attempt to upload files with names like `../../etc/passwd` (should be sanitized).
*   **ID Enumeration**: Verify that `id_selector` prevents guessing other user IDs.
*   **Token Replay**: Verify download tokens cannot be modified without invalidating signature.
