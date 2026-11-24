#!/usr/bin/env python3
"""Reel narrado estilo anúncio (fundo claro, telas do WavooAI animadas, legenda curta sincronizada) para o @wavooai.

Uso:
  python3 scripts/render_narrado.py media/AAAA-MM-DD/<slug>/spec.json [--trilha]

Precisa de voz/cenaNN.mp3 ao lado do spec (gerados pelo GitHub Actions a partir de narracao.json, voz Charon).
A duração de cada cena é a da fala. A voz é acelerada (spec "acelerar", padrão 1.12) e as pausas são cortadas.
Saída na pasta "saida": reel.mp4 (voz + efeitos, SEM música: o som em alta entra pelo Postiz),
reel-preview.mp4 (com trilha sintética, só para revisão), capa.png, preview.png, legenda-falas.txt.
Com --trilha, a trilha sintética também vai no reel.mp4 (use quando não houver som do Postiz).

Spec:
{
 "formato": "narrado", "saida": "media/2026-11-15/reel-espera", "acelerar": 1.12,
 "cenas": [ {"tipo": "...", "fala": "texto falado; **palavra** = destaque na legenda", ...campos do tipo} ]
}
O texto de "fala" tem de ser igual ao de narracao.json (sem os **).
Tipos:
  frase    linhas:[...] (entram uma a uma; ~~x~~ = riscado, ==x== = marca-texto azul) [kicker]
  chat     nome, [status], mensagens:[{de:"cliente"|"loja"|"ia", texto, hora}] [rodape: "Visto às 10:02"] [ia_tag: rótulo da bolha da IA, p/ outro idioma]
  notifs   itens:[{app:"WhatsApp"|"Instagram"|"Messenger"|"E-mail"|"Site", nome, texto, hora}] [titulo]
  inbox    [titulo] conversas:[{canal, nome, texto, tempo, [nao_lidas]}] [destaque: índice]
  kanban   colunas:[...], cards:[{titulo, sub, coluna}], [move:{card: índice, colunas:[1,2]}]
  cta      titulo, [palavra], [canal: comentario|direct], [texto], [acao]
"""
import html, json, re, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "node_modules" / "@fontsource"
ICONS = ROOT / "node_modules" / "lucide-static" / "icons"
LOGO = ROOT / "brand" / "logo" / "wavoo-logo-marinho.png"
W, H, FPS = 1080, 1920, 30
NAVY, BLUE, BG = "#101A31", "#3155FF", "#F4F6FB"
CANAIS = {  # cor, ícone lucide (sem logotipos de marca)
    "WhatsApp": ("#25D366", "message-circle"), "Instagram": ("#E1306C", "camera"), "Messenger": ("#0A7CFF", "send"),
    "E-mail": ("#F59E0B", "mail"), "Site": ("#6D5BFF", "globe"), "Telegram": ("#2AABEE", "send"), "TikTok": ("#111111", "music"),
}


def font_css():
    out = []
    for fam, pkg, ws in (("Outfit", "outfit", (500, 700, 800, 900)), ("Inter", "inter", (400, 500, 600, 700))):
        for w in ws:
            p = FONTS / pkg / "files" / f"{pkg}-latin-{w}-normal.woff2"
            out.append(f"@font-face{{font-family:'{fam}';font-weight:{w};src:url('file://{p}') format('woff2');}}")
    return "\n".join(out)


def icon(name, size=40, sw=2.4):
    f = ICONS / f"{name}.svg"
    if not f.exists():
        f = ICONS / "circle.svg"
    svg = f.read_text()
    svg = re.sub(r'width="\d+"', f'width="{size}"', svg, count=1)
    svg = re.sub(r'height="\d+"', f'height="{size}"', svg, count=1)
    svg = re.sub(r'stroke-width="[\d.]+"', f'stroke-width="{sw}"', svg)
    return re.sub(r"<!--.*?-->", "", svg, flags=re.S)


def rich(t):
    t = html.escape(t or "")
    t = re.sub(r"~~(.+?)~~", r'<span class="risc">\1</span>', t)
    t = re.sub(r"==(.+?)==", r'<span class="mk">\1</span>', t)
    t = re.sub(r"\*\*(.+?)\*\*", r'<span class="hl">\1</span>', t)
    return t.replace("\n", "<br>")


