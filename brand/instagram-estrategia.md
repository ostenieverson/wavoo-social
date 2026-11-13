# Estratégia Instagram — @wavooai

## Objetivo
1. Atrair leads de PMEs que vendem pelo WhatsApp e levá-los ao plano Free.
2. Construir comunidade em torno do ecossistema (clientes, parceiros/indicadores, agências, fundadores).

## O que o algoritmo premia (Mosseri, 2025–2026)
- Tempo de visualização (Reels: segurar os 3 primeiros segundos e a retenção até o fim).
- Envios por DM / alcance — o sinal mais forte para chegar a não seguidores. Todo post precisa de um motivo para ser enviado ("manda pro seu sócio que…").
- Curtidas e salvamentos / alcance. Checklists e templates geram salvamento.
- Conteúdo original. Nada de repost ou marca d'água de outra rede.

## Cadência diária (2 a 5 publicações/dia contando Stories)
| Dia | Feed | Reel automático | Stories |
|---|---|---|---|
| Seg | Carrossel ATRAIR | — | 2 |
| Ter | Post único PROVA | Reel ATRAIR | 2 |
| Qua | Carrossel SUPORTE (repete o tema do blog de quarta) | — | 3 |
| Qui | **Carrossel com imagens IA** (storytelling) | Reel CONVERTER | 2 |
| Sex | Carrossel CONVERTER | — | 3 |
| Sáb | — | **Reel história animada** (storytelling) | 2 |
| Dom | — | — | 1 (enquete/caixinha) |
Horários base (testar e ajustar pelo Insights): feed 11h30, reel 18h30, stories 9h / 13h / 20h (America/Sao_Paulo).

## Pilares
- ATRAIR (40%): dores de quem vende pelo WhatsApp. Lead esquecido, demora na primeira resposta, vendedor que sai e leva o histórico, follow-up que ninguém faz, atendimento fora do horário, mensagens espalhadas em vários celulares.
- PROVAR (20%): o produto funcionando. Tela do Kanban, cadência de retomada, Nexus IA sugerindo resposta, inbox com 12 canais. Só o que existe.
- SUPORTE (15%): como fazer no WavooAI, boas práticas, templates de mensagem.
- COMUNIDADE (15%): bastidores do time, perguntas para a audiência, destaques de parceiros, "o que vocês querem que a gente construa?", ponte com o perfil @ostenisilva.
- CONVERTER (10%): Free para sempre, comparação de planos, programa de indicação, implantação assistida.

## Formatos
- Carrossel 1080x1350, 6–9 slides: capa com gancho → problema → virada → passos/lista → prova/produto → CTA. Último slide pede envio ou palavra-chave.
- Post único 1080x1350: frase forte, dado verificável ou meme de rotina comercial.
- Story 1080x1920: enquete, caixinha, quiz, bastidor, "novo post no feed" (repost), link sticker para cadastro.
- Reel automático 1080x1920, 15–30 s: 4–7 cenas de texto grande em movimento, sem voz; a trilha vem da biblioteca do Instagram (Postiz audioSearch) ou é adicionada na aprovação.

## Carrossel com imagens IA (toda quinta, mínimo 1x/semana)
Referência de formato: @lemoncaps.br (posts de 08/11 e 12/11/2026) — foto cinematográfica em tela cheia, degradê escuro embaixo, título grande em caixa alta, frase de apoio com destaque colorido, numeração 01/07 no topo e seta.
- Linhas de história: (1) caso de grande empresa com lição para PME (fato verificado, fonte na legenda; o nome da empresa vai no texto, NUNCA logo ou produto da marca na imagem); (2) cena do dia a dia de quem vende pelo WhatsApp (balcão de loja, recepção de clínica, celular vibrando à noite, vendedor com 3 celulares); (3) "antes e depois" do atendimento.
- 5–8 slides: 3–5 com foto IA + 1–2 só texto/produto + CTA. Imagens retrato, mesma luz e paleta em todo o carrossel.
- Prompt de imagem: descreva cena, ambiente, enquadramento e luz; nada de texto, logotipos, marcas ou pessoas reais conhecidas; deixe o terço inferior mais limpo para o texto. O estilo base é somado automaticamente.
- O Instagram pode marcar a postagem com "Info de IA" (metadados das imagens geradas). É esperado.

