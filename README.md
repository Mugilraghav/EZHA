# EZHA

EZHA is a premium Indian marketplace for beauty, bridal, fashion, and artisan services. This repository establishes the foundation for a scalable startup product, starting with a strong landing page, clean backend structure, and modular frontend architecture.

## Quick start

1. Create and activate a virtual environment:
   ```bash
  python -m venv .venv
  source .venv/bin/activate
  ```
2. Install dependencies and create your local environment file:
  ```bash
   python -m pip install -r requirements.txt
  cp .env.example .env
   ```
3. Start the development server:
   ```bash
   python backend/run.py
   ```
4. Open http://localhost:5000/ (in Codespaces, forward port `5000` from the Ports panel).

The local default uses SQLite at `instance/ezha.db` and stores uploaded portfolio images under `instance/portfolio/`. The `instance/` directory is excluded from Git. Development seeds demo accounts: `customer` / `demo123`, `ananya` / `demo123`, and `admin` / `demo123`. Never use these demo accounts in production.

## Project structure

```text
backend/
  __init__.py
  app/
    __init__.py
    config.py
    routes/
      __init__.py
      public.py
  run.py
  tests/
    test_public_routes.py
frontend/
  index.html
  css/
  js/
  pages/
  docs/
```

## Architecture

- Flask application factory for modular backend growth.
- Frontend served from the `frontend` folder as static assets.
- Environment variables defined in `.env.example`.
- Role-specific experiences for customers, artisans, and admins.
- Customer and artisan accounts are stored in SQLAlchemy-backed database records; passwords are hashed.
- Default database is a persistent SQLite file at `instance/ezha.db`, which requires no paid service or separate database server.
- Set `DATABASE_URL` to a hosted PostgreSQL connection string to use a free hosted database tier such as Supabase.
- Artisan portfolio uploads use Supabase Storage when configured; local disk remains the development fallback.

## Phase 1 completed

- EZHA branding and visual identity
- Responsive navigation and premium landing page
- Category discovery section
- Featured artist cards
- How-it-works section
- Trust and conversion features
- CTA and footer structure
- CSS system with responsive design

## Role portals

- Landing page: `/`
- Sign in: `/login`
- Registration: `/register`
- Customer services: `/customer/services`
- Artisan workspace: `/artisan/dashboard`
- Admin monitoring: `/admin/dashboard`

Registration supports customers and artisans. Login requires selecting the matching account type; successful login redirects each role to its own portal. Admin accounts are created out of band and cannot be registered through the public form.

Demo accounts (username and password):

| Role | Username | Password |
| --- | --- | --- |
| Customer | `customer` | `demo123` |
| Artisan | `ananya` | `demo123` |
| Admin | `admin` | `demo123` |

The artisan workspace supports portfolio image uploads, customer browsing, bookings, and payment status. Customer and artisan profiles, categorized portfolio work, and bookings persist in the configured database. Payment settlement requires Razorpay credentials.

To use a hosted free PostgreSQL database, create a project with your provider, copy its PostgreSQL connection URL into `.env` as `DATABASE_URL`, and keep `.env` private. `psycopg2-binary` is already included. SQLite is used automatically when `DATABASE_URL` is not set.

For portfolio images, create a Supabase Storage bucket named `artisan-portfolio` and set it to public because artisan work is intended to be visible in customer listings. Configure `SUPABASE_URL`, `SUPABASE_STORAGE_BUCKET`, and `SUPABASE_SERVICE_ROLE_KEY` in the server environment. The service-role key is used only by Flask; never put it in frontend code or expose it to customers. Production uploads are rejected when storage settings are missing instead of silently saving to ephemeral local disk.

To accept real payments, add Razorpay test keys as `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` in `.env` first. Verify the full flow in Razorpay test mode before adding live keys. Without keys, checkout remains available but order creation reports that payments are not configured; it will not mark a booking as paid.

## Launch checklist

### 1. Verify locally

Run the regression suite and start the app:

```bash
python -m pytest -q
python backend/run.py
```

Test customer registration, artisan registration, portfolio upload, customer filtering and booking, and the admin dashboard. Demo accounts are for local testing only.

### 2. Prepare the production environment

Choose a host that runs Python WSGI applications and supports persistent PostgreSQL connectivity and persistent file storage. In that host's private environment settings, configure:

- `APP_ENV=production`
- `SEED_DEMO_USERS=false`
- `JWT_SECRET` as a random secret at least 32 characters long
- `DATABASE_URL` as your managed PostgreSQL connection URL
- `SUPABASE_URL`, `SUPABASE_STORAGE_BUCKET=artisan-portfolio`, and `SUPABASE_SERVICE_ROLE_KEY` for persistent artisan photos
- `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` using Razorpay test keys for initial verification

Generate a JWT secret locally with `python -c "import secrets; print(secrets.token_hex(32))"`. Put the result directly into the host's private environment settings; do not commit `.env` or share the secret in chat. `.env` is ignored by Git.

Build/install command:

```bash
python -m pip install -r requirements.txt
```

Production start command:

```bash
gunicorn --bind "0.0.0.0:${PORT:-8000}" "backend.app:create_app()"
```

### Deploying with Render

The repository includes `render.yaml` with `rootDir: .`, so Render installs from the repository root where `requirements.txt` lives. To use it, push the file to GitHub and create a Render Blueprint from that repository. Render will prompt for the database URL, Supabase URL/service key, and Razorpay keys as private environment values.

If you already created a Render Web Service and see `Could not open requirements file`, open **Settings → Build & Deploy** and clear **Root Directory** (or set it to `.`). Keep the build command as `python -m pip install -r requirements.txt`, then trigger a new deploy. Do not set Root Directory to `backend`; the dependency file is in the repository root.

### 3. Create your admin account

Open the host's private shell/console with the same production environment variables and run:

```bash
python -m backend.create_admin
```

The command prompts for the admin identity and password without echoing the password. Admin accounts cannot be created through public registration. Keep those credentials in your own password manager.

### 4. Verify before going public

Use Razorpay test mode first. Confirm customer registration, artisan onboarding, image upload from the deployed host, filtering, booking, successful payment verification, and the matching order on artisan/admin dashboards. Only then change the host's Razorpay variables to live keys.

The app's free local SQLite and disk storage are for development, not a multi-user hosted deployment. Use managed PostgreSQL and Supabase Storage for launch. Keep `.env` and all provider credentials private.

## Remaining before production

- Add a database migration tool before changing live schemas.
- Move the remaining hard-coded demo catalog and legacy demo bookings into managed records.
- Use managed object storage if the host cannot guarantee durable `UPLOAD_FOLDER` storage.
- Set up database backups, monitoring, rate limits, privacy/terms, refunds, and customer support procedures.
- Configure and fully test Razorpay in test mode before enabling live charges.

## Notes

This is an MVP launch foundation, not a complete production operations package. Production startup rejects the default JWT secret and skips demo-user seeding unless explicitly enabled. Use a separate production database, create an admin with `python -m backend.create_admin`, configure persistent media storage, and complete the remaining checks above before accepting real customers.
