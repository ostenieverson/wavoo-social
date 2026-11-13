#!/usr/bin/env python3
"""Reel animado "caso de negócio" (estilo infográfico em capítulos) para o @wavooai.

Uso:
  python3 scripts/render_caso.py media/AAAA-MM-DD/caso-x/spec.json

Gera, na pasta "saida" do spec: reel.mp4 (1080x1920, 30 fps, trilha silenciosa),
capa.png (quadro final da 1ª cena), preview.png (quadro final de cada cena) e roteiro.md (narração).

Spec:
{
 "formato": "caso",
 "saida": "media/2026-11-14/caso-zappos",
 "capitulos": ["O NÚMERO", "A HISTÓRIA", "A VIRADA", "A LIÇÃO"],
 "cenas": [
  {"capitulo": 0, "duracao": 6, "tema": "escuro|papel|azul", "tipo": "numero", ...},
  ...
 ]
}
Tipos de cena (campos opcionais entre colchetes; **x** = destaque; \n = quebra):
  numero       [kicker] [titulo] valor (ex.: "10 bilhões", "10h43", "13.477") [prefixo] [sufixo] [texto] [nota]
               números inteiros em "valor" sobem contando; o resto aparece pronto.
  barras       [kicker] titulo  barras:[{rotulo, valor (número relativo), texto_valor, destaque?}] [texto] [nota]
  linha_tempo  ano [local] [titulo] [texto] [icones: nomes lucide] [rodape] [nota]
  fluxo        [kicker] titulo  passos:[{icone, texto, [marca]}] [rodape]
  frase        linhas:[...] (entram uma a uma) [kicker]
  foto         imagem (relativa ao spec, ex.: img01.png; zoom lento) [hora: "21h07"] [notificacoes:[{app,nome,texto,hora}]] [linhas] [texto]
  lista        [kicker] titulo  itens:[...] [texto]
  cta          titulo [texto] [palavra] [canal: "direct"|"comentario"] [acao]
Cada cena pode ter "narracao" (vai para roteiro.md e legenda) e "nota" (fonte, em letra pequena).
Ícones: nomes do Lucide (https://lucide.dev/icons), ex.: store, building-2, banknote, message-circle,
clock, users, phone, chart-line, calendar, rocket, shopping-cart, headset, zap, trophy.
"""
import html, json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "node_modules" / "@fontsource"
ICONS = ROOT / "node_modules" / "lucide-static" / "icons"
LOGOS = ROOT / "brand" / "logo"
W, H, FPS = 1080, 1920, 30

PAL = {
    "escuro": dict(bg="#101A31", fg="#FFFFFF", muted="#AEB8D6", accent="#369EFF", strong="#3155FF", card="#18264A", line="#2A3A66", logo="wavoo-logo-branco.png", grain=False),
    "papel":  dict(bg="#F1E9DA", fg="#14203D", muted="#5B6478", accent="#3155FF", strong="#3155FF", card="#FBF7EF", line="#14203D", logo="wavoo-logo-marinho.png", grain=True),
    "azul":   dict(bg="#3155FF", fg="#FFFFFF", muted="#DCE3FF", accent="#101A31", strong="#101A31", card="#2546E0", line="#5C78FF", logo="wavoo-logo-monocromatico-branco.png", grain=False),
}


def font_css():
    out = []
    for fam, pkg, ws in (("Outfit", "outfit", (400, 600, 800, 900)), ("Inter", "inter", (400, 500, 700))):
        for w in ws:
            p = FONTS / pkg / "files" / f"{pkg}-latin-{w}-normal.woff2"
            out.append(f"@font-face{{font-family:'{fam}';font-weight:{w};src:url('file://{p}') format('woff2');}}")
    return "\n".join(out)


def rich(t):
    t = html.escape(t or "")
    t = re.sub(r"\*\*(.+?)\*\*", r'<span class="hl">\1</span>', t)
    t = re.sub(r"==(.+?)==", r'<span class="mk">\1</span>', t)
    return t.replace("\n", "<br>")