## Regras visuais (todo post de feed)
Post "só texto em fundo azul" não para o dedo. Em TODO carrossel/post:
- Capa com foto IA em tela cheia + título curto em caixa alta + `==marca-texto==` na palavra-chave do gancho + `selo` (adesivo amarelo inclinado com 2–4 palavras: "Salve antes de assinar", "\"Vou ver e te falo\"").
- 2 a 4 slides com foto IA ao longo do carrossel (a cada 2–3 slides), incluindo o CTA final. Os demais alternam escuro/claro.
- Pelo menos 1 elemento "de celular" que o lead reconhece: conversa (layout chat) ou `notificacoes` sobre a foto.
- Títulos com no máximo ~8 palavras; o resto vai no texto de apoio.
- Imagens: 4 por carrossel via `imagens.json` (GitHub Actions). Ver pessoas comuns em lojas, clínicas, escritórios, sofá à noite; mesma luz/paleta no carrossel; mesmo personagem quando a história continua.

## Reel história animada (todo sábado)
Inspiração de FORMATO (não de assunto): @lemoncaps.br, reel de 13/11/2026 — infográfico animado em capítulos com barra de progresso no topo, 40–60 s.
- O assunto é sempre NOSSO: uma situação do dia a dia de quem vende pelo WhatsApp/Instagram, contada como uma história contínua com o MESMO personagem e o MESMO fio do começo ao fim (ex.: "a mensagem das 21h07" seguida até virar venda perdida). Nada de copiar o tema do exemplo nem contar a história de outra empresa só porque ela é famosa.
- Cada cena continua a anterior (horário que avança, a mesma conversa, a consequência). Teste: lendo só os textos na tela, em sequência, a história faz sentido.
- 4 capítulos com nomes da própria história (ex.: 21H07 → O SILÊNCIO → O NÚMERO → A SAÍDA): situação → o problema acontece → o dado que prova que não é azar → a mesma cena resolvida com o WavooAI + CTA.
- 7–9 cenas de 5–7 s: 3–4 cenas `foto` (imagem IA com zoom lento, hora grande, notificações de celular, frase com `==marca-texto==`) + cenas de dado (`numero`, `barras`) + `fluxo` com o WavooAI + `cta`.
- Dado com fonte verificada (WebSearch/WebFetch), na `nota` da cena e na legenda. Personagem é ilustrativo: nunca apresentar como cliente real. Nexus IA só Scale/Elite, com asterisco.
- Áudio: sem voz sintética. Na aprovação, trilha em alta (Postiz audioSearch) ou narração de `roteiro.md` gravada por cima.
- Gerar: `python3 scripts/render_caso.py media/AAAA-MM-DD/caso-<slug>/spec.json` → reel.mp4, capa.png, preview.png, roteiro.md. Exemplo: `media/2026-11-14/caso-mensagem-21h/spec.json`.

## Legendas
- Primeira linha = gancho (aparece antes do "mais", ~125 caracteres).
- Corpo curto, parágrafos de 1–2 linhas, emojis com moderação.
- CTA único: "Comenta WAVOO que eu te mando o acesso" / "Manda pra quem ainda controla venda no caderninho" / "Link na bio: plano Free para sempre".
- 3–5 hashtags de nicho no fim (#atendimentowhatsapp #crm #vendaspelowhatsapp #pequenasempresas #automacao). Nunca 30.

## Palavra-chave nos comentários (captação)
Instagram é um canal do WavooAI (Direct e comentários). Usar palavras-chave fixas por campanha (WAVOO, KANBAN, FOLLOWUP, NEXUS) para a automação responder no Direct e criar o card no CRM. Só use a palavra-chave em post depois que a automação estiver ativa (ver config.json → keywords_ativas).

## Comunidade
- Responder todo comentário nas primeiras 2 horas (tarefa humana; o agente lembra no relatório).
- Toda semana: 1 story de caixinha "qual sua maior dor no atendimento?" — as respostas viram pauta.
- Mensal: destaque de cliente/parceiro, só com autorização e fatos reais.
