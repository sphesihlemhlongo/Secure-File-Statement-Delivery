| Risk | Severity | Mitigation Strategy |
| :--- | :--- | :--- |
| **Token Theft** | High | Short TTL (15 mins), HTTPS enforcement, One-time use tokens (optional). |
| **ID Enumeration** | Medium | Use deterministic HMAC `id_selector` instead of raw IDs in DB lookups. |
| **Malicious Upload** | High | Validate PDF mime-type, enforce size limits, virus scan (future), rename files on save. |
| **DB Leak** | Critical | Encrypt sensitive columns (if needed), strict firewall rules, no public DB access. |
| **DoS Attack** | Medium | Rate limiting on auth endpoints, file size limits, CDN for static assets. |
