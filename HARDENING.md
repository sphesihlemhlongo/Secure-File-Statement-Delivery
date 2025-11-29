# Security Hardening Guide

This document details prioritized steps to harden the Secure Statement Delivery application for production.

## 1. Critical Hardening Steps (Priority: High)

### HTTPS / TLS
*   **Requirement**: All traffic must be encrypted.
*   **Action**: Deploy behind a reverse proxy (Nginx, Traefik, AWS ALB) that handles SSL termination.
*   **Why**: Protects JWTs and download tokens from interception.

### Secrets Management
*   **Requirement**: No hardcoded secrets.
*   **Action**: Rotate `SECRET_KEY`, `SERVER_SELECTOR_SECRET`, and `DOWNLOAD_SECRET`. Use a secrets manager (AWS Secrets Manager, HashiCorp Vault) to inject them as environment variables at runtime.

### Database Security
*   **Requirement**: Least privilege access.
*   **Action**: Use a managed DB (RDS). Ensure the application user only has CRUD permissions on specific tables, not DDL permissions. Enforce SSL connections to the DB.

## 2. Application Security (Priority: Medium)

### Rate Limiting
*   **Action**: Implement rate limiting on `/api/login` and `/api/register` (e.g., using `slowapi` or Nginx) to prevent brute-force attacks.

### CORS Tightening
*   **Action**: Restrict `allow_origins` in `main.py` to the specific frontend domain (e.g., `https://app.example.com`) instead of `["*"]`.

### File Upload Security
*   **Action**:
    *   **Virus Scanning**: Integrate ClamAV to scan files upon upload before moving them to permanent storage.
    *   **Content Type Validation**: Use `python-magic` to verify file type by content, not just extension.

### Secure Headers
*   **Action**: Add security headers (HSTS, X-Frame-Options, X-Content-Type-Options, CSP) using middleware.

## 3. Infrastructure & Scalability (Priority: Low/Long-term)

### S3 Pre-signed URLs
*   **Action**: Move file storage to AWS S3. Instead of streaming files through the backend, generate pre-signed GET URLs with short expiry.
*   **Why**: Offloads bandwidth from the application server and leverages S3's security and durability.

### Logging & Monitoring
*   **Action**:
    *   **Redaction**: Ensure logs do not contain PII (ID numbers, names) or tokens.
    *   **Audit**: Log all access to `/api/download` (who downloaded what and when).

## 4. Risk & Mitigation Matrix

| Risk | Severity | Mitigation Strategy |
| :--- | :--- | :--- |
| **Token Theft** | High | Short TTL (15 mins), HTTPS enforcement, One-time use tokens (optional). |
| **ID Enumeration** | Medium | Use deterministic HMAC `id_selector` instead of raw IDs in DB lookups. |
| **Malicious Upload** | High | Validate PDF mime-type, enforce size limits, virus scan (future), rename files on save. |
| **DB Leak** | Critical | Encrypt sensitive columns (if needed), strict firewall rules, no public DB access. |
| **DoS Attack** | Medium | Rate limiting on auth endpoints, file size limits, CDN for static assets. |