def icon(name, size=72):
    f = ICONS / f"{name}.svg"
    if not f.exists():
        print(f"AVISO: ícone '{name}' não existe no Lucide; usando 'circle'", file=sys.stderr)
        f = ICONS / "circle.svg"
    svg = f.read_text()
    svg = re.sub(r'width="\d+"', f'width="{size}"', svg, count=1)
    svg = re.sub(r'height="\d+"', f'height="{size}"', svg, count=1)
    svg = re.sub(r'stroke-width="[\d.]+"', 'stroke-width="2.2"', svg)
    return re.sub(r"<!--.*?-->", "", svg, flags=re.S)


def A(t0, inner, cls="", extra=""):
    """Elemento que entra (fade + sobe) no segundo t0 da cena."""
    return f'<div class="a {cls}" data-in="{t0}" {extra}>{inner}</div>'


def count_html(valor):
    """Se o valor tem um número inteiro (com pontos de milhar), anima contando."""
    m = re.search(r"\d[\d.]*", valor or "")
    if not m:
        return rich(valor)
    num = m.group(0)
    target = int(num.replace(".", ""))
    nxt = valor[m.end():m.end() + 1]
    if target < 10 or (nxt and not nxt.isspace()):  # "10h43", "3x": aparece pronto
        return rich(valor)
    return (html.escape(valor[:m.start()]) + f'<span class="cnt" data-to="{target}" data-dots="{1 if "." in num else 0}">{html.escape(num)}</span>'
            + html.escape(valor[m.end():]))