def A(t0, inner, cls="", sfx=None, extra=""):
    """Elemento animado (pop) que entra no segundo t0 da cena; sfx = efeito sonoro no mesmo instante."""
    return f'<div class="a {cls}" data-in="{t0:.2f}" data-sfx="{sfx or ""}" {extra}>{inner}</div>'


def spread(n, dur, start=0.15, end_frac=0.78):
    """Momentos de entrada para n elementos, distribuídos ao longo da fala."""
    if n <= 0:
        return []
    end = max(start + 0.3, dur * end_frac)
    return [start + (end - start) * k / max(1, n - 1) if n > 1 else start for k in range(n)]


def badge(canal, size=64):
    cor, ic = CANAIS.get(canal, ("#8892AB", "message-circle"))
    return f'<div class="badge" style="background:{cor};width:{size}px;height:{size}px">{icon(ic, int(size*0.55), 2.6)}</div>'


def window(title_html, body, cls=""):
    return (f'<div class="win {cls}"><div class="wbar"><i></i><i></i><i></i><div class="wt">{title_html}</div></div>'
            f'<div class="wbody">{body}</div></div>')


def scene_html(s, D):
    tipo = s.get("tipo", "frase")
    if tipo == "frase":
        ls = s.get("linhas", [])
        ts = spread(len(ls), D, 0.05, 0.55)
        k = A(0.0, rich(s["kicker"]), "kicker") if s.get("kicker") else ""
        return f'<div class="stage frase">{k}' + "".join(A(t, rich(l), "ln", "pop") for t, l in zip(ts, ls)) + "</div>"
    if tipo == "chat":
        ms = s.get("mensagens", [])
        ts = spread(len(ms), D, 0.1, 0.8)
        rows = []
        for t, m in zip(ts, ms):
            de = m.get("de", "cliente")
            tag = f'<div class="iatag">{icon("sparkles", 26)} {html.escape(s.get("ia_tag", "Sugestão da IA"))}</div>' if de == "ia" else ""
            tick = '<span class="tk">✓✓</span>' if de != "cliente" else ""
            rows.append(A(t, f'{tag}<div class="bt">{rich(m.get("texto",""))}</div><div class="bh">{html.escape(m.get("hora",""))}{tick}</div>',
                          f"bub {de}", "pop"))
        rod = A(ts[-1] + 0.35 if ts else 0.5, rich(s["rodape"]), "visto") if s.get("rodape") else ""
        head = (f'<div class="av">{html.escape((s.get("nome","C") or "C")[0])}</div><div><b>{html.escape(s.get("nome","Cliente"))}</b>'
                f'<span>{html.escape(s.get("status","online"))}</span></div>')
        return f'<div class="stage">{window(head, "".join(rows) + rod, "chatw")}</div>'
    if tipo == "notifs":
        it = s.get("itens", [])
        ts = spread(len(it), D, 0.1, 0.75)
        tit = A(0.0, rich(s["titulo"]), "stitle") if s.get("titulo") else ""
        rows = [A(t, f'{badge(n.get("app","WhatsApp"))}<div class="nb"><div class="nh"><b>{html.escape(n.get("app",""))}</b><span>{html.escape(n.get("hora","agora"))}</span></div>'
                     f'<div class="nn">{html.escape(n.get("nome",""))}</div><div class="nt">{rich(n.get("texto",""))}</div></div>', "nt-card", "ping")
                for t, n in zip(ts, it)]
        return f'<div class="stage notifs">{tit}{"".join(rows)}</div>'
    if tipo == "inbox":
        cv = s.get("conversas", [])
        ts = spread(len(cv), D, 0.1, 0.7)
        dz = s.get("destaque")
        rows = []
        for i, (t, c) in enumerate(zip(ts, cv)):
            nl = f'<em>{c["nao_lidas"]}</em>' if c.get("nao_lidas") else ""
            rows.append(A(t, f'{badge(c.get("canal","WhatsApp"), 72)}<div class="rb"><div class="rh"><b>{html.escape(c.get("nome",""))}</b><span>{html.escape(c.get("tempo",""))}</span></div>'
                             f'<div class="rt">{rich(c.get("texto",""))}{nl}</div></div>', f'row {"dz" if dz == i else ""}', "pop"))
        head = f'{icon("inbox", 34)}<b>{html.escape(s.get("titulo","Caixa de entrada"))}</b><span class="wv">WavooAI</span>'
        return f'<div class="stage">{window(head, "".join(rows), "inboxw")}</div>'
    if tipo == "kanban":
        cols = s.get("colunas", ["Novo", "Negociando", "Fechado"])
        cards = s.get("cards", [])
        ts = spread(len(cards), D, 0.1, 0.45)
        mv = s.get("move") or {}
        colhtml = "".join(f'<div class="col"><div class="ch">{html.escape(c)}<span>{sum(1 for k in cards if k.get("coluna")==i)}</span></div></div>'
                          for i, c in enumerate(cols))
        ch = []
        for i, (t, c) in enumerate(zip(ts, cards)):
            extra = ""
            if i == mv.get("card"):
                path = [c.get("coluna", 0)] + list(mv.get("colunas", []))
                extra = f'data-path="{",".join(map(str, path))}" data-t0="{D*0.5:.2f}" data-t1="{D*0.92:.2f}"'
            ch.append(A(t, f'<b>{rich(c.get("titulo",""))}</b><span>{rich(c.get("sub",""))}</span>', "kc", "pop",
                        f'data-col="{c.get("coluna",0)}" data-slot="{sum(1 for k in cards[:i] if k.get("coluna")==c.get("coluna"))}" {extra}'))
        head = f'{icon("kanban", 34)}<b>{html.escape(s.get("titulo","Funil de vendas"))}</b><span class="wv">WavooAI</span>'
        return f'<div class="stage">{window(head, f"<div class=board style=--n:{len(cols)}>{colhtml}{"".join(ch)}</div>", "kanw")}</div>'
    if tipo == "cta":
        parts = [A(0.05, rich(s.get("titulo", "")), "ctat", "pop")]
        t = 0.35
        if s.get("palavra"):
            verbo = s.get("verbo") or ("Manda no Direct" if s.get("canal") == "direct" else "Comenta")
            parts.append(A(t, f'<span>{verbo}</span><b>{html.escape(s["palavra"])}</b>', "kw", "ping")); t += 0.4
        if s.get("texto"):
            parts.append(A(t, rich(s["texto"]), "ctx")); t += 0.35
        if s.get("acao"):
            parts.append(A(t, rich(s["acao"]), "btn"))
        return f'<div class="stage cta">{"".join(parts)}</div>'
    raise SystemExit(f"tipo de cena desconhecido: {tipo}")


