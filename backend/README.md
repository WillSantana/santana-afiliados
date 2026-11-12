# Backend – API Server (Django)

## Prerequisites
| OS | Required Tools |
|---|---|
| **Linux** | • Python 3.11 (or newer) <br> • `git` (optional) <br> • `make` (optional) |
| **Windows** | • Python 3.11 (or newer) <br> • PowerShell (default) |

## Quick Start (Linux & Windows)
1. **Clone the repository** (if you haven't already):
   ```bash
   git clone https://github.com/yourusername/apivendas.git
   cd apivendas/backend
   ```
2. **Create a virtual environment**
   - Linux/macOS:
     ```bash
     python -m venv venv
     source venv/bin/activate
     ```
   - Windows (PowerShell):
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```
3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
4. **Configure environment variables**
   - Copy the example file:
     ```bash
     cp .env.example .env   # Linux/macOS
     copy .env.example .env # Windows PowerShell
     ```
   - Edit `.env` and set the values you need. Important keys for WhatsApp integration:
     ```text
     WHATSAPP_API_ENABLED=True   # set to False while testing without Evolution API
     WHATSAPP_API_URL=http://localhost:8080/message/sendMedia/instancia-santana
     WHATSAPP_API_TOKEN=your_api_key_here
     WHATSAPP_GROUP_ID=1234567890@g.us   # leave empty; you will set via UI later
     ```
   - To search for real Mercado Livre listings:
     1. Sign in to the [Mercado Livre developers portal](https://developers.mercadolivre.com.br/) with the account that will use the affiliate program.
     2. Open **Minhas aplicações** and create an application. Select the Mercado Livre site used by the account and enable the permissions the app requests for reading items/searching.
     3. In the app's OAuth/redirect settings, add a redirect URL you control. It must match exactly when authorizing the app. Never publish the Client Secret.
     4. Complete Mercado Livre's OAuth authorization for that app/account and obtain a valid **access token**. Review the current [OAuth authorization documentation](https://developers.mercadolivre.com.br/pt_br/autenticacao-e-autorizacao) for the portal's current steps.
     5. Put the token in `MERCADOLIVRE_ACCESS_TOKEN` in the project-root `.env` file. Do not send it in chat, add it to source control, or put it in the frontend.
     6. Restart Django and run a new search. Access tokens expire; obtain/refresh a valid token using the app's OAuth flow when Mercado Livre requires it.
   - A 403 means Mercado Livre rejected the authorization or the app is not permitted to use the endpoint. Check the app/account, permissions and token in the developer portal. The search will not add fake items.
5. **Run PostgreSQL**
   - The project ships a local PostgreSQL binary in `pgsql/`. Start it with:
     ```powershell
     .\pgsql\pgsql\bin\postgres.exe -D "C:\projetos wilson\apivendas\pgsql\data" -p 5432
     ```
     *(On Linux you can use the bundled `pg_ctl` script similarly.)*
6. **Apply migrations & create a superuser**
   ```bash
   python manage.py migrate
   python manage.py createsuperuser   # follow prompts
   ```
7. **Start the development server**
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```
   The API will be reachable at `http://localhost:8000/`.

## Running the WhatsApp Gateway (Evolution API)
If you want automatic posting to WhatsApp groups, you need the open‑source Evolution API.
1. Install Docker **or** run the pre‑built binary.
2. Start the container (Docker example):
   ```bash
   docker run -d -p 8080:8080 ghcr.io/evolution-api/evolution-api:latest
   ```
3. Scan the QR‑code that appears in the container logs with your phone’s WhatsApp.
4. Once the session is active, the backend will be able to POST messages using the configuration stored in `.env`.

## Production Tips
- Use a real PostgreSQL server (RDS, CloudSQL, etc.) and set `DATABASE_URL` in `.env`.
- Set `WHATSAPP_API_ENABLED=False` when you do not want the bot to send messages.
- Secure the `.env` file – never commit it to version control.

---
**Troubleshooting**
- *"Module not found: psycopg2"* → Install the binary wheels: `pip install psycopg2-binary`.
- *"Database connection refused"* → Verify the PostgreSQL daemon is running and listening on port 5432.
- *WhatsApp messages not sending* → Ensure `WHATSAPP_API_URL` points to the running Evolution API and the token is correct.

---
*Last updated: 2026‑11‑11*