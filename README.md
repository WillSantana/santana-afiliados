# Santana Afiliados Bot • Plataforma de Inteligência Comercial e Automação

Documento Mestre e Especificação Consolidada para Produção (Versão 1.0).

---

## 📌 Visão Geral

O **Santana Afiliados Bot** é uma plataforma desenvolvida para automatizar a prospecção de ofertas, triagem e pontuação de oportunidades no programa oficial de afiliados do **Mercado Livre**, preparando postagens promocionais padronizadas para divulgação via **WhatsApp**.

---

## 📚 Documentações Específicas do Projeto

Consulte os manuais detalhados em cada pasta:

* 📘 **[Manual de Usabilidade do Sistema (Passo a Passo)](./frontend/USABILIDADE.md):** Guia detalhado de uso, desde a busca no Mercado Livre, triagem por Score, vinculação de link de afiliado até a postagem no WhatsApp.
* 📱 **[Guia de Integração com WhatsApp (Evolution API & Z-API)](./backend/WHATSAPP.md):** Passo a passo para subir o gateway Docker, ler QR Code, obter o ID do grupo (@g.us), modo simulação e disparos em 1 clique.
* 🗄️ **[Guia do Banco de Dados (PostgreSQL & SQLite)](./backend/DATABASE.md):** Como instalar, iniciar e manter o PostgreSQL no Windows, Linux, Docker e modo fallback SQLite.
* 🚀 **[Como Rodar o Backend (Windows & Linux)](./backend/README.md):** Instalação de dependências, ambiente virtual `venv`, variáveis de ambiente e execução da API Django.
* 💻 **[Como Rodar o Frontend (Windows & Linux)](./frontend/README.md):** Instalação do Node.js, Vite em modo desenvolvimento e build de produção com Nginx.

---

### Pilares Fundamentais:
1. **Modelo de Negócio Enxuto:** Sem estoque, sem logística e sem manipulação de pagamentos (responsabilidades exclusivas dos vendedores e do Mercado Livre). Monetização puramente por comissão sobre vendas atribuídas.
2. **Aprovação Humana Obrigatória (*Human-in-the-Loop*):** O robô coleta e pontua ofertas automaticamente, mantendo status `pending` até que o administrador aprove manualmente.
3. **Segurança de Links:** Manutenção estrita da separação entre o link original (`product_url`) e o link rastreado (`affiliate_url`).
4. **Conformidade Legal e Transparência:** Todas as publicações incluem disclaimer mandatório de transparência publicitária e preços verificados.

---

## 🏗️ Arquitetura do Sistema

```
santana-afiliados-bot/
├── backend/
│   ├── config/                     # Configurações Django, URLs, Celery, JWT
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   ├── celery.py
│   │   ├── asgi.py
│   │   └── wsgi.py
│   ├── apps/
│   │   ├── catalog/                # Modelo ProductOffer, filtros e aprovação
│   │   ├── integrations/
│   │   │   └── mercadolivre/       # API Mercado Livre, busca e ingestão
│   │   ├── affiliates/             # Gestão de links oficiais e auditoria
│   │   ├── campaigns/              # Campanhas temáticas e sazonais
│   │   ├── publications/           # Gerador de mensagens WhatsApp e histórico
│   │   └── analytics/              # Métricas, conversão e comparação de metas
│   ├── manage.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/             # Cards, modais, badges e KPIs
│   │   ├── pages/                  # Catálogo, Publicações, Analytics, Campanhas
│   │   ├── services/               # Cliente HTTP da API REST
│   │   ├── hooks/                  # Custom hooks para catálogo e produtos
│   │   ├── layouts/                # Layout principal e navegação
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   ├── Dockerfile
│   └── nginx.conf
├── docker/
│   └── docker-compose.yml          # PostgreSQL 16, Redis, Backend, Celery, Frontend
├── .env.example
├── .env
├── .gitignore
└── README.md
```

---

## 🛠️ Stack Tecnológica

| Camada | Tecnologia |
|---|---|
| **Sistema Operacional** | Ubuntu / Windows Server |
| **Linguagem Backend** | Python 3.12 |
| **Framework Backend** | Django 5.2 + Django REST Framework |
| **Autenticação** | SimpleJWT |
| **Banco de Dados** | PostgreSQL 16 (ou SQLite em modo fallback local) |
| **Mensageria & Broker** | Redis 7 |
| **Processamento Assíncrono**| Celery 5.3+ |
| **Frontend** | React 18 + Vite |
| **Servidor Web Frontend** | Nginx (Produção) |
| **Containers** | Docker & Docker Compose |

