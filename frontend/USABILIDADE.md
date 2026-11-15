# Guia do painel

O painel exibe o catálogo existente e, na tela **Automação**, a fila de links novos capturados do WhatsApp. O sistema não oferece mais busca de produtos no Mercado Livre.

## Tela Automação

Acesse `http://localhost:5173` e escolha **Automação** no menu. A tela atualiza a fila periodicamente e mostra:

- origens monitoradas e grupos de publicação configurados;
- quantidade publicada no dia em relação ao limite;
- link de origem, cupom detectado, horário e estado de processamento;
- falhas e envios incertos, que precisam ser avaliados no terminal antes de qualquer retry.

Clique em **Configurar grupos** para adicionar ou remover várias origens monitoradas, editar JIDs e cadastrar destinos. Cada origem deve ser diferente dos destinos; as ofertas são enviadas a todos os destinos cadastrados. O monitor percorre as origens em sequência. Quando uma origem é adicionada enquanto ele está ativo, as mensagens que já estão nela são registradas como histórico e ignoradas. A configuração fica salva no banco e é compartilhada pelo monitor e pelas publicações manuais.

A tela é de acompanhamento. O processo do monitor é iniciado no terminal do backend, não pelo navegador.

## Ativar o monitor

1. Configure os grupos e o limite diário no `.env` da raiz.
2. Inicie o Chrome dedicado com `iniciar_chrome_whatsapp.bat`.
3. Faça login no WhatsApp Web e no Mercado Livre nessa janela.
4. No terminal do backend, execute primeiro uma leitura sem envio:

   ```powershell
   .\venv\Scripts\python.exe manage.py monitor_whatsapp_offers --once
   ```

5. Para publicar automaticamente links novos, inicie:

   ```powershell
   .\venv\Scripts\python.exe manage.py monitor_whatsapp_offers --send
   ```

O monitor ignora os links que já estavam visíveis no grupo ao iniciar. Com `--send`, novas ofertas elegíveis são publicadas automaticamente sem aprovação por oferta. O limite padrão é 20 por dia, com intervalo mínimo de 120 segundos.

## Uso seguro

O perfil de Chrome é exclusivo do monitor, pois a porta `127.0.0.1:9222` permite controlar a sessão autenticada. Não use o perfil para navegação pessoal, não compartilhe a sessão e não exponha a porta na rede. Para interromper o monitor, pressione `Ctrl+C` no terminal.

Consulte [o guia do monitor](../backend/WHATSAPP.md) para configuração e diagnóstico, e [o guia do banco](../backend/DATABASE.md) para iniciar o PostgreSQL.
