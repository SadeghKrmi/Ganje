<p align="center">
  <img src="static/assets/img/ganje-icon-transparent.png" alt="Ganje logo" width="140" />
</p>

# Ganje – Research Tracking

**Ganje** (Persian: **گنجه**) is the word for an old, valued treasury box—the kind
of chest people used to lock away things worth keeping. In the world of large
language models, the tokens we spend and the generated output we care about are
a lot like that: easy to lose in a chat scroll, hard to reuse with confidence.
This project is a place to **keep** those analyses: stored, **versioned**, and
ready to revisit or re-run when your codebase moves on.

A Django + Bootstrap 5 web application for documenting, versioning, and
re-running AI-powered codebase analyses.

---

## Quick start with Podman

### Prerequisites

```bash
# Install podman-compose if not already present
pip3 install podman-compose
# or: dnf install podman-compose  (Fedora/RHEL)
# or: apt install podman-compose  (Ubuntu/Debian)
```

### Run

```bash
cp .env.example .env          # adjust secrets as needed
podman-compose up --build -d
# open http://localhost:8000
```

### Useful commands

```bash
podman-compose logs -f web    # follow app logs
podman-compose down           # stop containers
podman-compose down -v        # stop + delete volumes (resets DB)
podman-compose exec web python manage.py createsuperuser
```

> **Note:** The `docker-compose.yml` uses fully qualified image names
> (`docker.io/library/postgres:16-alpine`) so Podman resolves them without
> needing unqualified-search registries configured in
> `/etc/containers/registries.conf`.

---

## Authentication

Ganje requires login for **all** pages (every artifact and version is private to
authenticated users). Login is **email + password** only.

### First-time superuser

On first start, the entrypoint will auto-create a Django superuser if these
environment variables are set in `.env`:

```bash
DJANGO_SUPERUSER_EMAIL=admin@ganje.local
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_PASSWORD=changeme123
```

Open <http://localhost:8000/login/> and sign in with the email + password above.

### Managing additional users

User CRUD is handled through the Django admin at
<http://localhost:8000/admin/auth/user/>. After creating a user there, make sure
to set their **email** field — that's how they sign in. Set `is_staff = True` if
you also want them to access the admin site.

### Account self-service

Logged-in users can:

- Update their name and email at **/account/**
- Change their password at **/account/password/**

Sign out via the avatar dropdown in the top-right of the navbar.

---

## Local dev (no container)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser   # optional
python manage.py runserver
```

SQLite is used automatically when `DATABASE_URL` is not set.

---

## Features

| Feature | Details |
|---|---|
| **Research Artifacts** | Named topics with description, category, codebase, tags and status |
| **Versioned Analyses** | Each artifact stores unlimited versions; each version records the prompt, AI response, model used, and codebase git ref |
| **Markdown rendering** | Full CommonMark with fenced code blocks, tables, task lists |
| **Live preview** | Write/preview toggle while adding an analysis |
| **Dark mode** | Auto-detects system preference, toggle in navbar |
| **Full-text search** | Filter by title, category, codebase, tag, or description |
| **Stats dashboard** | KPIs, top categories, top tags, recent analyses |
| **Email authentication** | Login by email + password; protected by `LoginRequiredMiddleware` |
| **Account self-service** | Profile editing & password change at `/account/` |
| **Django Admin** | Full CRUD via `/admin/` (incl. user management) |
| **Offline assets** | All CSS/JS vendor files served locally — no CDN dependency |

---

## Vendor assets (offline)

All third-party assets are bundled under `static/vendor/` and served by
Whitenoise — no internet connection is needed at runtime.

| Library | Version | Location |
|---|---|---|
| Bootstrap | 5.3.8 | `static/vendor/bootstrap/` |
| Bootstrap Icons | 1.11.3 | `static/vendor/bootstrap-icons/` |
| Highlight.js | 11.9.0 | `static/vendor/highlightjs/` |
| marked | 12.0.0 | `static/vendor/marked/` |

To update a library, re-download the files into the same paths and rebuild
the container image (`podman-compose up --build`).

---

## Data model

```
ResearchArtifact          ResearchVersion
─────────────────         ──────────────────────
id (PK)                   id (PK)
uid (UUID)                artifact → FK
title                     version_number
description               prompt          ← the AI prompt
category                  analysis        ← markdown response
codebase                  model_used
tags (M2M → Tag)          codebase_ref    ← git hash/branch
status                    notes
created_at                created_at
updated_at
```
