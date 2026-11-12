# Apivendas – End‑User Guide

## Overview
`apivendas` is a small marketplace‑automation tool that scrapes product offers from **Mercado Libre**, formats an affiliate message and can post it automatically to a WhatsApp group.

## Prerequisites (already covered in the individual README files)
- **Backend (Django)** – Python 3.11+, PostgreSQL running locally (or remote). See `backend/README.md`.
- **Frontend (React + Vite)** – Node 20+, pnpm. See `frontend/README.md`.
- **WhatsApp gateway** – Evolution API (Docker) or any compatible service. See the *WhatsApp Integration* section below.

---
## 1️⃣ Starting the stack
1. **Database** – Ensure the PostgreSQL daemon is running (the background task `task‑568` does this automatically). If you stopped it, run:
   ```powershell
   .\pgsql\pgsql\bin\postgres.exe -D "C:\projetos wilson\apivendas\pgsql\data" -p 5432
   ```
2. **Backend** – From the project root:
   ```powershell
   cd backend
   .\venv\Scripts\activate
   python manage.py runserver 0.0.0.0:8000
   ```
   The API will listen on **http://localhost:8000/**.
3. **Frontend** – In another terminal:
   ```powershell
   cd frontend
   pnpm dev
   ```
   Open **http://localhost:5173/** in a browser.
4. **WhatsApp gateway (optional, required for automatic posting)** – Start Evolution API:
   ```bash
   docker run -d -p 8080:8080 ghcr.io/evolution-api/evolution-api:latest
   ```
   Wait for the container logs, scan the QR‑code with your phone and keep the session active.

---
## 2️⃣ Configuring WhatsApp inside the UI
1. Click the **⚙️ Settings** button (top‑right) → *WhatsApp Configuration*.
2. **Phone number** – Enter the number that you used to login to WhatsApp (including country code, e.g. `55 11 98765‑4321`).
3. **Add groups** – Press **+** and type the *group JID* (ends with `@g.us`).
   - You can obtain the JID by opening the group in WhatsApp Web, clicking the group name → *Group info* → *Group ID* (or use the Evolution API endpoint `/groups`).
4. Choose one group as **Active** – the selected group will receive every automatic publication.
5. Press **Save** – the data is stored in `localStorage`; the same configuration will be loaded next time you open the app.
> **Note:** The frontend only stores the config locally. For multi‑device usage you can expose a small API (`/whatsapp/config/`) on the backend and replace the `localStorage` calls – see the “Future improvements” section.

---
## 3️⃣ Using the application
### Searching offers
1. In the **Dashboard** type a search term (e.g. `smartphone`).
2. Press **Buscar** – the backend returns a list of offers.
3. Each card shows a **Ver no ML** button. **Now it opens the exact product page** (direct URL) instead of the generic search list.
   - If the product does not have a known direct URL, the system falls back to a safe Mercado Libre search query.

### Publishing an offer
1. Click **Publicar** on a card.
2. In the modal you can:
   - Edit the affiliate link (the system already inserts your `ML` affiliate token).
   - Choose a *custom caption*.
   - Press **Postar no WhatsApp**.
3. The modal will automatically use the **Active group** you set in the configuration and send the image + caption via the Evolution API.
   - A toast notification tells you if the request succeeded (`status 200`) or failed (check the console for the error response).

### Dispatch next offer (batch mode)
- After publishing a few offers you can click **Disparar Próxima**. The backend will pick the next pending offer and publish it using the same WhatsApp configuration.
- You can set an interval (30 min, 1 h, etc.) with a simple **cron** on the backend (`celery beat` or a custom management command) – not shipped yet, but the endpoint is ready.

---
## 4️⃣ Troubleshooting common issues
| Symptom | Likely cause | Fix |
|---|---|---|
| *“Page not found”* when clicking **Ver no ML** | Missing entry in `DIRECT_LINKS` map | Add the product ID and real URL to the map in `frontend/src/components/ProductCard.jsx` (or report to the maintainer). |
| *WhatsApp messages not arriving* | Evolution API not running / QR‑code not scanned | Run `docker ps` to see the container, view its logs (`docker logs <container>`), scan the QR‑code again. |
| *`WHATSAPP_API_ENABLED=False`* in the UI | The feature is hidden deliberately | Set `VITE_WHATSAPP_ENABLED=true` in `frontend/.env.local` and reload the page. |
| *Database connection error* | PostgreSQL daemon stopped | Restart task‑568 or run the command shown in **Starting the stack**. |
| *CORS error* | Backend missing origin | Add `http://localhost:5173` to `CORS_ALLOWED_ORIGINS` in `backend/settings.py`. |

---
## 5️⃣ Future improvements (optional for you)
- **Server‑side persistence of WhatsApp config** – expose `/whatsapp/config/` endpoints and store the data in the database.
- **Celery scheduler** – automate the dispatch‑next‑offer flow with configurable intervals.
- **Docker Compose** – single‑command bring‑up of PostgreSQL, Django, Vite, and Evolution API.
- **Multi‑language support** – add i18n strings for Portuguese/English.

---
**That’s it!** You now have a fully working stack, documentation for developers (see the `backend/README.md` and `frontend/README.md`) and a user guide on how to operate the system and send messages to WhatsApp groups.

_Last updated: 2026‑11‑11_