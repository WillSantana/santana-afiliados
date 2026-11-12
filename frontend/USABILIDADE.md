# 📘 Manual de Usabilidade • Santana Afiliados Bot

Guia prático e passo a passo de como operar a plataforma de inteligência comercial, prospecção e geração de campanhas para afiliados do **Mercado Livre** com foco em divulgação via **WhatsApp**.

---

## 📌 1. Visão Geral do Sistema e Modelo de Negócio

O **Santana Afiliados Bot** é uma solução desenvolvida para automatizar o processo diário de quem trabalha como afiliado digital:

1. **Sem Estoque e Sem Logística:** Todo o faturamento, envio da mercadoria e pós-venda é de responsabilidade exclusiva dos vendedores e do Mercado Livre. Sua remuneração vem de **comissões sobre vendas atribuídas** aos seus links oficiais de afiliado.
2. **Triagem com Pontuação Automática (Score 0 a 100):** O algoritmo analisa centenas de produtos, calcula descontos reais, verifica a reputação do vendedor (MercadoLíder/Green) e privilegia produtos de tíquete médio preferencial (até R$ 200,00).
3. **Aprovação Humana Obrigatória (*Human-in-the-Loop*):** Nenhuma oferta é disparada sem o seu aval. Você decide o que entra no canal e o que é rejeitado.
4. **Segurança e Conformidade:** Todas as postagens geradas incluem o disclaimer obrigatório de transparência publicitária exigido pelas políticas do Mercado Livre Afiliados e pelo CONAR.

---

## 🧭 2. Conhecendo as Telas da Plataforma

