"""Servidor de desenvolvimento: portal + API no mesmo endereço, como na Vercel.

    pip install -r requirements-dev.txt
    python scripts/dev.py

Depois abra http://localhost:8000
"""

import json
import sys
from pathlib import Path

import uvicorn
from fastapi.staticfiles import StaticFiles

AQUI = Path(__file__).resolve().parents[1] / "portal-laboratorio"
sys.path.insert(0, str(AQUI / "api"))

from index import app  # noqa: E402

# Mesmos cabeçalhos de segurança da produção (vercel.json), para pegar erros cedo.
_CABECALHOS = {
    c["key"]: c["value"]
    for regra in json.loads((AQUI / "vercel.json").read_text(encoding="utf-8")).get("headers", [])
    for c in regra["headers"]
    if c["key"] != "Strict-Transport-Security"  # só faz sentido com HTTPS
}


@app.middleware("http")
async def cabecalhos_de_seguranca(request, call_next):
    resposta = await call_next(request)
    resposta.headers.update(_CABECALHOS)
    return resposta


app.mount("/", StaticFiles(directory=AQUI, html=True), name="portal")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
