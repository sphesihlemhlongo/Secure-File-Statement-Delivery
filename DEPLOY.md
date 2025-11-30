# Deployment Guide

This guide provides instructions for deploying the database and application to a production-like environment.

## 1. Database Deployment (Managed Service)

Using a managed database is recommended for production reliability and backups.

### Option A: Railway (PostgreSQL)
1.  Create a new project on [Railway](https://railway.app/).
2.  Add a **PostgreSQL** database service.
3.  Go to the "Variables" tab of the database service to find the `DATABASE_URL`.
    *   Format: `postgresql://postgres:password@containers-us-west-1.railway.app:5432/railway`

### Option B: AWS RDS (PostgreSQL)
1.  Log in to AWS Console and navigate to **RDS**.
2.  Create a **PostgreSQL** database instance (Free Tier is sufficient for testing).
3.  Configure "Public Access" to **No** (application must be in the same VPC) or **Yes** (restricted by Security Group IP).
4.  Construct the `DATABASE_URL`:
    *   `postgresql://<username>:<password>@<endpoint>:<port>/<dbname>`

## 2. Application Deployment

### Environment Variables
Set the following environment variables in your deployment platform (Railway, AWS ECS, Heroku, etc.):

| Variable | Description | Example Value |
| :--- | :--- | :--- |
| `DATABASE_URL` | Connection string for the DB | `postgresql://user:pass@host:5432/db` |
| `SECRET_KEY` | Key for signing JWTs | `long-random-string-1` |
| `SERVER_SELECTOR_SECRET` | Key for HMAC ID selector | `long-random-string-2` |
| `DOWNLOAD_SECRET` | Key for signing download tokens | `long-random-string-3` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT validity duration | `30` |
| `DOWNLOAD_TOKEN_TTL_SECONDS` | Download token validity | `180` |

### Secrets Management
*   **Railway**: Add these under the "Variables" tab. Railway encrypts them at rest.
*   **AWS**: Use **AWS Secrets Manager** or **Parameter Store**.
    *   In ECS task definitions, reference secrets via ARN.
    *   Do **not** put secrets in plain text in Dockerfiles or source code.

## 3. Docker Deployment

1.  **Build & Push**:
    ```bash
    # Login to container registry (e.g., Docker Hub, ECR)
    docker login

    # Build and tag
    docker build -t my-registry/secure-backend:latest ./Backend
    docker build -t my-registry/secure-frontend:latest ./frontend

    # Push
    docker push my-registry/secure-backend:latest
    docker push my-registry/secure-frontend:latest
    ```

2.  **Run**:
    Configure your orchestrator (Kubernetes, ECS, Railway) to run the containers.
    *   **Backend**: Expose port 8000. Connects to DB via `DATABASE_URL`.
    *   **Frontend**: Expose port 3000. Ensure it can reach the backend (configure API URL in frontend build or via runtime config).

## 4. Database Migration
On the first deployment, the application will automatically create tables (`init_db` in `main.py`). For production, consider using **Alembic** for managed migrations.
