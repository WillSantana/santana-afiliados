# Guia de uso — Santana Afiliados Bot

## Pré-requisitos

- PostgreSQL iniciado (`iniciar_postgres.bat` ou via `pgsql\pgsql\bin\pg_ctl.exe start`)
- Google Chrome instalado
- Node.js e Python com dependências instaladas (`pip install -r requirements.txt` e `npm install`)

---

## 1. Iniciar a API (backend)

```powershell
Set-Location "C:\projetos wilson\apivendas\backend"
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py runserver
```

A API ficará disponível em `http://localhost:8000`.

---

## 2. Iniciar o painel (frontend)

```powershell
Set-Location "C:\projetos wilson\apivendas\frontend"
npm run dev
```

Acesse `http://localhost:5173`. O painel possui as seguintes abas:

| Aba | O que mostra |
|-----|--------------|
| **Dashboard** | Status do bot, Chrome e conexões; métricas do dia (ofertas, links, envios); grupos monitorados; atividade recente |
| **Ofertas Encontradas** | Todas as ofertas capturadas nos grupos, com texto original da mensagem, preço, status, link afiliado |
| **Links de Afiliados** | Todos os links de afiliado gerados, com link original, link afiliado, data e status de validação |
| **Publicações por Grupo** | Envios individuais por grupo de destino, com status por grupo, link utilizado e erros |
| **Catálogo** | Produtos indexados |

---

## 3. Configurar os grupos

No painel, clique em **Ofertas Encontradas → Configurar grupos** para:

- Definir quais grupos serão **monitorados** (origem)
- Definir quais grupos receberão as publicações (destino) com seu **JID** (`123456789@g.us`)

As alterações são salvas no banco de dados e passam a valer sem reiniciar o monitor.

Também é possível configurar via `.env` na raiz do projeto:

```dotenv
AFFILIATE_BOT_SOURCE_GROUP="Nome do grupo de origem"
AFFILIATE_BOT_TARGET_GROUP=NomeDoGrupoDestino
AFFILIATE_BOT_DAILY_LIMIT=20
AFFILIATE_BOT_POLL_INTERVAL_SECONDS=10
AFFILIATE_BOT_MIN_INTERVAL_SECONDS=120
AFFILIATE_BOT_CHROME_DEBUGGER_ADDRESS=127.0.0.1:9222
```

---

## 4. Iniciar o Chrome e fazer login

Execute na raiz do projeto:

```
iniciar_chrome_whatsapp.bat
```

No Chrome que abrir (perfil dedicado ao bot):
1. Faça login no **WhatsApp Web**.
2. Faça login no **Mercado Livre** (conta de afiliado).
3. **Não use esse perfil para navegação normal.**

---

## 5. Executar o monitor

### Apenas observar (sem publicar)

```powershell
Set-Location "C:\projetos wilson\apivendas\backend"
.\venv\Scripts\python.exe manage.py monitor_whatsapp_offers --once
```

Faz uma leitura dos grupos configurados, registra os links visíveis no momento como histórico e encerra. Os links já visíveis são ignorados na próxima execução (servem como baseline).

### Monitoramento contínuo com publicação automática

```powershell
.\venv\Scripts\python.exe manage.py monitor_whatsapp_offers --send
```

- Monitora os grupos de origem em loop.
- Captura links `meli.la` **e** links tradicionais do Mercado Livre (`mercadolivre.com.br`, `mercadolivre.com`).
- Gera o link de afiliado via Mercado Livre Afiliados (ML Link Builder).
- Publica nos grupos de destino autorizados.
- Registra cada envio individualmente por grupo.
- Se uma oferta falhar, registra o erro e **continua monitorando** (não para o bot).
- Use `Ctrl+C` para interromper.

### Flags disponíveis

| Flag | Descrição |
|------|-----------|
| `--send` | Ativa geração de links de afiliado e publicação automática |
| `--once` | Executa uma única rodada e encerra |
| `--prepare-only --once` | Gera e valida o link de afiliado sem publicar (exige `--once`) |
| `--retry-failed` | Recoloca na fila as ofertas com status FAILED para reprocessamento |
| `--reprocess-ignored` | Recoloca na fila as ofertas que foram salvas como histórico/ignoradas (as 13 que aparecem no painel) |
| `--process-existing` | Não ignora os links já visíveis nos grupos durante a inicialização (coloca todos na fila) |
| `--all-groups` | Descobre automaticamente **todos os grupos** visíveis no WhatsApp Web e os monitora |
| `--send-all-groups` | Republica as ofertas em **todos os outros grupos** descobertos (exceto o grupo de origem da oferta) |
| `--source-group "Nome"` | Monitora apenas o grupo de origem especificado |

---

## 6. O que o bot valida antes de publicar

1. **Captura o link** (meli.la ou mercadolivre.com.br/com) da mensagem do grupo.
2. **Resolve a URL** e identifica o produto no Mercado Livre.
3. **Gera o link de afiliado** usando o ML Link Builder (conta autenticada no Chrome dedicado).
4. **Valida o link afiliado** — confirma que pertence ao mesmo produto.
5. **Publica somente se o link for válido** — nunca usa o link original como link de afiliado.
6. **Registra cada envio por grupo** — uma oferta enviada a 5 grupos gera 5 registros independentes.

---

## 7. Controle de duplicidade

- Links já processados não são reprocessados.
- Publicações bem-sucedidas não são reenviadas ao mesmo grupo.
- Uma oferta pode ser enviada a vários grupos destino sem duplicidade entre grupos.

---

## 8. Solução de problemas

| Sintoma | Causa provável | O que fazer |
|---------|---------------|-------------|
| Backend não inicia | PostgreSQL parado | Executar `iniciar_postgres.bat` |
| `migrate` falha | Migration pendente ou banco desatualizado | Verificar se o banco está acessível e rodar `migrate` novamente |
| Chrome não conecta | Porta 9222 ocupada ou Chrome parado | Fechar outras instâncias do Chrome e rodar `iniciar_chrome_whatsapp.bat` |
| Bot não encontra grupos | Grupos não configurados | Configurar no painel ou no `.env` |
| Link de afiliado não gerado | Interface do ML Link Builder mudou ou sessão expirou | Fazer login novamente no ML no Chrome dedicado |
| Envio incerto | WhatsApp Web não confirmou o envio | Verificar no grupo manualmente; usar `--retry-failed` somente em status FAILED |
| Bot para com erro | Erro de autenticação ou configuração crítica | Ver mensagem no terminal; corrigir e reiniciar |

---

## 9. Segurança

- A porta `9222` permite controlar a sessão do Chrome. O launcher vincula-a a `127.0.0.1`.
- **Nunca altere para `0.0.0.0`** nem exponha essa porta no firewall/roteador.
- Não compartilhe o arquivo `.env` nem as pastas de sessão do Chrome.
- O painel não expõe credenciais no frontend.

Para mais detalhes:
- Banco de dados: [`backend/DATABASE.md`](./backend/DATABASE.md)
- WhatsApp: [`backend/WHATSAPP.md`](./backend/WHATSAPP.md)
