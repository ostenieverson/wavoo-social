#!/usr/bin/env python3
"""Gera artes do Instagram do WavooAI a partir de um JSON.

Uso:
  python3 scripts/render.py spec.json            # gera PNGs (e MP4 se formato=reel)
  python3 scripts/render.py spec.json --preview  # também gera preview.png (contact sheet)

Formatos: carrossel (1080x1350, vários slides), post (1080x1350, 1 slide),
story (1080x1920), reel (1080x1920, cenas -> MP4 30fps com texto entrando linha a linha).
Destaque: **palavra** fica na cor de destaque. Quebra de linha: \n.
"""
import html, json, re, subprocess, sys, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "node_modules" / "@fontsource"

PALETTE = {
    "escuro": dict(bg="#101A31", fg="#FFFFFF", muted="#AEB8D6", accent="#369EFF", card="#18264A", line="#2A3A66", pill_bg="#3155FF", pill_fg="#FFFFFF"),
    "claro":  dict(bg="#F5F7FC", fg="#101A31", muted="#55607A", accent="#3155FF", card="#FFFFFF", line="#E6EAF1", pill_bg="#3155FF", pill_fg="#FFFFFF"),
    "azul":   dict(bg="#3155FF", fg="#FFFFFF", muted="#DCE3FF", accent="#101A31", card="#2546E0", line="#5C78FF", pill_bg="#101A31", pill_fg="#FFFFFF"),
}
SIZES = {"carrossel": (1080, 1350), "post": (1080, 1350), "story": (1080, 1920), "reel": (1080, 1920)}


def font_css():
    faces = []
    for fam, pkg, weights in (("Outfit", "outfit", (400, 600, 800, 900)), ("Inter", "inter", (400, 500, 700))):
        for w in weights:
            p = FONTS / pkg / "files" / f"{pkg}-latin-{w}-normal.woff2"
            faces.append(f"@font-face{{font-family:'{fam}';font-weight:{w};src:url('file://{p}') format('woff2');}}")
    return "\n".join(faces)


def rich(text):
    """Escapa HTML, **destaque** -> span, \n -> <br>."""
    t = html.escape(text or "")
    t = re.sub(r"\*\*(.+?)\*\*", r'<span class="hl">\1</span>', t)
    return t.replace("\n", "<br>")


LOGOS = ROOT / "brand" / "logo"


def wordmark(c):
    """Logo oficial: branco p/ fundo escuro, marinho p/ fundo claro, monocromático no fundo azul."""
    f = {"#101A31": "wavoo-logo-branco.png", "#F5F7FC": "wavoo-logo-marinho.png"}.get(c["bg"], "wavoo-logo-monocromatico-branco.png")
    return f'<img class="wm" src="file://{LOGOS / f}" alt="Wavoo">'


