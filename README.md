# wavoo-social

Motor de conteúdo do Instagram do WavooAI, usado pelas skills `wavoo-instagram` (posts automáticos do @wavooai) e `persona-ceo-osteni` (roteiros do @ostenisilva).

```
brand/produto.md               fatos do produto (fonte única; confira sempre a home)
brand/logo/                    logo oficial (branco, marinho, monocromático, símbolo) — nunca desenhar outra
brand/instagram-estrategia.md  cadência, pilares, formatos, legendas, palavra-chave
config.json                    conta, modo (aprovacao|automatico), horários, palavras-chave ativas
historico.json                 o que já foi publicado (evita repetir tema)
scripts/render.py              JSON -> PNG (carrossel/post/story) e MP4 (reel)
scripts/render_caso.py         JSON -> reel animado "caso de negócio" (capítulos, contador, barras, linha do tempo, fluxo)
exemplos/                      specs de referência de cada layout
media/AAAA-MM-DD/...           artes publicadas (URL pública raw do GitHub, lida pelo Postiz)
```

## Gerar artes
```
npm ci && pip install playwright pillow && python3 -m playwright install chromium
python3 scripts/render.py exemplos/carrossel-followup.json --preview
```
Layouts: capa, texto (numero_etapa), lista (itens, numerada), frase, comparacao (antes/depois), chat (mensagens: empresa|cliente|sistema), kanban (colunas/cards — ilustrativo), numero, cta (palavra, acao), enquete (story), cena (reel: linhas, duracao). Temas: escuro, claro, azul (por spec ou por slide). `**texto**` = destaque; `==texto==` = marca-texto. Em qualquer slide: `imagem` (foto IA em tela cheia), `selo` (adesivo inclinado), `notificacoes` ([{app,nome,texto,hora}], notificações de celular).

## Reel caso de negócio animado
`python3 scripts/render_caso.py media/AAAA-MM-DD/caso-<slug>/spec.json` gera reel.mp4 (30 fps), capa.png, preview.png e roteiro.md. Tipos de cena e campos estão no topo do script; ícones do Lucide (`node_modules/lucide-static`). Cena `foto` usa imagem IA (`imagem`, `hora`, `notificacoes`, `linhas`). Exemplo: `media/2026-11-14/caso-mensagem-21h/spec.json`.

## Imagens por IA (GitHub Actions)
1. Crie `media/AAAA-MM-DD/<slug>/imagens.json`: `[{"arquivo":"img01.png","prompt":"…","formato":"retrato"}]` e faça push.
2. O workflow `.github/workflows/gerar-imagens.yml` gera as imagens (secret `OPENAI_API_KEY` ou `GEMINI_API_KEY`; modelo opcional na variável `IMAGE_MODEL`) e faz commit dos PNGs + `imagens.log.json` (status/erros).
3. `git pull` até os PNGs aparecerem (1–5 min) e use `"imagem": "img01.png"` no slide do spec (caminho relativo ao spec). Slide com imagem vira foto em tela cheia com degradê, título em caixa alta e numeração no topo.

## Publicação via Postiz (self-host)
1. Suba o Postiz pelo repositório oficial `gitroomhq/postiz-docker-compose` (pede ~2 GB RAM, Postgres, Redis e Temporal). Defina `MAIN_URL`, `FRONTEND_URL` e `NEXT_PUBLIC_BACKEND_URL` com o domínio (ex.: https://social.wavoo.com.br).
2. Instagram: use o app da Meta (`FACEBOOK_APP_ID`/`FACEBOOK_APP_SECRET` para Instagram ligado a Página do Facebook — necessário para busca de áudio em Reels; ou `INSTAGRAM_APP_ID`/`INSTAGRAM_APP_SECRET` para Instagram standalone). Redirect: `{FRONTEND_URL}/integrations/social/{provider}`. Conecte o @wavooai (conta Business).
3. Em Settings → Developers → Public API gere a chave. O MCP fica em `{NEXT_PUBLIC_BACKEND_URL}/mcp/{API_KEY}`.
4. No claude.ai, adicione esse endereço como conector personalizado ("Postiz"). As skills detectam as ferramentas `integrationList` / `schedulePostTool` e usam o Postiz; sem elas, entregam os arquivos no chat para postagem manual.