def chunks(fala):
    """Quebra a fala em blocos de 2–3 palavras (legenda). Mantém **destaque**. Devolve [(html, peso)]."""
    toks = re.findall(r"\*\*.+?\*\*|\S+", fala)
    words = []
    for t in toks:
        if t.startswith("**"):
            ws = t[2:-2].split()
            words += [(w, True) for w in ws]
        else:
            words.append((t, False))
    out, cur = [], []
    for i, (w, hl) in enumerate(words):
        cur.append((w, hl))
        end_punct = re.search(r"[.,!?…:;]$", w)
        nxt_hl = i + 1 < len(words) and words[i + 1][1] and not hl
        if len(cur) >= 3 or (end_punct and len(cur) >= 1) or (len(cur) == 2 and nxt_hl):
            out.append(cur); cur = []
    if cur:
        if out and len(cur) == 1 and len(out[-1]) < 3:
            out[-1] += cur
        else:
            out.append(cur)
    res = []
    for c in out:
        txt = " ".join(w for w, _ in c)
        peso = len(re.sub(r"[^\wÀ-ÿ]", "", txt)) + 2
        hh = " ".join(f'<span class="ck">{html.escape(w.rstrip(".,;:"))}</span>' if hl else html.escape(w.rstrip(".,;:")) for w, hl in c)
        res.append((hh, peso))
    return res


