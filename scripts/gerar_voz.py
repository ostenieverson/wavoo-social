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


def gemini_tts(texto, voz, instr, key):
    """Gemini TTS (camada gratuita da API do Google). Devolve WAV."""
    import base64, io, wave
    prompt = f"{instr}\n\nTexto: {texto}"
    last = None
    for model in (os.environ.get("GEMINI_TTS_MODEL") or "gemini-2.5-flash-preview-tts", "gemini-2.5-flash-tts", "gemini-2.5-pro-preview-tts"):
        body = {"contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"responseModalities": ["AUDIO"], "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voz}}}}}
        req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
                                     data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                data = json.loads(r.read())
            pcm = base64.b64decode(data["candidates"][0]["content"]["parts"][0]["inlineData"]["data"])
            buf = io.BytesIO()
            with wave.open(buf, "wb") as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(pcm)
            return buf.getvalue(), model
        except urllib.error.HTTPError as e:
            last = f"{model}: {e.code} {e.read()[:200].decode(errors='ignore')}"
    raise RuntimeError(last)


_kokoro = {}
def kokoro_tts(texto, voz, velocidade=1.1):
    """Kokoro (código aberto, Apache 2.0), roda local no Actions. Vozes pt-BR: pm_alex, pm_santa (masc.), pf_dora (fem.)."""
    import io, numpy as np, soundfile as sf
    from kokoro import KPipeline
    if "p" not in _kokoro:
        _kokoro["p"] = KPipeline(lang_code="p")
    audio = [a for _, _, a in _kokoro["p"](texto, voice=voz, speed=velocidade)]
    buf = io.BytesIO(); sf.write(buf, np.concatenate(audio), 24000, format="WAV")
    return buf.getvalue()


def to_mp3(wav_bytes, out):
    import subprocess, tempfile
    with tempfile.NamedTemporaryFile(suffix=".wav") as t:
        t.write(wav_bytes); t.flush()
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", t.name, "-b:a", "160k", str(out)], check=True)


def main():
    key = os.environ.get("OPENAI_API_KEY")
    gkey = os.environ.get("GEMINI_API_KEY")
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
            prov = f.get("provedor") or cfg.get("provedor", "openai")
            if prov in ("gemini", "kokoro"):
                try:
                    if prov == "gemini":
                        if not gkey:
                            raise RuntimeError("secret GEMINI_API_KEY ausente")
                        wav, m = gemini_tts(f["texto"], voz, instr, gkey)
                    else:
                        wav, m = kokoro_tts(f["texto"], voz, float(f.get("velocidade", cfg.get("velocidade", 1.1)))), "kokoro"
                    to_mp3(wav, out)
                    log[f["arquivo"]] = {"status": "ok", "provedor": prov, "modelo": m, "voz": voz, "segundos": round(time.time() - t0)}
                except Exception as e:
                    log[f["arquivo"]] = {"status": "erro", "provedor": prov, "erro": str(e)[:400]}
                print(spec, f["arquivo"], log[f["arquivo"]]["status"])
                continue
            if not key:
                log[f["arquivo"]] = {"status": "erro", "erro": "secret OPENAI_API_KEY ausente"}; continue
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