def body_for(slide, fmt, idx, total, theme):
    foto = slide.get("_img")
    c = PALETTE["escuro"] if foto else PALETTE[slide.get("tema", theme)]
    lay = slide.get("layout", "texto")
    k = slide.get("kicker", "")
    kick = f'<div class="kicker">{rich(k)}</div>' if k else ""
    titulo = rich(slide.get("titulo", ""))
    texto = f'<p class="txt">{rich(slide["texto"])}</p>' if slide.get("texto") else ""
    tall = fmt in ("story", "reel")

    if lay == "capa":
        main = f'{kick}<h1 class="t-xl">{titulo}</h1>{texto}'
        if fmt == "carrossel":
            main += '<div class="swipe">arrasta pro lado →</div>'
    elif lay == "lista":
        itens = slide.get("itens", [])
        numerada = slide.get("numerada", True)
        rows = "".join(
            f'<div class="row"><div class="bullet">{(str(i+1).zfill(2)) if numerada else "✓"}</div><div class="rowtxt">{rich(it)}</div></div>'
            for i, it in enumerate(itens))
        main = f'{kick}<h2 class="t-l">{titulo}</h2><div class="rows">{rows}</div>{texto}'
    elif lay == "frase":
        main = f'{kick}<h1 class="t-xl center">{titulo}</h1>{texto}'
    elif lay == "comparacao":
        a, b = slide.get("antes", {}), slide.get("depois", {})
        col = lambda d, cls: (f'<div class="col {cls}"><div class="colh">{rich(d.get("titulo",""))}</div>' +
                              "".join(f'<div class="ci">{rich(x)}</div>' for x in d.get("itens", [])) + "</div>")
        main = f'{kick}<h2 class="t-l">{titulo}</h2><div class="cols">{col(a,"bad")}{col(b,"good")}</div>{texto}'
    elif lay == "chat":
        msgs = "".join(
            (f'<div class="sys">{rich(m.get("texto",""))}</div>' if m.get("de")=="sistema" else
             f'<div class="msg {"me" if m.get("de")=="empresa" else "them"}"><div>{rich(m.get("texto",""))}</div>'
             f'<span class="time">{html.escape(m.get("hora",""))}</span></div>') for m in slide.get("mensagens", []))
        nome = html.escape(slide.get("contato", "Cliente"))
        main = (f'{kick}<h2 class="t-m">{titulo}</h2><div class="phone"><div class="ph-head"><div class="av"></div>'
                f'<div><b>{nome}</b><small>online</small></div></div><div class="ph-body">{msgs}</div></div>{texto}')
    elif lay == "kanban":
        cols = "".join(
            f'<div class="kc"><div class="kh">{rich(col.get("titulo",""))}<span>{len(col.get("cards",[]))}</span></div>' +
            "".join(f'<div class="kcard">{rich(cd)}</div>' for cd in col.get("cards", [])) + "</div>"
            for col in slide.get("colunas", []))
        main = f'{kick}<h2 class="t-m">{titulo}</h2><div class="kanban">{cols}</div>{texto}<div class="ilustr">ilustração</div>'
    elif lay == "numero":
        main = f'{kick}<div class="big">{rich(slide.get("numero",""))}</div><h2 class="t-l">{titulo}</h2>{texto}'
    elif lay == "cta":
        kw = slide.get("palavra")
        verbo = "Manda" if slide.get("canal", "comentario") == "direct" else "Comenta"
        kwbox = f'<div class="kw">{verbo} <b>{html.escape(kw)}</b></div>' if kw else ""
        acao = slide.get("acao", "")
        btn = f'<div class="btn">{rich(acao)}</div>' if acao else ""
        main = f'{kick}<h1 class="t-xl">{titulo}</h1>{texto}{kwbox}{btn}'
    elif lay == "enquete":  # story: deixa espaço para o sticker
        main = f'{kick}<h1 class="t-xl center">{titulo}</h1>{texto}<div class="sticker">{rich(slide.get("sticker","espaço do sticker"))}</div>'
    elif lay == "cena":  # reel
        linhas = slide.get("linhas", [])
        upto = slide.get("_upto", len(linhas))
        ls = "".join(f'<div class="ln {"on" if i < upto else "off"}">{rich(l)}</div>' for i, l in enumerate(linhas))
        main = f'{kick}<div class="scene">{ls}</div>'
    else:  # texto
        num = slide.get("numero_etapa")
        badge = (f'<div class="badge">{html.escape(str(num))}</div><div class="ghost">{html.escape(str(num))}</div>') if num else ""
        main = f'{badge}{kick}<h2 class="t-l">{titulo}</h2>{texto}'

    counter = f'<span>{idx+1}/{total}</span>' if fmt == "carrossel" and total > 1 and not foto else ('<span>→</span>' if foto and fmt == "carrossel" and idx < total - 1 else "")
    foot = f'<div class="foot">{wordmark(c)}<span>@wavooai</span>{counter}</div>'
    if fmt == "reel":
        foot = f'<div class="foot reel">{wordmark(c)}<span>@wavooai</span></div>'
    bg = (f'<div class="bgimg" style="background-image:url(\'file://{foto}\')"></div><div class="shade"></div>') if foto else ""
    top = f'<div class="topcount">{str(idx+1).zfill(2)}/{str(total).zfill(2)}</div>' if foto and fmt == "carrossel" and total > 1 else ""
    return c, f'{bg}{top}<div class="wrap {lay} {"tall" if tall else ""} {"temfoto" if foto else ""}"><div class="main">{main}</div>{foot}</div>'


