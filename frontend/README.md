# Frontend – React Application

## Prerequisites
| OS | Required Tools |
|---|---|
| **Linux** | • Node.js 20+ (LTS) <br> • `pnpm` (recommended) <br> • `git` (optional) |
| **Windows** | • Node.js 20+ (LTS) <br> • PowerShell (default) <br> • `pnpm` (recommended) |

## Quick Start (Linux & Windows)
1. **Clone the repository** (if you haven't already):
   ```bash
   git clone https://github.com/yourusername/apivendas.git
   cd apivendas/frontend
   ```
2. **Install pnpm** (if not already installed)
   - Linux/macOS:
     ```bash
     curl -fsSL https://pnpm.io/install.sh | sh -
     ```
   - Windows (PowerShell):
     ```powershell
     iwr https://pnpm.io/install.ps1 -UseBasicParsing | iex
     ```
3. **Install project dependencies**
   ```bash
   pnpm install
   ```
4. **Run the development server**
   ```bash
   pnpm dev
   ```
   The app will be available at `http://localhost:5173/`.
5. **Build for production**
   ```bash
   pnpm build
   ```
   The compiled files end up in the `dist/` folder and can be served by any static‑file server (NGINX, Apache, Vercel, Netlify, etc.).

## Environment Variables
Create a `.env.local` file in the `frontend/` directory (it is ignored by Git). Example:
```env
VITE_API_BASE_URL=http://localhost:8000/api
VITE_WHATSAPP_ENABLED=true
```
- `VITE_API_BASE_URL` – URL of the Django API server.
- `VITE_WHATSAPP_ENABLED` – Show the WhatsApp configuration UI. Set to `false` to hide it during local testing.

## Running the App with Docker (optional)
If you prefer containerised execution, a minimal Dockerfile is provided:
```Dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY . .
RUN npm i -g pnpm && pnpm install && pnpm build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```
Build and run:
```bash
docker build -t apivendas-frontend .
docker run -p 80:80 apivendas-frontend
```

## Troubleshooting
- *"pnpm not found"* → Ensure the installation script added the `pnpm` binary to your `PATH` or restart your terminal.
- *Port 5173 already in use* → Change the port in `vite.config.ts` or stop the conflicting process.
- *CORS errors when calling the backend* → Verify that the backend server (`http://localhost:8000`) includes the origin `http://localhost:5173` in `CORS_ALLOWED_ORIGINS` (see backend `settings.py`).

---
**Last updated: 2026‑11‑11**