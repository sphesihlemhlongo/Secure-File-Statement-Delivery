# System Architecture: Secure File Statement Delivery

## Overview
This system is designed to securely deliver sensitive financial statements to users. It prioritizes security, privacy, and ease of use, adhering to Capitec's branding and security standards.

## Core Components

### 1. Frontend (Client)
*   **Framework**: React (Vite)
*   **Styling**: Custom CSS using Capitec's brand colors (Red `#E51718`, Blue `#2F70EF`, White).
*   **Key Pages**:
    *   `Login`: ID-based authentication.
    *   `Register`: User registration with ID number.
    *   `Dashboard`: Main interface for uploading, viewing, and downloading statements.
*   **Features**:
    *   **Secure Uploads**: Validates PDF files before sending to backend.
    *   **Time-Limited Downloads**: "Request" button generates a secure link valid for 3 minutes.
    *   **Countdown Timer**: Visual indicator of download link validity.
    *   **Copy Link**: Allows sharing the secure link across devices.
    *   **AI Chatbot**: Floating assistant for security questions and system help.

### 2. Backend (Server)
*   **Framework**: FastAPI (Python)
*   **Runtime**: Uvicorn
*   **Key Responsibilities**:
    *   **Authentication**: JWT (JSON Web Tokens) for session management.
    *   **Authorization**: Role-based access (users can only see their own documents).
    *   **File Management**: Secure storage and retrieval of PDF files.
    *   **Token Generation**: HMAC-SHA256 signed tokens for secure, time-limited downloads.
    *   **AI Integration**: Google Gemini API for the chatbot.

### 3. Database (Data Persistence)
*   **Provider**: Supabase (PostgreSQL)
*   **Tables**:
    *   `users`: Stores user metadata (hashed ID, selector).
    *   `documents`: Stores document metadata (filename, path, owner, timestamp).
*   **Security**:
    *   **ID Hashing**: User ID numbers are hashed using Argon2 before storage.
    *   **ID Selectors**: Deterministic HMAC selectors allow looking up users without storing the raw ID or iterating through hashes.

### 4. Storage (File System)
*   **Type**: Local Filesystem (Volume mounted in Docker)
*   **Location**: `/app/uploads`
*   **Security**:
    *   Files are renamed with a timestamp and user ID to prevent collisions and guessing.
    *   Files are served via a streaming endpoint that validates the secure token.
    *   Direct file access is blocked; only the application can read files.

### 5. AI Service
*   **Provider**: Google Gemini (via `google-genai` SDK)
*   **Model**: `gemini-2.0-flash`
*   **Function**: Provides context-aware assistance to users. It knows the authenticated user's name and is prompted to act as a financial security assistant.

---

## Data Flow

### 1. User Registration
1.  User enters Name and ID Number.
2.  Frontend sends data to `/api/register`.
3.  Backend calculates:
    *   `id_selector` = HMAC(ID, Secret) -> Used for lookup.
    *   `id_hash` = Argon2(ID) -> Used for verification.
4.  Backend stores `name`, `id_selector`, and `id_hash` in Supabase `users` table.
5.  Backend returns a JWT access token.

### 2. Document Upload
1.  User selects a PDF file.
2.  Frontend sends file to `/api/documents` (Multipart/Form-Data).
3.  Backend validates:
    *   File type is `application/pdf`.
    *   Extension is `.pdf`.
    *   Size is < 10MB.
4.  Backend saves file to local disk with a safe name.
5.  Backend inserts metadata into Supabase `documents` table.

### 3. Secure Download Flow
1.  User clicks "Request" on Dashboard.
2.  Frontend calls `/api/documents/{id}/token`.
3.  Backend verifies ownership and generates a signed token:
    *   Payload: `doc_id|owner_id|expiry_timestamp`
    *   Signature: HMAC(Payload, Download_Secret)
4.  Backend returns token and expiry time (180 seconds).
5.  Frontend enables "Download" button and starts countdown.
6.  User clicks "Download".
7.  Frontend requests `/api/download?token={token}`.
8.  Backend verifies token signature and expiry.
9.  If valid, Backend streams the file from disk.

### 4. AI Chat
1.  User types a message.
2.  Frontend sends message + JWT to `/api/chat`.
3.  Backend identifies user from JWT (if logged in).
4.  Backend constructs prompt with user context ("The user's name is...").
5.  Backend calls Google Gemini API.
6.  Response is returned to Frontend.

---

## Security Measures

*   **Zero-Knowledge ID Storage**: Raw ID numbers are never stored. We use a "Selector + Hash" approach to allow login without exposing the ID in the database.
*   **Time-Limited Links**: Download links expire after 3 minutes, reducing the risk of leaked links being abused.
*   **HMAC Signatures**: Download tokens cannot be forged without the server's secret key.
*   **Path Traversal Protection**: File paths are strictly validated to ensure they remain within the upload directory.
*   **Argon2 Hashing**: Industry-standard password hashing for ID verification.
*   **Environment Variables**: All secrets (API keys, DB credentials, signing keys) are loaded from `.env`.

