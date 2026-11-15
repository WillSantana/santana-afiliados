# Backend Django

O backend fornece a API do catálogo e da fila de ofertas recebidas no WhatsApp. A coleta de produtos por busca no Mercado Livre e o monitoramento de preços não fazem mais parte do aplicativo.

## Instalação e inicialização

No PowerShell:

```powershell
Set-Location "C:\projetos wilson\apivendas\backend"
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py runserver
```

O ambiente local já pode ter uma `venv`; nesse caso, pule a criação. O `.env` é carregado da raiz do repositório. Configure o banco e os grupos do WhatsApp antes de iniciar o monitor.

## Monitor de ofertas recebidas

O comando `monitor_whatsapp_offers` acompanha o grupo de origem usando WhatsApp Web no Chrome dedicado. Ele detecta novos links `meli.la`, abre o anúncio, prepara o link de afiliado e pode publicar a oferta no grupo de destino.

1. Execute `iniciar_chrome_whatsapp.bat` na raiz do projeto.
2. Faça login no WhatsApp Web e no Mercado Livre nessa janela.
3. Faça uma leitura inicial sem enviar:

   ```powershell
   .\venv\Scripts\python.exe manage.py monitor_whatsapp_offers --once
   ```

4. Para processar continuamente e publicar automaticamente novas ofertas:

   ```powershell
   .\venv\Scripts\python.exe manage.py monitor_whatsapp_offers --send
   ```

`--send` ativa a publicação automática, sem aprovação individual por oferta. O teto padrão é 20 por dia e o intervalo mínimo entre publicações é 120 segundos. O comando aceita `--once` e `--retry-failed`; use a última opção somente após corrigir uma falha ocorrida antes do envio.

O monitor ignora links que já estavam visíveis quando iniciou. Confirma o grupo de destino e a prévia com imagem; se o resultado do envio for ambíguo, registra como incerto e não reenvia automaticamente. A fila pode ser consultada no painel e em `GET /api/publications/incoming-offers/`.

Gerencie grupos em **Automação → Configurar grupos** no painel. Cadastre uma origem monitorada e um ou mais destinos com JID válido; o monitor passa a usar essa configuração persistida no banco. As publicações manuais também são enviadas a todos os destinos configurados.

## Segurança do navegador

O Chrome deve ser iniciado pelo `iniciar_chrome_whatsapp.bat`, que usa perfil dedicado e depuração em `127.0.0.1:9222`. Essa porta permite controle da sessão autenticada: não use o perfil para outras atividades e não exponha a porta a outras máquinas.

## Banco de dados e dados antigos

Consulte [DATABASE.md](./DATABASE.md) para iniciar/configurar o PostgreSQL. As tabelas antigas de automação não são apagadas automaticamente; não remova dados legados sem backup e decisão explícita.