def page(s, D, idx, total, caps, start):
    caps_js = json.dumps(caps)
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
{font_css()}
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:{W}px;height:{H}px;overflow:hidden}}
body{{background:{BG};color:{NAVY};font-family:Inter,sans-serif;position:relative}}
.blob{{position:absolute;border-radius:50%;filter:blur(90px);opacity:.55}}
.b1{{width:700px;height:700px;background:#C9D4FF;left:-200px;top:-120px}}
.b2{{width:620px;height:620px;background:#D7F5E6;right:-220px;top:760px}}
.grid{{position:absolute;inset:0;background-image:radial-gradient(#10203f14 2px,transparent 2px);background-size:44px 44px}}
.prog{{position:absolute;top:70px;left:80px;right:80px;height:8px;border-radius:8px;background:#10203f14}}
.prog i{{display:block;height:100%;width:0;border-radius:8px;background:{BLUE}}}
.wrap{{position:absolute;top:150px;left:70px;right:70px;height:1080px;display:flex;align-items:center;justify-content:center}}
.stage{{width:100%;display:flex;flex-direction:column;gap:26px}}
.a{{opacity:0}}
.hl{{color:{BLUE}}}
.mk{{background:{BLUE};color:#fff;padding:0 .14em;border-radius:.12em}}
.risc{{position:relative;color:#8C95AD}}
.risc::after{{content:"";position:absolute;left:-4%;right:-4%;top:52%;height:.12em;background:#FF4D5E;border-radius:.1em;transform-origin:left;transform:scaleX(var(--rx,0))}}
.frase{{gap:6px}}
.ln{{font:900 150px/1.02 Outfit;letter-spacing:-4px}}
.kicker{{align-self:flex-start;background:{NAVY};color:#fff;font:700 32px Outfit;padding:12px 28px;border-radius:999px;margin-bottom:20px}}
.win{{background:#fff;border-radius:44px;box-shadow:0 40px 90px #1b2b5a26,0 4px 14px #1b2b5a14;overflow:hidden;width:100%}}
.wbar{{display:flex;align-items:center;gap:12px;padding:30px 34px;border-bottom:2px solid #EEF1F7}}
.wbar>i{{width:18px;height:18px;border-radius:50%;background:#E3E7F0}}
.wt{{flex:1;display:flex;align-items:center;gap:18px;margin-left:16px;font:600 30px Inter;color:#55607A}}
.wt b{{color:{NAVY};font:800 36px Outfit;display:block}}
.wt span{{display:block;font:500 24px Inter;color:#2DBE6C}}
.wt .wv{{margin-left:auto;font:800 24px Outfit;color:{BLUE};background:#EAF0FF;padding:8px 18px;border-radius:999px}}
.av{{width:72px;height:72px;border-radius:50%;background:linear-gradient(135deg,#9FB4FF,{BLUE});color:#fff;font:800 34px Outfit;display:flex;align-items:center;justify-content:center}}
.wbody{{padding:34px;display:flex;flex-direction:column;gap:22px;background:#F7F8FC;min-height:640px}}
.bub{{max-width:78%;padding:22px 28px 16px;border-radius:30px;font-size:38px;line-height:1.3;box-shadow:0 4px 10px #1b2b5a10}}
.bub.cliente{{align-self:flex-start;background:#fff;border-top-left-radius:8px}}
.bub.loja{{align-self:flex-end;background:#DCF8C6;border-top-right-radius:8px}}
.bub.ia{{align-self:flex-end;background:#EAF0FF;border:3px dashed {BLUE};border-top-right-radius:8px}}
.iatag{{display:flex;align-items:center;gap:8px;font:700 24px Outfit;color:{BLUE};margin-bottom:8px}}
.bh{{text-align:right;font-size:22px;color:#8892AB;margin-top:6px}}
.tk{{color:#34B7F1;margin-left:8px;font-weight:700}}
.visto{{align-self:center;font:600 26px Inter;color:#8892AB;background:#EEF1F7;padding:10px 24px;border-radius:999px}}
.stitle{{font:900 76px/1.05 Outfit;letter-spacing:-2px;margin-bottom:12px}}
.notifs{{gap:22px}}
.nt-card{{display:flex;gap:24px;align-items:flex-start;background:#fff;border-radius:36px;padding:28px 30px;box-shadow:0 24px 60px #1b2b5a22}}
.badge{{flex:none;border-radius:22px;display:flex;align-items:center;justify-content:center;color:#fff}}
.nb{{flex:1}} .nh{{display:flex;justify-content:space-between;font:600 26px Inter;color:#6B7590}} .nh b{{color:{NAVY}}}
.nn{{font:700 34px Inter;margin-top:4px}} .nt{{font:400 33px/1.3 Inter;color:#36405C}}
.row{{display:flex;gap:24px;align-items:center;background:#fff;border-radius:28px;padding:22px 26px;border:3px solid transparent}}
.row.dz{{border-color:{BLUE};box-shadow:0 14px 40px #3155ff2e}}
.rb{{flex:1;min-width:0}} .rh{{display:flex;justify-content:space-between;font:700 33px Inter}} .rh span{{font:500 24px Inter;color:#8892AB}}
.rt{{display:flex;justify-content:space-between;gap:12px;font:400 29px Inter;color:#55607A;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.rt em{{flex:none;font:700 24px Inter;font-style:normal;color:#fff;background:{BLUE};border-radius:999px;min-width:40px;height:40px;display:flex;align-items:center;justify-content:center;padding:0 10px}}
.board{{position:relative;display:grid;grid-template-columns:repeat(var(--n),1fr);gap:20px;height:700px}}
.col{{background:#EEF1F7;border-radius:26px;padding:18px}}
.ch{{display:flex;justify-content:space-between;font:800 28px Outfit;color:#55607A;padding:4px 6px 0}}
.ch span{{background:#fff;border-radius:999px;padding:0 14px;font-size:24px}}
.kc{{position:absolute;background:#fff;border-radius:22px;padding:20px 22px;box-shadow:0 10px 26px #1b2b5a1f;display:flex;flex-direction:column;gap:6px;border-left:8px solid {BLUE}}}
.kc b{{font:700 29px/1.2 Inter}} .kc span{{font:500 23px Inter;color:#6B7590}}
.cta{{gap:40px}}
.ctat{{font:900 112px/1.02 Outfit;letter-spacing:-3px}}
.kw{{align-self:flex-start;display:flex;flex-direction:column;gap:6px;background:#fff;border:6px dashed {BLUE};border-radius:36px;padding:34px 48px;box-shadow:0 30px 70px #3155ff26}}
.kw span{{font:600 40px Outfit;color:#55607A}} .kw b{{font:900 120px/1 Outfit;color:{BLUE};letter-spacing:-2px}}
.ctx{{font:500 44px/1.3 Inter;color:#36405C}}
.btn{{align-self:flex-start;background:{NAVY};color:#fff;font:800 42px Outfit;padding:28px 46px;border-radius:999px}}
.cap{{position:absolute;left:60px;right:60px;top:1268px;height:200px;display:flex;align-items:center;justify-content:center;text-align:center}}
.cap div{{font:900 84px/1.08 Outfit;letter-spacing:-1.5px;color:{NAVY};text-shadow:0 2px 0 #fff,0 0 24px #fff}}
.cap .ck{{background:{BLUE};color:#fff;padding:0 .16em;border-radius:.14em;text-shadow:none}}
.foot{{position:absolute;left:0;right:0;top:1500px;display:flex;justify-content:center;align-items:center;gap:18px;font:700 28px Outfit;color:#55607A}}
.foot img{{height:42px}}
</style></head><body>
<div class="blob b1"></div><div class="blob b2"></div><div class="grid"></div>
<div class="prog"><i></i></div>
<div class="wrap">{scene_html(s, D)}</div>
<div class="cap"><div id="cap"></div></div>
<div class="foot"><img src="file://{LOGO}"><span>@wavooai</span></div>
<script>
const CAPS={caps_js}, D={D:.3f}, IDX={idx}, TOTAL={total:.3f}, START={start:.3f};
const back=x=>{{const c1=1.70158,c3=c1+1;x=Math.min(1,Math.max(0,x));return 1+c3*Math.pow(x-1,3)+c1*Math.pow(x-1,2);}};
const ease=x=>x<=0?0:x>=1?1:1-Math.pow(1-x,3);
const io=x=>x<=0?0:x>=1?1:(x<.5?4*x*x*x:1-Math.pow(-2*x+2,3)/2);
const board=document.querySelector('.board');
function cardPos(col,slot){{const cw=(board.clientWidth-20*(board.style.getPropertyValue('--n')-1))/board.style.getPropertyValue('--n');
  return [col*(cw+20)+14, 74+slot*150, cw-28];}}
function draw(t){{
  const wrap=document.querySelector('.wrap');
  const s=0.94+0.06*ease(t/0.35); wrap.style.transform=`translateY(${{Math.sin((START+t)*1.3)*6}}px) scale(${{s+0.012*t/D}})`;
  wrap.style.opacity=ease(t/0.18);
  document.querySelector('.prog i').style.width=((START+t)/TOTAL*100)+'%';
  document.querySelectorAll('.a').forEach(e=>{{const k=(t-parseFloat(e.dataset.in))/0.38;
    e.style.opacity=ease(k*1.6); const sc=0.85+0.15*back(k); e.style.transform=`translateY(${{(1-ease(k))*40}}px) scale(${{sc}})`;
    e.querySelectorAll('.risc').forEach(r=>r.style.setProperty('--rx',ease((t-parseFloat(e.dataset.in)-0.45)/0.35)));}});
  if(board){{const cards=[...document.querySelectorAll('.kc')];const mv=cards.find(e=>e.dataset.path);
    let mvCol=null,mvW=0,mvX,mvY,mvLeave=null;
    if(mv){{const p=mv.dataset.path.split(',').map(Number),t0=+mv.dataset.t0,t1=+mv.dataset.t1,seg=p.length-1;
      const u=Math.min(1,Math.max(0,(t-t0)/(t1-t0)))*seg,i=Math.min(seg-1,Math.floor(u)),f=io(u-i);
      const slotIn=c=>cards.filter(e=>e!==mv&&+e.dataset.col===c).length;
      const a=cardPos(p[i],i===0?+mv.dataset.slot:slotIn(p[i])),b=cardPos(p[i+1],slotIn(p[i+1]));
      mvX=a[0]+(b[0]-a[0])*f;mvY=a[1]+(b[1]-a[1])*f-Math.sin(f*Math.PI)*60;mvW=a[2];
      mvLeave={{col:i===0?p[0]:null,w:i===0?1-f:0,slot:+mv.dataset.slot}};mvCol=f>0.5?p[i+1]:p[i];
      mv.style.boxShadow=f>0&&f<1?'0 30px 60px #3155ff44':'';mv.style.zIndex=5;mv.style.left=mvX+'px';mv.style.top=mvY+'px';mv.style.width=mvW+'px';}}
    const cnt={{}};
    document.querySelectorAll('.col').forEach((c,ci)=>{{let k=0;cards.filter(e=>e!==mv&&+e.dataset.col===ci).forEach((e,j)=>{{
        const before=mvLeave&&mvLeave.col===ci&&mvLeave.slot<=j?mvLeave.w:0;const [x,y,w]=cardPos(ci,j+before);
        e.style.left=x+'px';e.style.top=y+'px';e.style.width=w+'px';k++;}});
      if(mv&&mvCol===ci)k++;c.querySelector('.ch span').textContent=k;}});
  }}
  let cur=CAPS[0];for(const c of CAPS){{if(t>=c[0])cur=c;}}
  const el=document.getElementById('cap');if(el.dataset.k!==String(cur[0])){{el.innerHTML=cur[1];el.dataset.k=String(cur[0]);}}
  const k=(t-cur[0])/0.16;el.style.transform=`scale(${{0.9+0.1*back(k)}})`;el.style.opacity=ease(k*2);
}}
</script></body></html>"""


def adur(f):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def make_sfx(d):
    d.mkdir(exist_ok=True)
    sx = {"ping": d / "ping.wav", "pop": d / "pop.wav", "whoosh": d / "whoosh.wav"}
    run = lambda *a: subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *a], check=True)
    run("-f", "lavfi", "-i", "sine=f=1318:d=0.11", "-f", "lavfi", "-i", "sine=f=1760:d=0.22", "-filter_complex",
        "[0]afade=t=out:st=0.06:d=0.05,volume=0.28[a];[1]afade=t=out:st=0.05:d=0.17,volume=0.28,adelay=90|90[b];[a][b]amix=inputs=2:normalize=0,aformat=channel_layouts=stereo",
        "-ar", "44100", str(sx["ping"]))
    run("-f", "lavfi", "-i", "sine=f=620:d=0.09", "-af", "asetrate=44100*1.6,aresample=44100,afade=t=out:st=0.01:d=0.08,volume=0.35,aformat=channel_layouts=stereo",
        "-ar", "44100", str(sx["pop"]))
    run("-f", "lavfi", "-i", "anoisesrc=d=0.45:c=pink:a=0.5", "-af",
        "highpass=f=600,lowpass=f=6000,afade=t=in:d=0.22,afade=t=out:st=0.22:d=0.23,volume=0.22,aformat=channel_layouts=stereo",
        "-ar", "44100", str(sx["whoosh"]))
    return sx


def make_bed(dur, out):
    """Trilha sintética simples (sem direitos autorais) só para a prévia."""
    import numpy as np, soundfile as sf
    sr = 44100; bpm = 118; n = int(sr * dur); y = np.zeros(n); beat = 60 / bpm
    rng = np.random.default_rng(1)
    t = np.arange(int(sr * .35)) / sr; kick = np.sin(2 * np.pi * (50 + 90 * np.exp(-t * 30)) * t) * np.exp(-t * 9)
    th = np.arange(int(sr * .06)) / sr; hat = np.diff(rng.standard_normal(len(th)) * np.exp(-th * 70), prepend=0)
    st = np.arange(int(sr * .18)) / sr; sn = (rng.standard_normal(len(st)) * .6 + np.sin(2 * np.pi * 190 * st)) * np.exp(-st * 22)
    def add(sig, pos, g):
        i = int(pos * sr); j = min(n, i + len(sig))
        if 0 <= i < n:
            y[i:j] += sig[:j - i] * g
    k, p = 0, 0.0
    while p < dur:
        b = k % 4
        if b in (0, 2): add(kick, p, .9)
        if b in (1, 3): add(sn, p, .35)
        add(hat, p + beat / 2, .25)
        if b == 0:
            f = 440 * 2 ** (([45, 45, 48, 43][(k // 4) % 4] - 69) / 12); L = int(sr * beat * 4); tt = np.arange(L) / sr
            env = np.minimum(1, tt * 8) * np.minimum(1, (beat * 4 - tt) * 8)
            add((np.sin(2 * np.pi * f * tt) + .5 * np.sin(2 * np.pi * f * 1.5 * tt) + .3 * np.sin(2 * np.pi * f * 2 * tt)) * env * .18, p, 1)
        k += 1; p += beat
    y /= np.max(np.abs(y)) * 1.1
    sf.write(out, y, sr)


def render(spec_path, trilha=False):
    spec_path = Path(spec_path).resolve()
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    base = spec_path.parent
    out = (ROOT / spec["saida"]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    tmpd = out / "_tmp"; tmpd.mkdir(exist_ok=True)
    cenas = spec["cenas"]
    acel = float(spec.get("acelerar", 1.12))
    # 1) voz: corta pausas, acelera, mede
    vozes, durs = [], []
    for i, c in enumerate(cenas):
        src = base / "voz" / f"cena{i+1:02d}.mp3"
        if not src.exists():
            raise SystemExit(f"falta {src} (rode o workflow de voz)")
        pv = tmpd / f"v{i+1:02d}.wav"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-af",
                        "silenceremove=start_periods=1:start_threshold=-45dB:stop_periods=-1:stop_duration=0.16:stop_threshold=-42dB,"
                        f"atempo={acel},aresample=44100,aformat=channel_layouts=stereo", str(pv)], check=True)
        d = adur(pv)
        vozes.append(pv); durs.append(round(d + float(c.get("respiro", 0.12)), 3))
    durs[-1] += 1.4  # CTA fica na tela depois da fala
    total = sum(durs)
    # 2) vídeo
    from playwright.sync_api import sync_playwright
    silent = tmpd / "video.mp4"
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-c:v", "mjpeg", "-r", str(FPS), "-i", "-",
                           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", str(silent)], stdin=subprocess.PIPE)
    events, finals, falas, t_abs = [], [], [], 0.0
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--allow-file-access-from-files"])
        pg = b.new_page(viewport={"width": W, "height": H})
        tmp = tmpd / "page.html"
        for i, c in enumerate(cenas):
            D = durs[i]
            vd = D - float(c.get("respiro", 0.12)) - (1.4 if i == len(cenas) - 1 else 0)
            ch = chunks(c.get("fala", ""))
            tot_w = sum(w for _, w in ch) or 1
            caps, acc = [], 0.04
            for hh, w in ch:
                caps.append([round(acc, 3), hh]); acc += vd * w / tot_w
            falas.append(re.sub(r"\*\*", "", c.get("fala", "")))
            tmp.write_text(page(c, D, i, total, caps, t_abs), encoding="utf-8")
            pg.goto(tmp.as_uri()); pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(100)
            for e in pg.evaluate("[...document.querySelectorAll('.a')].map(e=>[parseFloat(e.dataset.in),e.dataset.sfx])"):
                if e[1]:
                    events.append((e[1], t_abs + e[0]))
            if i:
                events.append(("whoosh", t_abs - 0.08))
            for f in range(int(round(D * FPS))):
                pg.evaluate(f"draw({f / FPS})")
                ff.stdin.write(pg.screenshot(type="jpeg", quality=88))
            pg.evaluate(f"draw({D - 0.05})")
            fin = tmpd / f"f{i+1:02d}.png"; pg.screenshot(path=str(fin)); finals.append(fin)
            t_abs += D
        b.close()
    ff.stdin.close(); ff.wait()
    # 3) áudio: vozes em sequência + efeitos
    sx = make_sfx(tmpd / "sfx")
    ins, filt, labs, t0 = [], [], [], 0.0
    def add(f, at, vol=1.0):
        k = len(ins) // 2; ins.extend(["-i", str(f)]); ms = max(0, int(at * 1000))
        filt.append(f"[{k}]aresample=44100,aformat=channel_layouts=stereo,volume={vol},adelay={ms}|{ms}[a{k}]"); labs.append(f"[a{k}]")
    for i, v in enumerate(vozes):
        add(v, t0 + 0.04, 1.0); t0 += durs[i]
    for name, at in events:
        add(sx[name], at, 0.9)
    mix = f"{''.join(labs)}amix=inputs={len(labs)}:normalize=0:duration=longest,apad,atrim=0:{total:.2f}"
    voice = tmpd / "voz.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *ins, "-filter_complex", ";".join(filt) + ";" + mix + "[o]",
                    "-map", "[o]", str(voice)], check=True)
    bed = tmpd / "bed.wav"; make_bed(total + 1, bed)
    def mux(dst, with_bed):
        if with_bed:
            fc = (f"[1]aformat=channel_layouts=stereo[v];[2]aformat=channel_layouts=stereo,volume=0.13,afade=t=out:st={total-0.8:.2f}:d=0.8[b];"
                  f"[v][b]amix=inputs=2:normalize=0:duration=first,loudnorm=I=-14:TP=-1.5:LRA=11[a]")
            extra = ["-i", str(bed)]
        else:
            fc, extra = "[1]loudnorm=I=-14:TP=-1.5:LRA=11[a]", []
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(silent), "-i", str(voice), *extra, "-filter_complex", fc,
                        "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(dst)], check=True)
    mux(out / "reel.mp4", trilha)
    mux(out / "reel-preview.mp4", True)
    # 4) capa, prévia, falas
    shutil.copy(finals[0], out / "capa.png")
    from PIL import Image
    ims = [Image.open(f) for f in finals]; tw, th = 270, 480; cols = min(len(ims), 7); rows = (len(ims) + cols - 1) // cols
    S = Image.new("RGB", (cols * (tw + 14) + 14, rows * (th + 14) + 14), "#dddddd")
    for j, im in enumerate(ims):
        S.paste(im.resize((tw, th)), (14 + (j % cols) * (tw + 14), 14 + (j // cols) * (th + 14)))
    S.save(out / "preview.png")
    (out / "legenda-falas.txt").write_text("\n".join(falas) + "\n", encoding="utf-8")
    shutil.rmtree(tmpd, ignore_errors=True)
    print(json.dumps({"reel": str(out / "reel.mp4"), "duracao_s": round(total, 1), "cenas": [round(d, 2) for d in durs]}, ensure_ascii=False))


if __name__ == "__main__":
    render(sys.argv[1], "--trilha" in sys.argv)
