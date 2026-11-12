# 🗄️ Guia do Banco de Dados • PostgreSQL 16 & Fallback SQLite

Este documento descreve detalhadamente como instalar, configurar, iniciar e manter o banco de dados do **Santana Afiliados Bot** em ambientes **Windows**, **Linux** e **Docker**, além do modo de contingência local em **SQLite**.

---

## 📌 Configuração Padrão do Projeto

O backend espera por padrão os seguintes parâmetros configurados no arquivo `.env` (na raiz do projeto):

| Variável | Valor Padrão | Descrição |
|---|---|---|
| `USE_SQLITE` | `False` | Se `True`, ignora o PostgreSQL e usa `db.sqlite3` |
| `DB_ENGINE` | `django.db.backends.postgresql` | Driver de banco de dados do Django |
| `DB_NAME` | `santana_afiliados_db` | Nome do banco de dados |
| `DB_USER` | `santana_admin` | Usuário proprietário do banco |
| `DB_PASSWORD` | definir no `.env` | Senha exclusiva do usuário do banco |
| `DB_HOST` | `localhost` (ou `127.0.0.1`) | Endereço do servidor PostgreSQL |
| `DB_PORT` | `5432` | Porta padrão do PostgreSQL |
| `MERCADOLIVRE_ACCESS_TOKEN` | vazio | Token OAuth válido para consultar anúncios reais; configure no `.env` da raiz |

Para buscar anúncios reais:

1. Acesse o [portal de desenvolvedores do Mercado Livre](https://developers.mercadolivre.com.br/) com a conta que usará o programa de afiliados e crie uma aplicação em **Minhas aplicações**.
2. Configure o site/país da conta, as permissões de leitura necessárias e uma URL de redirecionamento válida. A URL informada no fluxo OAuth deve ser idêntica à registrada.
3. Autorize a aplicação com a conta desejada e obtenha um token de acesso OAuth. Siga a documentação oficial atual de [autenticação e autorização](https://developers.mercadolivre.com.br/pt_br/autenticacao-e-autorizacao).
4. Configure `MERCADOLIVRE_ACCESS_TOKEN` no `.env` da raiz do projeto e reinicie o backend. Nunca compartilhe ou versione tokens, Client Secret ou códigos de autorização.
5. Se o Mercado Livre retornar 401/403, confirme no portal se a autorização/token está válido e se a aplicação tem acesso à API. Tokens expiram e precisam seguir o fluxo de renovação OAuth do Mercado Livre.

Sem token válido, a busca informa a configuração pendente ou a recusa da API e não cadastra produtos fictícios. O catálogo também oculta registros antigos com links de busca ou IDs demonstrativos; após configurar o OAuth, faça uma nova busca.

---

## 🪟 Como Rodar no Windows

No ambiente Windows deste projeto, já existe uma distribuição **portátil do PostgreSQL 16** localizada na pasta:
`C:\projetos wilson\apivendas\pgsql\`

Você pode executar o PostgreSQL no Windows de três formas:

### Opção 1: Via Script Automatizado
Na raiz do projeto (`C:\projetos wilson\apivendas`), execute:
```cmd
iniciar_postgres.bat
```
ou simplesmente:
```cmd
iniciar_tudo.bat
```
`iniciar_postgres.bat` também tenta configurar o usuário/banco e executar migrações. Para apenas iniciar o banco, use o procedimento manual abaixo.

---

### Opção 2: Iniciar Manualmente pelo Terminal (PowerShell / CMD)
O caminho `.\pgsql\pgsql\bin\...` é relativo à pasta raiz do projeto. Se o PowerShell estiver em outra pasta (por exemplo, `C:\Users\wilson`), primeiro use o caminho completo ou mude para a raiz do projeto.

1. **Defina a raiz do projeto e localize os executáveis:**
   ```powershell
   $projectRoot = "C:\projetos wilson\apivendas"
   $pgBin = Join-Path $projectRoot "pgsql\pgsql\bin"
   ```
   Se o projeto estiver em outra pasta, ajuste o valor de `$projectRoot`.

2. **Verifique se o PostgreSQL já está rodando:**
   ```powershell
   & "$pgBin\pg_ctl.exe" status -D "$projectRoot\pgsql\data"
   ```
   Se informar que o servidor está rodando, não inicie outra instância. Se estiver parado, inicie-o:
   ```powershell
   & "$pgBin\pg_ctl.exe" -D "$projectRoot\pgsql\data" -l "$projectRoot\pgsql\server.log" start -w
   ```

3. **Confirme que aceita conexões:**
   ```powershell
   & "$pgBin\pg_isready.exe" -h 127.0.0.1 -p 5432
   ```
   O resultado esperado é `127.0.0.1:5432 - accepting connections` (ou `aceitando conexões`).

4. **Aplique as migrações e inicie o backend**, em seguida:
   ```powershell
   Set-Location "$projectRoot\backend"
   .\venv\Scripts\python.exe manage.py migrate
   .\venv\Scripts\python.exe manage.py runserver
   ```

---

### Opção 3: Usando o Instalador Oficial do PostgreSQL no Windows
Caso prefira instalar o PostgreSQL nativo do Windows com instalador gráfico (.exe):
1. Baixe o instalador do PostgreSQL 16 no site oficial: [https://www.postgresql.org/download/windows/](https://www.postgresql.org/download/windows/)
2. Instale mantendo a porta `5432`.
3. Abra o **pgAdmin** ou o **SQL Shell (psql)** e execute:
   ```sql
   CREATE USER santana_admin WITH PASSWORD 'DEFINA_UMA_SENHA_FORTE';
   CREATE DATABASE santana_afiliados_db OWNER santana_admin;
   GRANT ALL PRIVILEGES ON DATABASE santana_afiliados_db TO santana_admin;
   ```
4. O serviço do Windows rodará automaticamente em segundo plano.

---

### ⚠️ Resolução de Problemas no Windows: "postmaster.pid"
Não apague `postmaster.pid` enquanto o PostgreSQL estiver rodando. Esse arquivo evita que duas instâncias usem a mesma pasta de dados e removê-lo à força pode danificar o banco.

**Sintoma:** O PostgreSQL não inicia e informa que já existe um servidor ou que `postmaster.pid` está presente.

**Verifique primeiro o estado do servidor:**
```powershell
& "$pgBin\pg_ctl.exe" status -D "$projectRoot\pgsql\data"
Get-Process postgres -ErrorAction SilentlyContinue
```
Se o servidor estiver ativo, não remova o arquivo. Se estiver parado, consulte `pgsql\server.log` e confirme que não há nenhum processo PostgreSQL usando essa pasta de dados antes de considerar qualquer remoção manual.

---

## 🐧 Como Rodar no Linux (Ubuntu / Debian / CentOS)

No Linux, o PostgreSQL pode ser instalado nativamente como serviço do sistema operacional (`systemd`).

### 1. Instalar o PostgreSQL 16 no Ubuntu/Debian
```bash
sudo apt update
sudo apt install -y postgresql postgresql-contrib
```

### 2. Iniciar e Habilitar o Serviço
```bash
sudo systemctl enable postgresql
sudo systemctl start postgresql
sudo systemctl status postgresql
```

### 3. Criar Usuário e Banco de Dados
Acesse o usuário `postgres` e crie as credenciais da aplicação:
```bash
sudo -u postgres psql
```
No console do PostgreSQL, execute os comandos SQL:
```sql
CREATE USER santana_admin WITH PASSWORD 'DEFINA_UMA_SENHA_FORTE';
CREATE DATABASE santana_afiliados_db OWNER santana_admin;
GRANT ALL PRIVILEGES ON DATABASE santana_afiliados_db TO santana_admin;
\q
```

### 4. Configurar Permissões de Conexão Local (`pg_hba.conf`)
Verifique o arquivo de autenticação do PostgreSQL (geralmente em `/etc/postgresql/16/main/pg_hba.conf`):
```text
# IPv4 local connections:
host    all             santana_admin   127.0.0.1/32            md5
host    all             santana_admin   ::1/128                 md5
```
Se alterar, reinicie o PostgreSQL:
```bash
sudo systemctl restart postgresql
```

### 5. Testar a Conexão
```bash
psql -h 127.0.0.1 -U santana_admin -d santana_afiliados_db
```
Digite a senha definida para o usuário `santana_admin` quando solicitada.

---

## 🐳 Como Rodar com Docker (Windows ou Linux)

Se você utiliza **Docker** e **Docker Compose**, o projeto já possui a configuração pronta no arquivo `docker/docker-compose.yml`:

### 1. Iniciar Apenas o Contêiner do PostgreSQL
```bash
cd docker
docker compose up -d db
```

### 2. Verificar o Status do Contêiner
```bash
docker compose ps
```

### 3. Parar o Contêiner
```bash
docker compose stop db
```

Os dados do banco ficam persistidos com segurança no volume nomeado `postgres_data`.

---

## 🔄 Modo Fallback SQLite (Sem Servidor de Banco)

Caso você esteja em um ambiente de desenvolvimento sem permissão de portas ou queira testar a aplicação rapidamente sem ligar o PostgreSQL:

1. Abra o arquivo `.env` na raiz do projeto.
2. Altere a variável:
   ```env
   USE_SQLITE=True
   ```
3. O Django passará a usar automaticamente o arquivo local `backend/db.sqlite3`.
4. Aplique as migrações no SQLite:
   ```bash
   python manage.py migrate
   python create_admin.py
   python seed_data.py
   ```
*(Para voltar a usar o PostgreSQL, basta recolocar `USE_SQLITE=False` no `.env` e iniciar o serviço do PostgreSQL).*

---

## 🛠️ Comandos de Manutenção Django

Após o banco de dados estar rodando (PostgreSQL ou SQLite):

* **Aplicar Migrações:**
  ```bash
  python manage.py migrate
  ```
* **Criar Novas Migrações (se alterar modelos):**
  ```bash
  python manage.py makemigrations
  ```
* **Cadastrar/Redefinir Administrador:**
  ```bash
  python create_admin.py
  ```
  O comando cria um superusuário solicitando as credenciais no terminal; ele não define nem redefine uma senha padrão.
* **Recarregar Ofertas Demonstrativas:**
  ```bash
  python seed_data.py
  ```
* **Acessar o Terminal SQL do Django:**
  ```bash
  python manage.py dbshell
  ```