def scene_html(s):
    tipo = s.get("tipo", "frase")
    k = A(0.1, rich(s["kicker"]), "kicker") if s.get("kicker") else ""
    nota = A(0.8, rich(s["nota"]), "nota") if s.get("nota") else ""
    t = 0.25
    parts = [k]
    if tipo == "numero":
        if s.get("titulo"):
            parts.append(A(t, rich(s["titulo"]), "t-m")); t += 0.4
        big = f'{html.escape(s.get("prefixo",""))}{count_html(s.get("valor",""))}{html.escape(s.get("sufixo",""))}'
        parts.append(A(t, big, "big", 'data-count="1"')); t += 1.4
        if s.get("texto"):
            parts.append(A(t, rich(s["texto"]), "txt")); t += 0.5
    elif tipo == "barras":
        parts.append(A(t, rich(s.get("titulo", "")), "t-m")); t += 0.5
        mx = max([b.get("valor", 1) for b in s.get("barras", [])] or [1])
        rows = []
        for b in s.get("barras", []):
            pct = 100 * b.get("valor", 0) / mx
            rows.append(A(t, f'<div class="bl"><span>{rich(b.get("rotulo",""))}</span><b>{rich(b.get("texto_valor",""))}</b></div>'
                             f'<div class="track"><div class="fill {"dest" if b.get("destaque") else ""}" data-w="{pct:.1f}" data-in="{t+0.2}"></div></div>', "bar"))
            t += 0.6
        parts.append(f'<div class="bars">{"".join(rows)}</div>')
        if s.get("texto"):
            parts.append(A(t + 0.4, rich(s["texto"]), "txt"))
    elif tipo == "linha_tempo":
        head = f'<div class="ano">{html.escape(str(s.get("ano","")))}</div>'
        if s.get("local"):
            head += f'<div class="local">{rich(s["local"])}</div>'
        parts.append(A(t, head, "tl-head")); t += 0.5
        if s.get("titulo"):
            parts.append(A(t, rich(s["titulo"]), "t-l")); t += 0.4
        if s.get("texto"):
            parts.append(A(t, rich(s["texto"]), "txt")); t += 0.6
        ics = s.get("icones", [])
        if ics:
            row = "".join(A(t + 0.25 * i, icon(n, 96), "ic") for i, n in enumerate(ics))
            parts.append(f'<div class="icons"><div class="rail"></div>{row}</div>'); t += 0.25 * len(ics) + 0.4
        if s.get("rodape"):
            parts.append(A(t, rich(s["rodape"]), "rodape"))
    elif tipo == "fluxo":
        parts.append(A(t, rich(s.get("titulo", "")), "t-m")); t += 0.5
        ps = s.get("passos", [])
        for i, p in enumerate(ps):
            marca = f'<div class="marca">{icon(p["marca"], 56)}</div>' if p.get("marca") else ""
            parts.append(A(t, f'<div class="pi">{icon(p.get("icone","circle"), 64)}</div><div class="pt">{rich(p.get("texto",""))}</div>{marca}', "passo"))
            t += 0.7
            if i < len(ps) - 1:
                parts.append(A(t - 0.3, icon("arrow-down", 52), "seta"))
        if s.get("rodape"):
            parts.append(A(t + 0.2, rich(s["rodape"]), "rodape"))
    elif tipo == "lista":
        parts.append(A(t, rich(s.get("titulo", "")), "t-l")); t += 0.5
        for it in s.get("itens", []):
            parts.append(A(t, f'<span class="ck">{icon("check", 48)}</span><span>{rich(it)}</span>', "item")); t += 0.5
        if s.get("texto"):
            parts.append(A(t + 0.2, rich(s["texto"]), "txt"))
    elif tipo == "cta":
        parts.append(A(t, rich(s.get("titulo", "")), "t-xl")); t += 0.6
        if s.get("texto"):
            parts.append(A(t, rich(s["texto"]), "txt")); t += 0.5
        if s.get("palavra"):
            verbo = "Manda" if s.get("canal", "comentario") == "direct" else "Comenta"
            parts.append(A(t, f'{verbo} <b>{html.escape(s["palavra"])}</b>', "kw")); t += 0.5
        if s.get("acao"):
            parts.append(A(t, rich(s["acao"]), "btn"))
    elif tipo == "foto":
        if s.get("hora"):
            parts.append(A(t, html.escape(s["hora"]), "hora")); t += 0.4
        for n in s.get("notificacoes", []):
            parts.append(A(t, f'<div class="nt-ic"></div><div class="nt-b"><div class="nt-h"><b>{html.escape(n.get("app","WhatsApp"))}</b><span>{html.escape(n.get("hora","agora"))}</span></div>'
                              f'<div class="nt-n">{html.escape(n.get("nome",""))}</div><div class="nt-t">{rich(n.get("texto",""))}</div></div>', "nt")); t += 0.6
        for ln in s.get("linhas", []):
            parts.append(A(t, rich(ln), "fl")); t += 0.6
        if s.get("texto"):
            parts.append(A(t, rich(s["texto"]), "txt"))
    else:  # frase
        for ln in s.get("linhas", []):
            parts.append(A(t, rich(ln), "ln")); t += 0.6
    parts.append(nota)
    bg = ""
    if tipo == "foto" and s.get("_img"):
        bg = f'<div class="ph" style="background-image:url(\'file://{s["_img"]}\')"></div><div class="phs"></div>'
    return f'{bg}<div class="main {tipo}">{"".join(parts)}</div>'


