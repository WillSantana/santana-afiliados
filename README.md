# Santana Afiliados

Bot local de afiliados para o WhatsApp. Monitora grupos autorizados, captura links do Mercado Livre, gera links de afiliado e republica as ofertas nos grupos de destino — tudo rodando na sua máquina.

**O bot não pesquisa produtos no Mercado Livre.** Ele parte de links compartilhados nos grupos de origem e os converte em links de afiliado.

---

## Fluxo principal

```
WhatsApp (grupo de origem)
  → Captura do link (meli.la ou mercadolivre.com.br)
  → Identificação do produto
  → Geração do link de afiliado (ML Link Builder, conta autenticada)
  → Validação do link
  → Publicação nos grupos de destino autorizados
  → Registro individual por grupo no painel
```

---

## Componentes

| Pasta / Arquivo | Descrição |
|-----------------|-----------|
| `backend/` | API Django, fila de ofertas, automação via Selenium |
| `frontend/` | Painel web com Dashboard, Ofertas, Links de Afiliados, Publicações |
| `iniciar_chrome_whatsapp.bat` | Abre o Chrome em perfil dedicado na porta 9222 |
| `iniciar_postgres.bat` | Inicia o PostgreSQL local |
| `backend/DATABASE.md` | Configuração do PostgreSQL |
| `backend/WHATSAPP.md` | Configuração e operação do monitor |
| `USAGE.md` | Guia completo de uso e solução de problemas |

---

## Início rápido

Veja o passo a passo completo em **[USAGE.md](./USAGE.md)**.

```powershell
# 1. Iniciar PostgreSQL
.\iniciar_postgres.bat

# 2. Backend (terminal 1)
Set-Location "C:\projetos wilson\apivendas\backend"
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py runserver

# 3. Frontend (terminal 2)
Set-Location "C:\projetos wilson\apivendas\frontend"
npm run dev

# 4. Chrome dedicado
.\iniciar_chrome_whatsapp.bat
# → Faça login no WhatsApp Web e no Mercado Livre

# 5. Monitor (terminal 3)
Set-Location "C:\projetos wilson\apivendas\backend"
.\venv\Scripts\python.exe manage.py monitor_whatsapp_offers --send
```

Acesse o painel em `http://localhost:5173`.

---

## Links capturados

O bot aceita:
- `https://meli.la/...` (links curtos do Mercado Livre)
- `https://www.mercadolivre.com.br/...` (links tradicionais)
- `https://mercadolivre.com/...`

---

## Painel administrativo

| Aba | Conteúdo |
|-----|---------|
| **Dashboard** | Status do bot e conexões; métricas; grupos; atividade recente |
| **Ofertas Encontradas** | Ofertas capturadas com texto original, preço, status e link afiliado |
| **Links de Afiliados** | Todos os links gerados com link original e link afiliado |
| **Publicações por Grupo** | Envios individuais por grupo de destino com status e erros |
| **Catálogo** | Produtos indexados |

---

## Segurança

- Credenciais ficam apenas no `.env` (nunca no frontend).
- A porta `9222` fica vinculada a `127.0.0.1` pelo launcher.
- O bot nunca publica uma oferta sem um link de afiliado válido.
- Nunca compartilhe o `.env` nem exponha a porta `9222` na rede.
