#!/usr/bin/env python3
"""Gera narração (TTS) para os reels a partir de media/**/narracao.json.

Formato:
{
 "voz": "onyx",                      # vozes masculinas boas: onyx, ash, echo
 "instrucoes": "Português do Brasil...",  # tom, ritmo, sotaque
 "falas": [{"arquivo": "voz/cena01.mp3", "texto": "...", "voz": "opcional"}]
}
Usa OPENAI_API_KEY (modelo TTS_MODEL, padrão gpt-4o-mini-tts; cai para tts-1-hd se não aceitar).
Pula arquivos que já existem. Grava voz.log.json ao lado.
"""
import glob, json, os, sys, time, urllib.request, urllib.error
from pathlib import Path

INSTR_PADRAO = ("Fale em português do Brasil, sotaque neutro, voz masculina adulta. Tom de narrador de história curta "
                "para redes sociais: confiante, próximo, com pausas curtas e ênfase nas palavras-chave. Ritmo dinâmico, sem soar como anúncio.")


def tts(texto, voz, instr, key, model):
    body = {"model": model, "voice": voz, "input": texto, "response_format": "mp3"}
    if model.startswith("gpt-4o"):
        body["instructions"] = instr
    req = urllib.request.Request("https://api.openai.com/v1/audio/speech", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


def main():
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        sys.exit("Defina o secret OPENAI_API_KEY.")
    model = os.environ.get("TTS_MODEL") or "gpt-4o-mini-tts"
    for spec in sorted(glob.glob("media/**/narracao.json", recursive=True)):
        base = Path(spec).parent
        cfg = json.loads(Path(spec).read_text(encoding="utf-8"))
        logf = base / "voz.log.json"
        log = json.loads(logf.read_text()) if logf.exists() else {}
        for f in cfg.get("falas", []):
            out = base / f["arquivo"]
            if out.exists():
                continue
            out.parent.mkdir(parents=True, exist_ok=True)
            voz = f.get("voz") or cfg.get("voz", "onyx")
            instr = cfg.get("instrucoes") or INSTR_PADRAO
            t0 = time.time()
            for m in (model, "tts-1-hd"):
                try:
                    out.write_bytes(tts(f["texto"], voz, instr, key, m))
                    log[f["arquivo"]] = {"status": "ok", "modelo": m, "voz": voz, "segundos": round(time.time() - t0)}
                    break
                except urllib.error.HTTPError as e:
                    log[f["arquivo"]] = {"status": "erro", "modelo": m, "erro": f"{e.code} {e.read()[:300].decode(errors='ignore')}"}
                except Exception as e:  # rede
                    log[f["arquivo"]] = {"status": "erro", "modelo": m, "erro": str(e)[:300]}
            print(spec, f["arquivo"], log[f["arquivo"]]["status"])
        logf.write_text(json.dumps(log, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