def page(s, chapters, cur):
    c = PAL[s.get("tema", "escuro")]
    segs = "".join(f'<div class="seg {"done" if i < cur else ""}" data-i="{i}"><div class="sf"></div><span>{html.escape(n)}</span></div>'
                   for i, n in enumerate(chapters))
    grain = ("background-image:url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='300' height='300'>"
             "<filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.8' numOctaves='3'/><feColorMatrix values='0 0 0 0 .3  0 0 0 0 .25  0 0 0 0 .2  0 0 0 .09 0'/></filter>"
             "<rect width='100%' height='100%' filter='url(%23n)'/></svg>\");") if c["grain"] else ""
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
{font_css()}
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:{W}px;height:{H}px;overflow:hidden}}
body{{background:{c['bg']};color:{c['fg']};font-family:Inter,sans-serif;position:relative}}
body::before{{content:"";position:absolute;inset:0;{grain}{'' if c['grain'] else f"background:radial-gradient(900px 700px at 85% 0%,{c['accent']}2e,transparent 60%)"}}}
.chap{{position:absolute;top:96px;left:72px;right:72px;display:grid;grid-template-columns:repeat({len(chapters)},1fr);gap:14px;z-index:3}}
.seg{{display:flex;flex-direction:column;gap:12px}}
.seg::before{{content:"";height:8px;border-radius:8px;background:{c['fg']}33;display:block}}
.sf{{height:8px;border-radius:8px;background:{c['fg']};margin-top:-20px;width:0}}
.seg.done .sf{{width:100%}}
.seg span{{font:700 22px Outfit;letter-spacing:2px;color:{c['fg']};opacity:.55;text-align:center}}
.seg.cur span{{opacity:1}}
.main{{position:absolute;top:250px;bottom:420px;left:80px;right:150px;display:flex;flex-direction:column;justify-content:center;gap:34px}}
.a{{opacity:0;transform:translateY(34px)}}
.hl{{color:{c['accent']}}}
.kicker{{align-self:flex-start;background:{c['strong']};color:#fff;font:700 30px Outfit;letter-spacing:1px;padding:12px 26px;border-radius:999px;text-transform:uppercase}}
.t-xl{{font:900 104px/1 Outfit;letter-spacing:-2px}}
.t-l{{font:900 84px/1.02 Outfit;letter-spacing:-1.5px;text-transform:uppercase}}
.t-m{{font:800 58px/1.08 Outfit;letter-spacing:-1px}}
.big{{font:900 190px/0.95 Outfit;letter-spacing:-5px;color:{c['accent']};text-transform:uppercase}}
.numero .big{{font-size:{'190'}px}}
.txt{{font-size:46px;line-height:1.32;color:{c['muted']}}}
.txt .hl{{font-weight:700}}
.nota{{font-size:24px;color:{c['muted']};opacity:.8;margin-top:10px}}
.bars{{display:flex;flex-direction:column;gap:34px}}
.bl{{display:flex;justify-content:space-between;align-items:baseline;font:700 36px Outfit;margin-bottom:12px}}
.bl b{{font:900 44px Outfit}}
.track{{height:40px;border-radius:12px;background:{c['fg']}1f;overflow:hidden}}
.fill{{height:100%;width:0;background:{c['muted']};border-radius:12px}}
.fill.dest{{background:{c['accent']}}}
.tl-head{{display:flex;align-items:center;gap:30px}}
.ano{{font:900 120px/1 Outfit;color:#fff;background:{c['strong']};padding:14px 30px 10px;border-radius:18px;letter-spacing:-3px}}
.local{{font:700 34px/1.2 Outfit;text-transform:uppercase;letter-spacing:1px;color:{c['muted']}}}
.icons{{position:relative;display:flex;gap:46px;align-items:center;padding:40px 0}}
.rail{{position:absolute;left:0;right:0;top:50%;height:6px;background:{c['fg']};opacity:.15;border-radius:6px}}
.ic{{position:relative;color:{c['strong']};background:{c['bg']};padding:10px}}
.rodape{{font:900 72px/1.04 Outfit;color:{c['accent']};text-transform:uppercase;letter-spacing:-1px}}
.passo{{display:flex;align-items:center;gap:28px;background:{c['card']};border:3px solid {c['line']}{'' if c['grain'] else '88'};border-radius:26px;padding:26px 30px}}
.pi{{flex:none;color:{c['strong']}}}
.pt{{flex:1;font-size:38px;line-height:1.25;font-weight:500}}
.marca{{flex:none;color:{c['accent']}}}
.seta{{align-self:center;color:{c['fg']};opacity:.5;margin:-18px 0}}
.fluxo{{gap:26px}}
.item{{display:flex;gap:24px;align-items:center;font-size:44px;font-weight:500;line-height:1.25}}
.ck{{flex:none;width:72px;height:72px;border-radius:20px;background:{c['strong']};color:#fff;display:flex;align-items:center;justify-content:center}}
.ln{{font:900 100px/1.02 Outfit;letter-spacing:-2px}}
.kw{{align-self:flex-start;border:5px dashed {c['accent']};border-radius:28px;padding:26px 38px;font:600 54px Outfit}}
.kw b{{color:{c['accent']};font-weight:900}}
.btn{{align-self:flex-start;background:{c['bg'] if s.get('tema')=='azul' else c['strong']};color:#fff;font:800 42px Outfit;padding:28px 44px;border-radius:999px;{'background:#101A31' if s.get('tema')=='azul' else ''}}}
.ph{{position:absolute;inset:-20px;filter:brightness(1.25) saturate(1.1);background-size:cover;background-position:center 18%;transform-origin:50% 30%}}
.phs{{position:absolute;inset:0;background:linear-gradient(to top,rgba(16,26,49,.96) 0%,rgba(16,26,49,.8) 34%,rgba(16,26,49,.08) 62%,rgba(16,26,49,.4) 100%)}}
.foto{{justify-content:flex-end;color:#fff}}
.foto .txt{{color:#E3E8F5}}
.hora{{align-self:flex-start;font:900 150px/1 Outfit;letter-spacing:-4px;color:#fff;text-shadow:0 6px 40px #0009}}
.fl{{font:900 92px/1.02 Outfit;letter-spacing:-2px;text-transform:uppercase;text-shadow:0 6px 40px #0009}}
.nt{{display:flex;gap:20px;align-items:flex-start;background:rgba(245,247,252,.94);color:#101A31;border-radius:30px;padding:22px 26px;box-shadow:0 18px 50px #0008}}
.nt-ic{{flex:none;width:62px;height:62px;border-radius:16px;background:linear-gradient(135deg,#3DDC84,#1FAF5A)}}
.nt-b{{flex:1}} .nt-h{{display:flex;justify-content:space-between;font:600 24px Inter;color:#55607A}} .nt-h b{{color:#101A31}}
.nt-n{{font:700 30px Inter;margin-top:4px}} .nt-t{{font:400 30px/1.3 Inter;color:#26314F}}
.mk{{background:#3155FF;color:#fff;padding:0 .16em;border-radius:.1em;box-decoration-break:clone;-webkit-box-decoration-break:clone;text-shadow:none}}
.foot{{position:absolute;left:0;right:0;bottom:300px;display:flex;justify-content:center;align-items:center;gap:20px;font:600 28px Outfit;color:{c['muted']}}}
.foot img{{height:42px}}
</style></head><body>
<div class="chap">{segs}</div>
{scene_html(s)}
<div class="foot"><img src="file://{LOGOS / c['logo']}"><span>@wavooai</span></div>
<script>
const ease=x=>x<=0?0:x>=1?1:1-Math.pow(1-x,3);
const fmt=(n,dots)=>dots?n.toLocaleString('pt-BR'):String(n);
function draw(t,prog){{
  document.querySelectorAll('.a').forEach(e=>{{const k=ease((t-parseFloat(e.dataset.in))/0.45);
    e.style.opacity=k;e.style.transform=`translateY(${{(1-k)*34}}px)`;}});
  document.querySelectorAll('.fill').forEach(e=>{{const k=ease((t-parseFloat(e.dataset.in))/0.9);e.style.width=(k*parseFloat(e.dataset.w))+'%';}});
  document.querySelectorAll('.big .cnt').forEach(e=>{{const p=e.closest('.a');const k=ease((t-parseFloat(p.dataset.in))/1.3);
    e.textContent=fmt(Math.round(k*parseInt(e.dataset.to)),e.dataset.dots==='1');}});
  const ph=document.querySelector('.ph');if(ph)ph.style.transform=`scale(${{1+0.012*t}})`;
  const cur=document.querySelector('.seg[data-i="{cur}"]');cur.classList.add('cur');cur.querySelector('.sf').style.width=(prog*100)+'%';
}}
</script></body></html>"""


def render(spec_path):
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    out = (ROOT / spec["saida"]).resolve() if not Path(spec["saida"]).is_absolute() else Path(spec["saida"])
    out.mkdir(parents=True, exist_ok=True)
    chapters, cenas = spec["capitulos"], spec["cenas"]
    chap_dur = {}
    for s in cenas:
        chap_dur[s["capitulo"]] = chap_dur.get(s["capitulo"], 0) + float(s.get("duracao", 5))
    from playwright.sync_api import sync_playwright
    mp4 = out / "reel.mp4"
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-c:v", "mjpeg", "-r", str(FPS), "-i", "-",
                           "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-shortest",
                           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                           "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(mp4)], stdin=subprocess.PIPE)
    finals, elapsed_in_chap = [], {}
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--allow-file-access-from-files"])
        pg = b.new_page(viewport={"width": W, "height": H})
        tmp = out / "_tmp.html"
        base_dir = Path(spec_path).resolve().parent
        for i, s in enumerate(cenas):
            ch = s["capitulo"]
            if s.get("imagem"):
                fimg = (base_dir / s["imagem"]).resolve()
                if fimg.exists():
                    s = dict(s, _img=str(fimg))
                else:
                    print(f"AVISO: imagem não encontrada: {fimg}", file=sys.stderr)
            tmp.write_text(page(s, chapters, ch), encoding="utf-8")
            pg.goto(tmp.as_uri()); pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(120)
            dur = float(s.get("duracao", 5)); n = int(dur * FPS)
            base = elapsed_in_chap.get(ch, 0.0)
            for f in range(n):
                t = f / FPS
                pg.evaluate(f"draw({t},{(base + t) / chap_dur[ch]})")
                ff.stdin.write(pg.screenshot(type="jpeg", quality=88))
            elapsed_in_chap[ch] = base + dur
            fin = out / f"cena{i+1:02d}.png"
            pg.evaluate(f"draw(99,{elapsed_in_chap[ch] / chap_dur[ch]})")
            pg.screenshot(path=str(fin)); finals.append(fin)
        tmp.unlink(missing_ok=True); b.close()
    ff.stdin.close(); ff.wait()
    # capa = quadro final da 1ª cena
    (out / "capa.png").write_bytes(finals[0].read_bytes())
    from PIL import Image
    ims = [Image.open(f) for f in finals]; tw = 270; th = 480; cols = min(len(ims), 6); rows = (len(ims) + cols - 1) // cols
    S = Image.new("RGB", (cols * (tw + 14) + 14, rows * (th + 14) + 14), "#dddddd")
    for j, im in enumerate(ims):
        S.paste(im.resize((tw, th)), (14 + (j % cols) * (tw + 14), 14 + (j // cols) * (th + 14)))
    S.save(out / "preview.png")
    for f in finals:
        f.unlink()
    rot = ["# Narração (opcional)\n", "Texto para voz, se for gravar ou usar narração. Tempo de cada cena entre parênteses.\n"]
    for i, s in enumerate(cenas):
        if s.get("narracao"):
            rot.append(f"- **{chapters[s['capitulo']]}** ({s.get('duracao',5)}s): {s['narracao']}")
    (out / "roteiro.md").write_text("\n".join(rot) + "\n", encoding="utf-8")
    total = sum(float(s.get("duracao", 5)) for s in cenas)
    print(json.dumps({"saida": str(out), "reel": str(mp4), "duracao_s": total}, ensure_ascii=False))


if __name__ == "__main__":
    render(sys.argv[1])