def page(c, inner, w, h, fmt):
    pad_top, pad_bot = (260, 360) if fmt in ("story", "reel") else (96, 64)
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
{font_css()}
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:{w}px;height:{h}px;overflow:hidden}}
body{{background:{c['bg']};color:{c['fg']};font-family:Inter,sans-serif;position:relative}}
body::before{{content:"";position:absolute;inset:0;background:radial-gradient(900px 700px at 85% 0%,{c['accent']}33,transparent 60%),radial-gradient(700px 600px at 0% 100%,{c['pill_bg']}22,transparent 60%);}}
.wrap{{position:relative;height:100%;padding:{pad_top}px 88px {pad_bot}px;display:flex;flex-direction:column}}
.main{{flex:1;display:flex;flex-direction:column;justify-content:center;gap:34px}}
.kicker{{align-self:flex-start;background:{c['pill_bg']};color:{c['pill_fg']};font:600 30px Outfit;padding:12px 26px;border-radius:999px;letter-spacing:.5px}}
h1,h2{{font-family:Outfit;letter-spacing:-1.5px;line-height:1.02}}
.t-xl{{font-weight:900;font-size:{124 if fmt in ('story','reel') else 104}px}}
.t-l{{font-weight:800;font-size:{88 if fmt in ('story','reel') else 72}px}}
.t-m{{font-weight:800;font-size:60px}}
.center{{text-align:center}}
.frase .main,.enquete .main{{align-items:center;text-align:center}}
.frase .kicker,.enquete .kicker{{align-self:center}}
.hl{{color:{c['accent']}}}
.txt{{font-size:{46 if fmt in ('story','reel') else 42}px;line-height:1.36;color:{c['muted']};font-weight:400}}
.txt .hl{{font-weight:700}}
.swipe{{font:600 32px Outfit;color:{c['muted']};margin-top:8px}}
.badge{{width:96px;height:96px;border-radius:28px;background:{c['pill_bg']};color:{c['pill_fg']};font:900 48px Outfit;display:flex;align-items:center;justify-content:center}}
.rows{{display:flex;flex-direction:column;gap:22px}}
.row{{display:flex;gap:26px;align-items:center;background:{c['card']};border:2px solid {c['line']};border-radius:28px;padding:26px 30px}}
.bullet{{flex:none;width:72px;height:72px;border-radius:20px;background:{c['pill_bg']};color:{c['pill_fg']};font:800 32px Outfit;display:flex;align-items:center;justify-content:center}}
.rowtxt{{font-size:40px;line-height:1.25;font-weight:500}}
.cols{{display:grid;grid-template-columns:1fr 1fr;gap:24px}}
.col{{border-radius:28px;padding:30px;display:flex;flex-direction:column;gap:18px;background:{c['card']};border:2px solid {c['line']}}}
.col.good{{border-color:{c['pill_bg']};box-shadow:0 0 0 4px {c['pill_bg']}33}}
.colh{{font:800 40px Outfit}} .col.bad .colh::before{{content:"✕ ";color:#FF6B6B}} .col.good .colh::before{{content:"✓ ";color:{c['accent']}}}
.ci{{font-size:34px;line-height:1.3;color:{c['muted']}}}
.phone{{background:#0B141A;border-radius:44px;overflow:hidden;border:2px solid {c['line']};box-shadow:0 30px 80px #0006}}
.ph-head{{display:flex;gap:18px;align-items:center;background:#1F2C33;color:#E9EDEF;padding:22px 28px;font-size:32px}}
.ph-head small{{display:block;font-size:24px;color:#8696A0}}
.av{{width:64px;height:64px;border-radius:50%;background:linear-gradient(135deg,#6F8BFF,#3155FF)}}
.ph-body{{padding:28px;display:flex;flex-direction:column;gap:16px}}
.msg{{max-width:82%;padding:18px 24px 30px;border-radius:22px;font-size:32px;line-height:1.3;position:relative;color:#E9EDEF}}
.msg.them{{background:#202C33;align-self:flex-start;border-top-left-radius:6px}}
.msg.me{{background:#005C4B;align-self:flex-end;border-top-right-radius:6px}}
.msg .time{{position:absolute;right:16px;bottom:6px;font-size:20px;color:#8696A0}}
.kanban{{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}}
.kc{{background:{c['card']};border:2px solid {c['line']};border-radius:24px;padding:18px;display:flex;flex-direction:column;gap:14px}}
.kh{{font:700 28px Outfit;display:flex;justify-content:space-between}} .kh span{{color:{c['muted']}}}
.kcard{{background:{c['bg']};border-left:6px solid {c['pill_bg']};border-radius:14px;padding:16px;font-size:26px;line-height:1.25}}
.ilustr{{font-size:22px;color:{c['muted']};opacity:.6}}
.big{{font:900 220px Outfit;letter-spacing:-6px;color:{c['accent']};line-height:.9}}
.kw{{align-self:flex-start;border:4px dashed {c['accent']};border-radius:28px;padding:26px 36px;font:600 48px Outfit}}
.kw b{{color:{c['accent']};font-weight:900}}
.btn{{align-self:flex-start;background:{c['pill_bg']};color:{c['pill_fg']};font:800 42px Outfit;padding:28px 44px;border-radius:999px}}
.bgimg{{position:absolute;inset:0;background-size:cover;background-position:center}}
.shade{{position:absolute;inset:0;background:linear-gradient(to top,rgba(16,26,49,.98) 0%,rgba(16,26,49,.9) 28%,rgba(16,26,49,.35) 55%,rgba(16,26,49,0) 72%),linear-gradient(to bottom,rgba(16,26,49,.55) 0%,rgba(16,26,49,0) 14%)}}
.topcount{{position:absolute;top:44px;right:56px;font:600 28px Outfit;color:#fff;opacity:.85;z-index:2}}
.temfoto .main{{justify-content:flex-end;padding-bottom:36px}}
.temfoto .foot>span:last-child{{font-size:40px;color:#fff}}
.temfoto h1,.temfoto h2{{text-transform:uppercase;letter-spacing:-1px;text-shadow:0 4px 30px #0008}}
.temfoto .txt{{color:#E3E8F5}}
body:has(.bgimg)::before{{display:none}}
.sys{{align-self:center;background:#182229;color:#8696A0;font-size:26px;padding:10px 22px;border-radius:14px}}
.ghost{{position:absolute;right:40px;bottom:120px;font:900 520px Outfit;letter-spacing:-20px;color:{c['fg']};opacity:.05;line-height:1}}
.sticker{{margin-top:40px;width:760px;height:300px;border:4px dashed {c['line']};border-radius:40px;display:flex;align-items:center;justify-content:center;color:{c['muted']};font:600 34px Outfit}}
.scene{{display:flex;flex-direction:column;gap:30px}}
.ln{{font:900 124px Outfit;letter-spacing:-2px;line-height:1.04}}
.ln.off{{visibility:hidden}}
.foot{{display:flex;align-items:center;gap:22px;font:600 28px Outfit;color:{c['muted']}}}
.foot>span:last-child{{margin-left:auto}}
.foot.reel{{justify-content:center}} .foot.reel>span:last-child{{margin-left:0}}
.wm{{height:44px;width:auto;display:block}}
</style></head><body>{inner}</body></html>"""


def render(spec_path, preview=False):
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    fmt = spec["formato"]
    theme = spec.get("tema", "escuro")
    w, h = SIZES[fmt]
    out = Path(spec.get("saida", Path(spec_path).with_suffix(""))).resolve()
    out.mkdir(parents=True, exist_ok=True)
    slides = spec["slides"]
    from playwright.sync_api import sync_playwright
    files = []
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--allow-file-access-from-files"])
        pg = b.new_page(viewport={"width": w, "height": h})
        tmp = out / "_tmp.html"

        base = Path(spec_path).resolve().parent

        def shot(slide, i, name):
            if slide.get("imagem") and not slide.get("_img"):
                f = (base / slide["imagem"]).resolve()
                if f.exists():
                    slide = dict(slide, _img=str(f))
                else:
                    print(f"AVISO: imagem não encontrada: {f} (slide {i+1} sai sem foto)", file=sys.stderr)
            c, inner = body_for(slide, fmt, i, len(slides), theme)
            tmp.write_text(page(c, inner, w, h, fmt), encoding="utf-8")
            pg.goto(tmp.as_uri())
            pg.evaluate("document.fonts.ready")
            pg.wait_for_timeout(150)
            f = out / name
            pg.screenshot(path=str(f), type="png")
            return f

        if fmt == "reel":
            clips = []
            for i, s in enumerate(slides):
                linhas = s.get("linhas", [])
                steps = list(range(1, len(linhas) + 1)) or [0]
                for u in steps:
                    ss = dict(s, _upto=u)
                    f = shot(ss, i, f"cena{i+1:02d}_{u}.png")
                    last = (u == steps[-1])
                    dur = float(s.get("duracao", 3.0)) - 0.55 * (len(steps) - 1) if last else 0.55
                    clips.append((f, max(dur, 0.8 if last else 0.55)))
            files = [c[0] for c in clips]
            mp4 = out / "reel.mp4"
            make_video(clips, mp4, w, h)
            files.append(mp4)
        else:
            for i, s in enumerate(slides):
                files.append(shot(s, i, f"{i+1:02d}.png"))
        tmp.unlink(missing_ok=True)
        b.close()
    if preview and fmt != "reel":
        sheet(files, out / "preview.png")
    print(json.dumps({"saida": str(out), "arquivos": [str(f) for f in files]}, ensure_ascii=False, indent=1))


def make_video(clips, mp4, w, h):
    """Cada imagem vira um trecho com zoom lento; trechos unidos com fade curto. Trilha silenciosa."""
    fps = 30
    lst = mp4.parent / "_concat"
    shutil.rmtree(lst, ignore_errors=True); lst.mkdir()
    parts = []
    for n, (img, dur) in enumerate(clips):
        part = lst / f"p{n:03d}.mp4"
        frames = int(dur * fps)
        vf = (f"scale={w*2}:{h*2},zoompan=z='min(1+0.0006*on,1.06)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
              f"d={frames}:s={w}x{h}:fps={fps},format=yuv420p")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(img), "-vf", vf,
                        "-frames:v", str(frames), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", str(part)], check=True)
        parts.append(part)
    (lst / "list.txt").write_text("".join(f"file '{p.name}'\n" for p in parts))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst / "list.txt"),
                    "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-shortest",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(fps),
                    "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(mp4)], check=True)
    shutil.rmtree(lst, ignore_errors=True)


def sheet(files, dest):
    from PIL import Image
    ims = [Image.open(f) for f in files]
    tw = 360; th = int(ims[0].height * tw / ims[0].width)
    cols = min(len(ims), 5); rows = (len(ims) + cols - 1) // cols
    S = Image.new("RGB", (cols * (tw + 16) + 16, rows * (th + 16) + 16), "#dddddd")
    for i, im in enumerate(ims):
        S.paste(im.resize((tw, th)), (16 + (i % cols) * (tw + 16), 16 + (i // cols) * (th + 16)))
    S.save(dest)


if __name__ == "__main__":
    render(sys.argv[1], "--preview" in sys.argv)
