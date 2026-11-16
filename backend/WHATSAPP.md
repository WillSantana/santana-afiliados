# Monitor de ofertas do WhatsApp

O monitor acompanha vários grupos de origem por meio do WhatsApp Web, detecta links `meli.la`, abre os anúncios para preparar o link de afiliado e publica as ofertas em todos os grupos de destino configurados. Ele não faz busca de produtos. As origens são percorridas em sequência; ao adicionar uma origem enquanto o monitor estiver ativo, o conteúdo já existente nela é tratado como histórico e não é publicado retroativamente.

## Requisitos

- Backend instalado com as dependências de `requirements.txt`.
- PostgreSQL ativo e migrations aplicadas.
- Google Chrome instalado.
- Sessão do WhatsApp Web acessível no Chrome dedicado.
- Acesso à página de link builder de afiliados do Mercado Livre.

## Configuração

Edite o `.env` na raiz do projeto:

```dotenv
AFFILIATE_BOT_SOURCE_GROUP="Promozone #46"
AFFILIATE_BOT_TARGET_GROUP=Santana_Indica
AFFILIATE_BOT_DAILY_LIMIT=20
AFFILIATE_BOT_POLL_INTERVAL_SECONDS=10
AFFILIATE_BOT_MIN_INTERVAL_SECONDS=120
AFFILIATE_BOT_CHROME_DEBUGGER_ADDRESS=127.0.0.1:9222
```

Os valores desse arquivo são usados como configuração inicial. Depois, use **Automação → Configurar grupos** no painel para cadastrar várias origens e destinos. Informe nas origens o nome exatamente como aparece no WhatsApp; destinos precisam de JID no formato `123456789@g.us`. Não use o mesmo grupo como origem e destino. As ofertas são encaminhadas para todos os destinos. As alterações salvas no painel são lidas pelo monitor em execução.

O limite diário deve ficar entre 1 e 100; o intervalo de leitura deve ser de pelo menos 3 segundos.

## Primeira execução

1. Na raiz do projeto, execute `iniciar_chrome_whatsapp.bat`.
2. Faça login no WhatsApp Web e no Mercado Livre nessa janela do Chrome. Não compartilhe nem reutilize o perfil dedicado.
3. No diretório `backend`, execute:

   ```powershell
   .\venv\Scripts\python.exe manage.py monitor_whatsapp_offers --once
   ```

Essa leitura verifica o acesso e registra os links já visíveis como linha de base; não os republica.

Para preparar uma oferta já pendente sem enviar mensagem, limite a execução à origem correspondente:

```powershell
.\venv\Scripts\python.exe manage.py monitor_whatsapp_offers --once --prepare-only --source-group "Vendas & Divulgações"
```

O comando resolve o anúncio, gera o link no Link Builder e confirma que o link retorna ao mesmo item do Mercado Livre. Se passar, a oferta fica como **Pronta para envio** no painel. Nenhuma mensagem é enviada; depois, o modo `--send` pode publicar ofertas pendentes ou já preparadas.

## Publicação automática

Inicie o monitor contínuo com:

```powershell
.\venv\Scripts\python.exe manage.py monitor_whatsapp_offers --send
```

Depois de iniciado, novas ofertas elegíveis são publicadas sem aprovação humana individual. O comando pode ser interrompido com `Ctrl+C`. `--once --send` processa no máximo uma oferta pendente e encerra. Se já houver uma oferta pendente, o comando valida as origens na leitura inicial e evita uma segunda varredura antes do processamento; sem oferta pendente, faz a leitura adicional para detectar links novos.

O monitor:

- limita envios ao teto diário configurado (20 por padrão);
- aguarda pelo menos 120 segundos entre publicações;
- confirma o grupo de destino e verifica a prévia com imagem;
- ignora dados ambíguos e não repete automaticamente um envio incerto;
- registra os dados necessários à deduplicação, sem persistir o corpo integral das mensagens.

`--retry-failed` recoloca na fila apenas ofertas marcadas como falha pré-envio; corrija a causa antes de usá-lo. Não use retry para status `uncertain`, pois a mensagem pode já ter sido enviada.

## Segurança e diagnóstico

A porta de depuração do Chrome dá acesso à sessão autenticada. O launcher limita a conexão a `127.0.0.1:9222`; não altere para um endereço de rede nem exponha a porta. Use somente o perfil do bot.

Se o comando não encontrar uma aba do WhatsApp, autentique-se no WhatsApp Web e tente novamente. Se a interface do WhatsApp ou Mercado Livre mudou, interrompa o monitor e revise o erro antes de repetir. Consulte a fila pelo painel **Automação** ou em `GET /api/publications/incoming-offers/`.

O envio manual legado da tela **Publicações** ainda pode usar as configurações do gateway Evolution API; ele é independente deste monitor Selenium.
