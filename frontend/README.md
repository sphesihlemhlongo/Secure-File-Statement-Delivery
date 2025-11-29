# Secure Statement Delivery - Frontend

This is the React frontend for the Secure Statement Delivery application.

## Local Development

1.  Install dependencies:
    ```bash
    npm install
    ```

2.  Start the development server:
    ```bash
    npm run dev
    ```
    The app will be available at `http://localhost:3000`.

## Features

*   **Register**: Create a new account with Name and ID Number.
*   **Login**: Access your account using your ID Number.
*   **Dashboard**:
    *   View list of uploaded documents.
    *   Upload new PDF documents.
    *   Securely download documents (uses short-lived tokens).

## Configuration

The API URL is configured in `src/pages/Login.jsx`, `src/pages/Register.jsx`, and `src/pages/Dashboard.jsx` as `http://localhost:8000/api`.