---

## 🚀 Como Executar o Projeto

### Opção 1: Inicialização Completa com Docker Compose (Recomendado)

Certifique-se de ter o Docker e Docker Compose instalados e execute:

```bash
cd docker
docker compose up --build
```

O ambiente subirá os seguintes serviços:
* **Frontend React:** `http://localhost:5173`
* **API Backend Django:** `http://localhost:8000/api/`
* **Painel Administrativo:** `http://localhost:8000/admin/`
* **Banco PostgreSQL:** porta `5432`
* **Redis Broker:** porta `6379`
* **Worker Celery:** processamento de buscas em background

---

### Opção 2: Execução Manual / Desenvolvimento Local

#### 1. Configurar o Backend (Python 3.12)

```bash
# Acesse o diretório do backend
cd backend

# Crie e ative o ambiente virtual
python -m venv venv
# No Windows:
.\venv\Scripts\activate
# No Linux:
source venv/bin/activate

# Instale as dependências
pip install -r requirements.txt

# Execute as migrações do banco de dados
python manage.py makemigrations
python manage.py migrate

# (Opcional) Crie o superusuário administrador
python manage.py createsuperuser

# Inicie o servidor Django
python manage.py runserver 0.0.0.0:8000
```

#### 2. Configurar o Frontend (React + Vite)

```bash
# Em outro terminal, acesse o diretório do frontend
cd frontend

# Instale os pacotes npm
npm install

# Inicie o servidor de desenvolvimento
npm run dev
```

Acesse o frontend em `http://localhost:5173`.

---

## 📡 Endpoints REST Disponíveis (Seção 3.11)

| Método | Endpoint | Finalidade |
|---|---|---|
| `GET` | `/api/health/` | Verificar funcionamento operacional |
| `GET` | `/api/products/` | Listar catálogo com filtros (categoria, status, score) |
| `POST` | `/api/products/` | Cadastrar anúncio manualmente |
| `GET` | `/api/products/{id}/` | Detalhes de um produto específico |
| `PATCH` | `/api/products/{id}/` | Atualizar dados do produto |
| `POST` | `/api/products/{id}/approve/` | Aprovar oferta (administrador) |
| `POST` | `/api/products/{id}/reject/` | Rejeitar oferta (com justificativa) |
| `POST` | `/api/products/{id}/affiliate-link/` | Associar URL de afiliado oficial |
| `POST` | `/api/search/run/` | Executar busca e ingestão na API do Mercado Livre |
| `GET` | `/api/campaigns/` | Listar campanhas ativas |
| `GET` | `/api/publications/` | Listar publicações e histórico |
| `POST` | `/api/publications/generate/` | Gerar texto promocional formatado para WhatsApp |
| `POST` | `/api/publications/{id}/publish/` | Disparar foto + legenda no WhatsApp (Evolution / Z-API) |
| `GET` | `/api/publications/whatsapp-config/` | Consultar status, tipo de gateway e grupo ativo |
| `POST` | `/api/publications/test-whatsapp/` | Disparar ping de teste no grupo de WhatsApp |
| `POST` | `/api/publications/dispatch-next/` | Publicar automaticamente a próxima oferta na fila |
| `GET` | `/api/analytics/` | Consultar KPIs, conversão e comparativo com metas |

---

## 📊 Regras de Pontuação (Score de Oportunidade)

O cálculo de oportunidade varia de **0 a 100 pontos**:
* **Preço dentro do orçamento preferencial (até R$ 200):** até 20 pontos
* **Reputação do vendedor (verde/ouro/platina):** 20 pontos
* **Produto novo e anúncio ativo:** 15 pontos
* **Competitividade de preço (desconto real verificado):** até 20 pontos
* **Comissão/link cadastrado e confirmado:** 15 pontos
* **Atratividade comercial e consistência do anúncio:** 10 pontos

Faixas de classificação:
* `85 - 100`: **Excelente**
* `70 - 84`: **Boa**
* `50 - 69`: **Moderada**
* `0 - 49`: **Baixa prioridade**

---

## 📱 Modelo de Mensagem Promocional para WhatsApp

```
■ OFERTA DO DIA!
■ [NOME DO PRODUTO]

[DESCRIÇÃO DO BENEFÍCIO / CATEGORIA]

■ Preço: R$ XX,XX
■ Consulte as condições de entrega.

■ Confira a oferta:
[LINK DE AFILIADO OFICIAL]

Publicidade: este é um link de afiliado e posso receber comissão se você comprar.
```
