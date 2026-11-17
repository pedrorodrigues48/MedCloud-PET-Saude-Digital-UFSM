"""Testes da API com PDFs gerados na hora (nenhum laudo real no repositório)."""

import pymupdf as fitz
import pytest
from fastapi.testclient import TestClient

import index

cliente = TestClient(index.app)


def pdf_de_texto(*linhas: str) -> bytes:
    documento = fitz.open()
    pagina = documento.new_page()
    for i, linha in enumerate(linhas):
        pagina.insert_text((50, 60 + 18 * i), linha, fontsize=10)
    return documento.tobytes()


def pdf_em_tabela(linhas: list[tuple[str, ...]], colunas=(50, 250, 330, 420)) -> bytes:
    """Cada célula é escrita separada, como nos laudos em formato de tabela."""
    documento = fitz.open()
    pagina = documento.new_page()
    for i, celulas in enumerate(linhas):
        for x, celula in zip(colunas, celulas, strict=False):
            pagina.insert_text((x, 60 + 20 * i), celula, fontsize=10)
    return documento.tobytes()


def enviar(conteudo: bytes, nome="laudo.pdf"):
    return cliente.post("/api/process-pdf", files={"file": (nome, conteudo, "application/pdf")})


def valores(resposta) -> dict[str, str]:
    return {d["nome"]: d["valor"] for d in resposta.json()["dadosClinicos"]}


def test_laudo_em_texto_corrido():
    resposta = enviar(
        pdf_de_texto(
            "LABORATORIO EXEMPLO - Emitido em 15/11/2026 08:30",
            "ID do Paciente: 510004",
            "HEMOGRAMA",
            "Hemoglobina ........: 13,5 g/dL      13,5 a 17,5",
            "Hematocrito ........: 41,0 %         39 a 50",
            "Leucocitos .........: 6.500 /mm3     4.000 a 10.000",
            "Linfocitos .........: 30 %  1.950 /mm3   900 a 2.900",
            "Plaquetas ..........: 250.000 /mm3   150.000 a 450.000",
            "Glicose ............: 92 mg/dL       70 a 99",
            "Vitamina D 25-OH ...: 32,1 ng/mL     30 a 100",
        )
    )
    assert resposta.status_code == 200
    assert resposta.json()["patientId"] == "510004"
    assert resposta.json()["semTexto"] is False
    assert valores(resposta) == {
        "Hemoglobina": "13.5",
        "Hematócrito": "41",
        "Leucócitos": "6500",
        "Plaquetas": "250000",
        "Glicose": "92",
        "Vitamina D": "32.1",
        "Linfócitos Absolutos": "1950",
    }


def test_laudo_em_tabela_junta_nome_e_valor_da_mesma_linha():
    resposta = enviar(
        pdf_em_tabela(
            [
                ("Exame", "Resultado", "Unidade", "Referencia"),
                ("Creatinina", "0,95", "mg/dL", "0,70 a 1,30"),
                ("Ureia", "32", "mg/dL", "15 a 45"),
                ("Potassio", "4,3", "mEq/L", "3,5 a 5,1"),
                ("TSH", "2,10", "uUI/mL", "0,40 a 4,00"),
            ]
        )
    )
    assert valores(resposta) == {"Creatinina": "0.95", "Ureia": "32", "Potássio": "4.3", "TSH": "2.1"}


def test_tabela_so_com_referencia_nao_inventa_resultado():
    resposta = enviar(
        pdf_em_tabela(
            [("Glicose", "70 a 99", "mg/dL"), ("Sodio", "135 a 145", "mEq/L")],
            colunas=(50, 250, 330),
        )
    )
    assert valores(resposta) == {}


def test_recusa_arquivo_que_nao_e_pdf():
    resposta = enviar(b"<html>oi</html>")
    assert resposta.status_code == 415


def test_recusa_pdf_grande_demais():
    resposta = enviar(b"%PDF-1.7\n" + b"0" * (index.TAMANHO_MAXIMO + 1))
    assert resposta.status_code == 413


def test_pdf_corrompido_nao_vaza_erro_interno():
    resposta = enviar(b"%PDF-1.7\nisso nao e um pdf de verdade")
    assert resposta.status_code == 422
    assert resposta.json() == {"detail": "Não foi possível ler este PDF."}


def test_pdf_sem_texto_avisa():
    documento = fitz.open()
    documento.new_page()
    resposta = enviar(documento.tobytes())
    assert resposta.status_code == 200
    assert resposta.json() == {"dadosClinicos": [], "patientId": None, "semTexto": True}


def test_credenciais_pacs_continuam_sendo_lidas():
    resposta = enviar(pdf_de_texto("Acesse https://pacs.exemplo.com/viewer", "Usuario: joao123", "Senha: abc@123"))
    (pacs,) = resposta.json()["dadosClinicos"]
    assert pacs["tipo"] == "pacs"
    assert (pacs["usuario"], pacs["url"]) == ("joao123", "https://pacs.exemplo.com/viewer")


@pytest.mark.parametrize("rota", ["/api/process-pdf", "/api/parse-pdf"])
def test_as_duas_rotas_existem(rota):
    resposta = cliente.post(rota, files={"file": ("a.pdf", pdf_de_texto("Ureia 30 mg/dL"), "application/pdf")})
    assert resposta.status_code == 200


def test_cors_fechado_por_padrao():
    resposta = cliente.options(
        "/api/process-pdf",
        headers={"Origin": "https://site-qualquer.com", "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in resposta.headers
