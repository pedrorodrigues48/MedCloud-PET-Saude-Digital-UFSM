"""API do MedCloud: lê o laudo em PDF e devolve os exames encontrados."""

import logging
import os
import re
import sys

import pymupdf
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _extrator import extrair_exames, extrair_id_paciente, linhas_do_pdf  # noqa: E402

TAMANHO_MAXIMO = 10 * 1024 * 1024  # 10 MB
PAGINAS_MAXIMAS = 30

log = logging.getLogger("medcloud")

app = FastAPI(title="MedCloud API", docs_url=None, redoc_url=None, openapi_url=None)

# O portal chama a API no mesmo endereço, então CORS fica fechado por padrão.
# Para liberar outro site, defina CORS_ORIGINS="https://a.com,https://b.com".
_origens = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]
if _origens:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_origens,
        allow_credentials=False,
        allow_methods=["POST"],
        allow_headers=["*"],
    )


def _acesso_pacs(texto: str) -> dict | None:
    """Credenciais de visualizador de imagem (PACS) impressas no laudo."""
    usuario = re.search(r"(?:Usu[aá]rio|Login|Accession(?: Number)?|Protocolo)\s*[:\-]?\s*([\w\d]+)", texto, re.IGNORECASE)
    senha = re.search(r"(?:Senha|Password|Pin)\s*[:\-]?\s*([\w\d@#$%&*!]+)", texto, re.IGNORECASE)
    if not (usuario and senha):
        return None
    url = re.search(r"https?://[\w\-\.]+(?:/[\w\-\./?%&=]*)?", texto)
    return {
        "nome": "Acesso PACS",
        "valor": "Credenciais encontradas",
        "uni": "",
        "tipo": "pacs",
        "usuario": usuario.group(1),
        "senha": senha.group(1),
        "url": url.group(0) if url else "",
    }


@app.post("/api/parse-pdf")
@app.post("/api/process-pdf")
async def process_pdf(file: UploadFile = File(...)):
    conteudo = await file.read(TAMANHO_MAXIMO + 1)
    if len(conteudo) > TAMANHO_MAXIMO:
        raise HTTPException(status_code=413, detail="O PDF passa do limite de 10 MB.")
    if not conteudo.startswith(b"%PDF-"):
        raise HTTPException(status_code=415, detail="O arquivo enviado não é um PDF.")

    try:
        with pymupdf.open(stream=conteudo, filetype="pdf") as documento:
            if documento.page_count > PAGINAS_MAXIMAS:
                raise HTTPException(status_code=413, detail=f"O PDF tem mais de {PAGINAS_MAXIMAS} páginas.")
            linhas = linhas_do_pdf(documento)
    except HTTPException:
        raise
    except Exception:
        # O detalhe do erro fica só no log do servidor, nunca vai para o usuário.
        log.exception("Falha ao abrir o PDF")
        raise HTTPException(status_code=422, detail="Não foi possível ler este PDF.") from None

    dados = extrair_exames(linhas)
    pacs = _acesso_pacs("\n".join(linhas))
    if pacs:
        dados.append(pacs)

    return {
        "dadosClinicos": dados,
        "patientId": extrair_id_paciente(linhas),
        # PDF escaneado (só imagem) não tem texto para ler.
        "semTexto": not any(linha.strip() for linha in linhas),
    }