Ao abrir o sistema em **[http://localhost:5173](http://localhost:5173)**, você tem acesso às 5 áreas principais:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ [⚡ Santana Afiliados]   📦 Catálogo   ⚙️ Automação   📢 WhatsApp   📊 Métricas  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 1. 📦 Catálogo & Triagem (Tela Principal)
* **Painel de KPIs no Topo:** Exibe o *Total Prospectado*, *Revisão Pendente* (destaque em âmbar), *Ofertas Aprovadas* e o *Maior Desconto* encontrado no momento.
* **Barra de Abas de Status:** Filtre rapidamente com 1 clique:
  * `Todas`: Lista completa do catálogo.
  * `Pendentes`: Ofertas recém-captadas que precisam da sua aprovação.
  * `Aprovadas`: Ofertas revisadas e prontas para receber link ou divulgação.
  * `Publicadas`: Ofertas que já foram disparadas para o WhatsApp.
  * `Rejeitadas`: Ofertas descartadas na triagem com registro do motivo.
* **Controles de Busca e Ordenação:** Permite buscar por título ou código MLB, filtrar por nicho e ordenar por *Maior Score*, *Maior Desconto*, *Menor Preço* ou *Maior Preço*.
* **Cards de Produtos Estilo E-Commerce:** Foto de alta resolução, tag de desconto `-X% OFF`, badge de Score, preço comparativo, indicador de link de afiliado e botões rápidos de ação.

---

### 2. ⚙️ Automação & Monitor
* **Controle das Rotinas Automáticas:** Ative ou pause a busca agendada e o monitor de oscilação de preços.
* **Monitor de Oscilações de Preços (Seção 3.3 da Especificação):** Caso um vendedor no Mercado Livre aumente o preço em mais de 5% ou pause o anúncio, um alerta surge imediatamente nesta tela para que você não divulgue preços desatualizados.
* **Histórico de Execuções (SearchRun):** Auditoria de cada ciclo de pesquisa realizado, com data/hora, produtos encontrados, criados e atualizados.

---

### 3. 📢 Central de Publicações & Gateway WhatsApp
* **Painel de Controle do Gateway (Topo da Tela):**
  * **Indicador de Status em Tempo Real:** Identifica se o gateway está em `Modo Simulação (Dry-Run)` ou `Conectado ao WhatsApp`.
  * **Informações Operacionais:** Exibe o tipo de gateway ativo (`Evolution API` ou `Z-API`), o endpoint e o ID do Grupo de destino (`@g.us`).
  * **Botão "⚡ Testar Conexão":** Realiza um ping imediato no gateway com timestamp para confirmar que seu bot está online e pronto para envio.
  * **Botão "🚀 Disparar Próxima":** Localiza a oferta aprovada mais antiga na fila e dispara automaticamente para o grupo de WhatsApp sem precisar abrir o modal.
* **Lista de Cards de Publicações:**
  * **Miniatura da Foto Oficial:** Exibe a foto da mercadoria em alta resolução vinda do Mercado Livre.
  * **Badges de Status:** Indica visualmente se está `⏳ Pendente` ou `✓ Publicado` com data e hora do envio.
  * **Contador de Cliques:** Acompanhe a quantidade de cliques gerados no seu link de afiliado.
  * **Botões de Ação:** "Ver Detalhes / Publicar" e "Copiar Texto".

---

### 4. 📊 Métricas & Metas
* **Funil de Conversão de Afiliados:**
  * Produtos Prospectados ➔ Ofertas Aprovadas ➔ Links Oficiais ➔ Ofertas Publicadas ➔ Cliques Rastreados.
* **Taxa de Aprovação:** Percentual de aproveitamento do catálogo.
* **Distribuição por Categoria:** Gráfico demonstrando quais nichos (Tecnologia, Moda, Casa, Beleza) têm maior volume de ofertas.

---

### 5. 🎯 Campanhas Temáticas
* Agrupamento sazonal de ofertas para datas especiais (ex: *Black Friday*, *Dia dos Pais*, *Semana Gamer*, *Mega Saldão*).

---

## 🚀 3. O Passo a Passo de Uso Diário (Do Zero à Venda)

Siga este roteiro todos os dias para manter seus grupos cheios de ofertas quentes:

```
[1. Buscar no ML] ──► [2. Analisar Score] ──► [3. Aprovar Oferta]
                             │
                             ▼
[6. Vendas Realizadas] ◄── [5. Postar no WhatsApp] ◄── [4. Inserir Link /sec/]
```

---

### Passo 1: Fazer uma Nova Busca de Ofertas
1. No canto superior direito da tela, clique no botão azul com ícone de lupa: **"Buscar no ML"**.
2. Na janela que surgir:
   * **Selecione o Nicho:** Escolha entre *Tecnologia & Games*, *Moda Masculina*, *Casa & Utilidades* ou *Beleza & Cuidados*.
   * **Termo Específico (Opcional):** Se desejar um produto em foco, digite termos como: `fone bluetooth`, `controle sem fio`, `smartwatch`, `tenis corrida`. Se deixar em branco, o robô busca os itens mais populares da categoria.
   * **Quantidade:** Defina a quantidade de ofertas desejada (de 5 a 50 produtos).
3. Clique em **"Executar Busca"**.
4. O sistema consultará os anúncios, aplicará a deduplicação (não cadastra itens repetidos) e colocará os novos anúncios na aba **Pendentes**.

---

### Passo 2: Analisar a Pontuação (Score de Oportunidade)
Acesse a aba **"Pendentes"** para fazer a triagem.  
Cada card exibe uma pontuação calculada por inteligência comercial:

| Score | Classificação | Cor da Badge | O que Significa | Ação Recomendada |
|---|---|---|---|---|
| **85 a 100** | **Excelente** | 🟢 Verde | Desconto expressivo, vendedor MercadoLíder/Oficial e preço competitivo. | **Aprovação Imediata** |
| **70 a 84** | **Muito Bom** | 🔵 Azul | Bom desconto e produto com apelo de venda. | **Aprovar após conferir** |
| **50 a 69** | **Moderado** | 🟡 Âmbar | Desconto mediano ou vendedor sem reputação máxima. | **Avaliar se vale a pena** |
| **Abaixo de 50** | **Regular/Baixo**| ⚪ Cinza | Pouco atrativo para venda em grupo. | **Rejeitar** |

---

### Passo 3: Aprovar ou Rejeitar a Oferta

* **Para Aprovar:**  
  Clique no botão verde **"✓ Aprovar"**. O produto muda de status imediatamente para *Aprovado* e fica pronto para receber seu link de afiliado.

* **Para Rejeitar:**  
  Clique no botão **"✕ Rejeitar"**. Uma janela elegante se abrirá com opções de justificativa rápida:
  * *Preço acima do teto preferencial (R$ 200)*
  * *Margem de desconto insuficiente*
  * *Reputação ou histórico do vendedor duvidoso*
  * *Produto fora do perfil do público*
  * *Oferta duplicada*  
  Você também pode digitar um motivo personalizado e confirmar. A oferta será arquivada e não incomodará mais.

---

### Passo 4: Associar seu Link Oficial de Afiliado
Para que você receba comissões pelas vendas, o link final divulgado precisa ser o seu link encurtado oficial do programa de afiliados:

1. No card do produto aprovado, clique em **"+ Inserir Link"** (ou **"Editar"** se já existir).
2. Se quiser ver a página oficial da mercadoria primeiro, clique em **"Ver no ML"**.
3. No portal do [Mercado Livre Afiliados](https://www.mercadolivre.com.br/afiliados), gere o seu link rastreado exclusivo (o link deve começar com `https://mercadolivre.com/sec/...`).
4. Volte à plataforma, clique em **"Colar do Clipboard"** e depois em **"Salvar Link"**.
5. O card exibirá a confirmação verde: **"✓ Link Afiliado Vinculado"**.

---

### Passo 5: Gerar a Mensagem e Publicar no WhatsApp
Com o produto aprovado e o link vinculado:

1. Acesse a aba **"📢 WhatsApp"** (ou clique no botão **"💬 Post WhatsApp"** no card do produto).
2. Cada card na lista de publicações exibe:
   * A imagem original da mercadoria capturada do Mercado Livre.
   * O texto publicitário persuasivo pronto, com formatação de negrito e itálico do WhatsApp.
   * O badge de status (`⏳ Pendente` ou `✓ Publicado`).
3. Clique em **"Ver Detalhes / Publicar"**:
   * O modal abrirá um simulador fiel do balão de mensagem do WhatsApp.
   * Você verá a imagem que acompanhará o envio e o texto completo.
4. **Formas de Publicação:**
   * **🚀 Envio em 1-Clique pelo Gateway (Recomendado):**
     * Clique no botão verde **"Publicar no WhatsApp"**.
     * O sistema envia a foto e a mensagem para o grupo configurado (`WHATSAPP_GROUP_ID`) via **Evolution API** ou **Z-API**.
     * Caso `WHATSAPP_API_ENABLED=False`, o sistema executa o **Modo Simulação**, gerando logs com sucesso e atualizando o status para `Publicado` para que você possa validar o fluxo visualmente.
   * **⚡ Disparo da Fila ("Disparar Próxima"):**
     * No banner superior da tela de publicações, clique no botão **"🚀 Disparar Próxima"**.
     * O sistema encontra a oferta pendente mais prioritária e a despacha instantaneamente, poupando tempo na sua rotina.
   * **📋 Envio Manual (Copiar para Área de Transferência):**
     * Clique em **"Copiar Texto"**. Uma notificação avisará que o texto foi copiado com sucesso.
     * Abra seu WhatsApp Web/Desktop e cole com `Ctrl + V` no grupo ou canal desejado.

> 📖 **Dica de Configuração:** Para conectar seu número e ler o QR Code da **Evolution API**, consulte o guia detalhado em [`backend/WHATSAPP.md`](../backend/WHATSAPP.md).

---

## 💡 4. Dicas de Ouro para Aumentar suas Vendas

1. **Priorize Ofertas com Score 85+:** Produtos nessa faixa possuem a maior probabilidade de conversão por impulso.
2. **Respeite o Teto de R$ 200,00:** No WhatsApp, produtos abaixo de R$ 200,00 têm menor atrito de decisão e compras mais rápidas no PIX ou cartão.
3. **Distribuição nos Horários de Pico:** Programe seus envios para os horários de maior engajamento dos membros:
   * **Manhã:** 10h00 às 11h30 (pausa para o café).
   * **Almoço:** 12h30 às 13h30.
   * **Fim de Tarde / Noite:** 18h30 às 20h30 (volta para casa e descanso).
4. **Evite SPAM Excessivo:** Não envie mais de 1 oferta a cada 30 a 60 minutos para não cansar os participantes do seu grupo. Qualidade de curadoria supera quantidade!
5. **Confira sempre o Monitor de Preços:** Antes de postar promoções de dias anteriores, consulte a aba *Automação & Monitor* para ter certeza de que o vendedor não aumentou o valor da mercadoria.
