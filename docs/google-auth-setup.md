# Enable Google sign-in

Local development login is enabled for now, as requested. Google credentials are optional until you are ready to add them.

1. Create a Google Cloud OAuth client with application type **Web application**. Configure the consent screen and its audience; add test users if the application is in testing.
2. Add this exact authorized redirect URI for the local frontend:

   ```text
   http://localhost:5184/api/v1/auth/google/callback
   ```

3. Add credentials and allowed staff accounts to `backend/.env` when running locally. For Docker, use root `.env`, which Compose reads.

   ```dotenv
   ATTENDANCE_GOOGLE_CLIENT_ID=your-client-id
   ATTENDANCE_GOOGLE_CLIENT_SECRET=your-client-secret
   ATTENDANCE_PUBLIC_URL=http://localhost:5184
   ATTENDANCE_ALLOWED_STAFF_EMAILS=["your-email@example.com"]
   # Optional: allow all verified accounts in a staff domain instead.
   ATTENDANCE_ALLOWED_EMAIL_DOMAINS=[]
   ```

4. Restart the backend. The login page will offer Google when its provider is configured.
5. Before deploying, set the real HTTPS public URL, register its exact callback URL with Google, disable development login, enable secure cookies, and set a strong private session secret. Configure the authorized staff emails or domains.

The client secret belongs only on the backend. Never expose it in frontend environment variables or commit real credentials.

The current starter uses signed, HTTP-only session cookies. Logout clears the browser cookie; it does not revoke a stolen copy server-side. Rotating the signing secret invalidates all existing sessions.

Reference: [Google's web-server OAuth documentation](https://developers.google.com/identity/protocols/oauth2/web-server), checked 2026-10-09.
