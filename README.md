# wavoo-social

Motor de conteúdo do Instagram do WavooAI, usado pelas skills `wavoo-instagram` (posts automáticos do @wavooai) e `persona-ceo-osteni` (roteiros do @ostenisilva).

```
brand/produto.md               fatos do produto (fonte única; confira sempre a home)
brand/logo/                    logo oficial (branco, marinho, monocromático, símbolo) — nunca desenhar outra
brand/instagram-estrategia.md  cadência, pilares, formatos, legendas, palavra-chave
config.json                    conta, modo (aprovacao|automatico), horários, palavras-chave ativas
historico.json                 o que já foi publicado (evita repetir tema)
scripts/render.py              JSON -> PNG (carrossel/post/story) e MP4 (reel)
exemplos/                      specs de referência de cada layout
media/AAAA-MM-DD/...           artes publicadas (URL pública raw do GitHub, lida pelo Postiz)
```

## Gerar artes
```
npm ci && pip install playwright pillow && python3 -m playwright install chromium
python3 scripts/render.py exemplos/carrossel-followup.json --preview
```
Layouts: capa, texto (numero_etapa), lista (itens, numerada), frase, comparacao (antes/depois), chat (mensagens: empresa|cliente|sistema), kanban (colunas/cards — ilustrativo), numero, cta (palavra, acao), enquete (story), cena (reel: linhas, duracao). Temas: escuro, claro, azul (por spec ou por slide). `**texto**` = destaque.

## Publicação via Postiz (self-host)
1. Suba o Postiz pelo repositório oficial `gitroomhq/postiz-docker-compose` (pede ~2 GB RAM, Postgres, Redis e Temporal). Defina `MAIN_URL`, `FRONTEND_URL` e `NEXT_PUBLIC_BACKEND_URL` com o domínio (ex.: https://social.wavoo.com.br).
2. Instagram: use o app da Meta (`FACEBOOK_APP_ID`/`FACEBOOK_APP_SECRET` para Instagram ligado a Página do Facebook — necessário para busca de áudio em Reels; ou `INSTAGRAM_APP_ID`/`INSTAGRAM_APP_SECRET` para Instagram standalone). Redirect: `{FRONTEND_URL}/integrations/social/{provider}`. Conecte o @wavooai (conta Business).
3. Em Settings → Developers → Public API gere a chave. O MCP fica em `{NEXT_PUBLIC_BACKEND_URL}/mcp/{API_KEY}`.
4. No claude.ai, adicione esse endereço como conector personalizado ("Postiz"). As skills detectam as ferramentas `integrationList` / `schedulePostTool` e usam o Postiz; sem elas, entregam os arquivos no chat para postagem manual.
