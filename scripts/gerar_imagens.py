#!/usr/bin/env python3
"""Gera imagens por IA a partir de pedidos media/**/imagens.json (roda no GitHub Actions).

Formato de imagens.json:
  [{"arquivo": "img01.png", "prompt": "…", "formato": "retrato" | "quadrado" | "paisagem"}]

Provedor: OPENAI_API_KEY (padrão) ou GEMINI_API_KEY. Modelo: variável IMAGE_MODEL
(padrão gpt-image-2 / gemini-2.5-flash-image). Imagens já existentes não são refeitas.
Saída: PNG ao lado do imagens.json + imagens.log.json com status de cada pedido.
"""
import base64, glob, json, os, sys, time, urllib.request, urllib.error
from pathlib import Path

ESTILO = ("Fotografia editorial realista, luz cinematográfica, profundidade de campo, cores frias com "
          "toques de azul (#3155FF). Sem texto, letras, números, logotipos ou marcas na imagem. "
          "Sem rostos de pessoas reais conhecidas. Espaço livre no terço inferior para texto.")
SIZES = {"retrato": "1024x1536", "quadrado": "1024x1024", "paisagem": "1536x1024"}
ASPECT = {"retrato": "3:4", "quadrado": "1:1", "paisagem": "4:3"}


def post(url, body, headers):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())


def openai(prompt, formato, key, model):
    body = {"model": model, "prompt": prompt, "n": 1, "size": SIZES.get(formato, "1024x1536")}
    try:
        d = post("https://api.openai.com/v1/images/generations", body, {"Authorization": f"Bearer {key}"})
    except urllib.error.HTTPError as e:
        if e.code == 400:  # modelo pode não aceitar "size": tenta sem
            body.pop("size")
            d = post("https://api.openai.com/v1/images/generations", body, {"Authorization": f"Bearer {key}"})
        else:
            raise
    return base64.b64decode(d["data"][0]["b64_json"])


def gemini(prompt, formato, key, model):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": ASPECT.get(formato, "3:4")}}}
    d = post(url, body, {})
    for part in d["candidates"][0]["content"]["parts"]:
        if "inlineData" in part:
            return base64.b64decode(part["inlineData"]["data"])
    raise RuntimeError("Gemini não devolveu imagem")


def main():
    key_o = os.environ.get("OPENAI_API_KEY")
    key_g = os.environ.get("GEMINI_API_KEY")
    if not (key_o or key_g):
        sys.exit("Defina o secret OPENAI_API_KEY ou GEMINI_API_KEY no repositório.")
    model = os.environ.get("IMAGE_MODEL") or ("gpt-image-2" if key_o else "gemini-2.5-flash-image")
    gerou = 0
    for pedido in sorted(glob.glob("media/**/imagens.json", recursive=True)):
        pasta = Path(pedido).parent
        log_path = pasta / "imagens.log.json"
        log = json.loads(log_path.read_text()) if log_path.exists() else {}
        for item in json.loads(Path(pedido).read_text(encoding="utf-8")):
            destino = pasta / item["arquivo"]
            if destino.exists():
                continue
            prompt = f'{item["prompt"].strip()}\n\nEstilo: {ESTILO}'
            for tentativa in range(2):
                try:
                    t = time.time()
                    img = openai(prompt, item.get("formato"), key_o, model) if key_o else gemini(prompt, item.get("formato"), key_g, model)
                    destino.write_bytes(img)
                    log[item["arquivo"]] = {"status": "ok", "modelo": model, "segundos": round(time.time() - t)}
                    gerou += 1
                    break
                except Exception as e:  # noqa: BLE001
                    msg = e.read().decode()[:400] if hasattr(e, "read") else str(e)[:400]
                    log[item["arquivo"]] = {"status": "erro", "modelo": model, "erro": msg}
                    time.sleep(5)
        log_path.write_text(json.dumps(log, ensure_ascii=False, indent=1))
    print(f"imagens geradas: {gerou}")


if __name__ == "__main__":
    main()
