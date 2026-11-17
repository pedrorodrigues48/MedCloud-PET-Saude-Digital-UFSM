"""Leitura determinística de laudos laboratoriais em PDF.

Regra de ouro: **nunca inventar um valor**. Um número só é aceito quando
está na mesma linha do nome do exame (ou na linha seguinte, sozinho),
logo depois do nome, e não faz parte de data, valor de referência ou do
próprio nome do exame. Na dúvida, o exame fica de fora e o laboratório
preenche na tela de conferência.

Cada resultado devolve também a linha original do PDF (`linha`) e um aviso
(`suspeito`) quando o valor está fora de qualquer faixa fisiológica possível.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Catálogo de exames
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Exame:
    nome: str
    padrao: str  # regex sobre o texto sem acento e em minúsculas
    unidade: str
    minimo: float  # limites fisiológicos amplos, só para marcar "suspeito"
    maximo: float
    absoluto: bool = False  # diferencial do hemograma: queremos o valor em /mm³


EXAMES: tuple[Exame, ...] = (
    # Hemograma
    Exame("Hemoglobina", r"(?<!de )hemoglobina(?!\s+(?:glicada|glicosilada|corpuscular|a1c))", "g/dL", 2, 25),
    Exame("Hematócrito", r"hematocrito", "%", 5, 75),
    Exame("Leucócitos", r"leucocitos(?:\s+totais)?|globulos\s+brancos", "/mm³", 100, 500_000),
    Exame("Plaquetas", r"plaquetas", "/mm³", 1_000, 2_000_000),
    # Bioquímica
    Exame("Glicose", r"glic(?:emia|ose)(?!\s+(?:media|pos|urinaria))(?:\s+(?:de|em)\s+jejum)?", "mg/dL", 10, 1500),
    Exame("Colesterol Total", r"colesterol\s+total", "mg/dL", 30, 1000),
    Exame("Colesterol HDL", r"colesterol\s+hdl|hdl\s*-?\s*colesterol", "mg/dL", 5, 200),
    Exame("Colesterol LDL", r"colesterol\s+ldl|ldl\s*-?\s*colesterol", "mg/dL", 5, 600),
    Exame("Colesterol VLDL", r"colesterol\s+vldl|vldl\s*-?\s*colesterol", "mg/dL", 1, 300),
    Exame("Triglicerídeos", r"triglicerid(?:eos|es|ios)", "mg/dL", 10, 10_000),
    Exame("Ureia", r"ureia", "mg/dL", 2, 500),
    Exame("Creatinina", r"(?<!de )creatinina(?!\s+urinaria)", "mg/dL", 0.1, 30),
    Exame("eTFG", r"etfg|tfge|taxa\s+de\s+filtracao\s+glomerular(?:\s+estimada)?", "mL/min", 1, 200),
    Exame("Sódio", r"sodio", "mEq/L", 90, 200),
    Exame("Potássio", r"potassio", "mEq/L", 1, 10),
    Exame("Cálcio Total", r"calcio(?:\s+total)?(?!\s+(?:ionico|ionizado|urinario))", "mg/dL", 3, 20),
    Exame("Magnésio", r"magnesio", "mg/dL", 0.3, 10),
    Exame("Cloreto", r"cloretos?|cloro", "mEq/L", 50, 150),
    # Fígado, coagulação, inflamação, tireoide
    Exame("TGO / AST", r"tgo|ast|aspartato\s+aminotransferase|transaminase\s+oxalacetica", "U/L", 1, 20_000),
    Exame("TGP / ALT", r"tgp|alt|alanina\s+aminotransferase|transaminase\s+piruvica", "U/L", 1, 20_000),
    Exame("Gama-GT", r"gama[\s-]*gt|ggt|gama[\s-]*glutamil\s*transferase", "U/L", 1, 10_000),
    Exame("Fosfatase Alcalina", r"fosfatase\s+alcalina", "U/L", 5, 5000),
    Exame("Bilirrubina Total", r"bilirrubina\s+total", "mg/dL", 0.05, 60),
    Exame("Bilirrubina Direta", r"bilirrubina\s+direta", "mg/dL", 0, 40),
    Exame("Bilirrubina Indireta", r"bilirrubina\s+indireta", "mg/dL", 0, 40),
    Exame("Hemoglobina Glicada", r"hemoglobina\s+glic(?:ada|osilada)|hba1c|a1c", "%", 3, 20),
    Exame("Ácido Úrico", r"acido\s+urico", "mg/dL", 0.5, 25),
    Exame("Tempo de Protrombina", r"tempo\s+de\s+protrombina|tap", "seg", 5, 150),
    Exame("INR", r"inr|rni", "", 0.5, 20),
    Exame("TTPA", r"ttpa|tempo\s+de\s+tromboplastina(?:\s+parcial(?:\s+ativada)?)?", "seg", 10, 250),
    Exame("Proteína C Reativa", r"proteina\s+c\s+reativa|pcr", "mg/L", 0, 700),
    Exame("Velocidade de Hemossedimentação", r"velocidade\s+de\s+hemossedimentacao|vhs", "mm/h", 0, 200),
    Exame("TSH", r"tsh|hormonio\s+tireoestimulante", "µUI/mL", 0.001, 500),
    Exame("T4 Livre", r"t4\s+livre|tiroxina\s+livre", "ng/dL", 0.05, 15),
    Exame("Proteínas Totais", r"proteinas\s+totais", "g/dL", 2, 15),
    Exame("Albumina", r"albumina", "g/dL", 0.5, 8),
    Exame("Globulinas", r"globulinas", "g/dL", 0.5, 10),
    # Nutricional e hormonal
    Exame("Ferro Sérico", r"(?<!do )(?<!de )ferro(?:\s+serico)?", "µg/dL", 5, 1000),
    Exame("Ferritina", r"ferritina", "ng/mL", 1, 100_000),
    Exame("TIBC", r"tibc|capacidade\s+total\s+de\s+ligacao\s+(?:do|de)\s+ferro", "µg/dL", 50, 1000),
    Exame(
        "Vitamina D",
        r"25[\s-]*hidroxi[\s-]*vitamina\s+d|(?:25[\s-]*oh[\s-]*)?vitamina\s+d3?(?:\s*-?\s*25[\s-]*(?:oh|hidroxi[a-z]*))?",
        "ng/mL",
        2,
        300,
    ),
    Exame("Vitamina B12", r"vitamina\s+b\s*12", "pg/mL", 30, 10_000),
    Exame("FSH", r"fsh|hormonio\s+foliculo\s*-?\s*estimulante", "mUI/mL", 0.01, 300),
    Exame("LH", r"lh|hormonio\s+luteinizante", "mUI/mL", 0.01, 300),
    Exame("Prolactina", r"prolactina", "ng/mL", 0.1, 5000),
    Exame("Estradiol", r"estradiol", "pg/mL", 1, 50_000),
    Exame("Testosterona Total", r"testosterona(?:\s+total)?(?!\s+livre)", "ng/dL", 1, 3000),
    Exame("Testosterona Livre", r"testosterona\s+livre", "ng/dL", 0.01, 100),
    Exame("Progesterona", r"progesterona", "ng/mL", 0.01, 500),
    Exame("Cortisol Basal", r"cortisol(?:\s+(?:basal|serico))?", "µg/dL", 0.1, 150),
    # Marcadores
    Exame("Troponina I ou T", r"troponina(?:\s+[it])?", "ng/mL", 0, 100_000),
    Exame("CK-MB", r"ck[\s-]*mb", "U/L", 0, 5000),
    Exame("BNP", r"nt[\s-]*probnp|bnp", "pg/mL", 1, 100_000),
    Exame("D-Dímero", r"d[\s-]*dimero", "ng/mL", 1, 100_000),
    Exame("PSA Livre", r"psa\s+livre", "ng/mL", 0, 500),
    Exame("PSA Total", r"psa(?:\s+total)?(?!\s+livre)", "ng/mL", 0, 10_000),
    Exame("CEA", r"cea|antigeno\s+carcinoembrionario", "ng/mL", 0, 100_000),
    Exame("CA 125", r"ca[\s-]*125", "U/mL", 0, 100_000),
    Exame("CA 19-9", r"ca[\s-]*19[\s.-]*9", "U/mL", 0, 100_000),
    Exame("Alfa-fetoproteína", r"alfa[\s-]*fetoproteina|afp", "ng/mL", 0, 100_000),
    # Diferencial do hemograma (valor absoluto)
    Exame("Linfócitos Absolutos", r"linfocitos(?!\s+atipicos)", "/mm³", 0, 400_000, absoluto=True),
    Exame("Monócitos Absolutos", r"monocitos", "/mm³", 0, 100_000, absoluto=True),
    Exame("Eosinófilos Absolutos", r"eosinofilos", "/mm³", 0, 100_000, absoluto=True),
    Exame("Basófilos Absolutos", r"basofilos", "/mm³", 0, 50_000, absoluto=True),
)

# Nome do exame precisa ser uma palavra inteira ("AST" não casa em "CONTRASTE",
# "PCR" não casa em "RT-PCR").
_COMPILADOS = tuple(
    (exame, re.compile(r"(?<![a-z0-9-])(?:" + exame.padrao + r")(?![a-z0-9])")) for exame in EXAMES
)

# ---------------------------------------------------------------------------
# Peças de texto
# ---------------------------------------------------------------------------

_NUMERO = re.compile(r"(?<![\w/,.])(\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?)(?![\d/ªº°]|[.,]\d)")
_DATA_HORA = re.compile(
    r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}/\d{1,2}|\d{1,2}:\d{2}(?::\d{2})?|\d{1,2}h\d{2}"
)
_PONTILHADO = re.compile(r"\.{2,}|…")
_PARENTESES = re.compile(r"\([^)]*\)|\[[^\]]*\]")
_FAIXA = re.compile(r"(\d[\d.,]*)\s*(?:a|ate|-|–|—|~)\s*(\d[\d.,]*\d|\d)")
_REFERENCIA = re.compile(
    r"valor(?:es)?\s+de\s+ref|referencia|\bref\b|\bv\.?\s?r\.?(?=[\s:])|\bnormal|desejavel|otimo|"
    r"limitrofe|\bate\b|inferior|superior|\bmenor\b|\bmaior\b|\bacima\b|\babaixo\b|"
    r"adultos?|homens|mulheres|criancas|masculino|feminino"
)
_MIL = re.compile(r"^\s*(?:mil\b|x?\s*10\s*\^?\s*[3³]|x\s*10e3|k\s*/)")
_PORCENTO = re.compile(r"^\s*%")
_UNIDADE_ABSOLUTA = re.compile(r"^\s*(?:/\s*(?:mm|µl|ul|mcl)|mil\b|x?\s*10)")
_MILHAR = re.compile(r"^\d{1,3}(?:\.\d{3})+$")

# Palavras que podem aparecer entre o nome do exame e o valor.
_ENCHIMENTO = frozenset(
    "em de do da jejum soro plasma sangue serico serica total totais resultado valor basal dosagem ultrassensivel".split()
)
_PONTUACAO = re.compile(r"[.:;,=_|*\-–—<>·…]+")

_ID_PACIENTE = re.compile(
    r"(?:(?:id|c[oó]d(?:igo)?\.?)\s*(?:d[oa]\s*)?paciente|prontu[aá]rio)\s*(?:n[ºo°.]*)?\s*[:\-]?\s*(\d{5,8})(?!\d)",
    re.IGNORECASE,
)


def sem_acento(texto: str) -> str:
    """Minúsculas e sem acento, mantendo o mesmo número de caracteres."""
    saida = []
    for letra in unicodedata.normalize("NFC", texto):
        base = unicodedata.normalize("NFD", letra)[0]
        saida.append(base.lower() if len(base.lower()) == 1 else base)
    return "".join(saida)


def _apagar(padrao: re.Pattern[str], texto: str) -> str:
    """Troca o que casar por espaços, sem mudar as posições do resto."""
    return padrao.sub(lambda m: " " * len(m.group(0)), texto)


def _para_numero(texto: str, exame: Exame) -> float:
    """Converte "4.500", "13,5" ou "1.234,5" respeitando o padrão brasileiro."""
    if "," in texto:
        return float(texto.replace(".", "").replace(",", "."))
    if _MILHAR.match(texto) and not texto.startswith("0."):
        milhar = float(texto.replace(".", ""))
        decimal = float(texto)
        # "4.500" é quatro mil e quinhentos; só vira 4,5 se for o único que faz sentido.
        if not (exame.minimo <= milhar <= exame.maximo) and exame.minimo <= decimal <= exame.maximo:
            return decimal
        return milhar
    return float(texto)


def _formatar(valor: float) -> str:
    return str(int(valor)) if valor == int(valor) else repr(round(valor, 4))


def _ler_valor(resto: str, exame: Exame) -> dict | None:
    """Procura o resultado no texto que vem logo depois do nome do exame."""
    limpo = _apagar(_PONTILHADO, _apagar(_DATA_HORA, _apagar(_PARENTESES, resto)))

    # Tudo a partir do valor de referência é ignorado.
    corte = len(limpo)
    faixa = _FAIXA.search(limpo)
    if faixa:
        corte = faixa.start()
    palavra_ref = _REFERENCIA.search(limpo)
    if palavra_ref:
        corte = min(corte, palavra_ref.start())
    trecho = limpo[:corte]

    numeros = list(_NUMERO.finditer(trecho))
    if not numeros:
        return None

    # Entre o nome e o primeiro número só pode haver pontuação e palavras neutras.
    antes = trecho[: numeros[0].start()]
    if any(p not in _ENCHIMENTO for p in _PONTUACAO.sub(" ", antes).split()):
        return None
    operador = antes.rstrip()[-1:] if antes.rstrip()[-1:] in ("<", ">") else ""

    escolhido = numeros[0]
    if exame.absoluto:
        sem_porcento = [n for n in numeros if not _PORCENTO.match(limpo[n.end() :])]
        if len(numeros) >= 2 and sem_porcento:
            com_unidade = [n for n in sem_porcento if _UNIDADE_ABSOLUTA.match(limpo[n.end() :])]
            candidatos = com_unidade or sem_porcento
            escolhido = max(candidatos[:2], key=lambda n: _para_numero(n.group(1), exame))
        elif len(numeros) == 1 and sem_porcento:
            # Um número só: aceito apenas se claramente for contagem absoluta.
            unico = numeros[0]
            if not (_UNIDADE_ABSOLUTA.match(limpo[unico.end() :]) or _para_numero(unico.group(1), exame) > 100):
                return None
        else:
            return None  # só porcentagem na linha

    valor = _para_numero(escolhido.group(1), exame)
    if _MIL.match(limpo[escolhido.end() :]):
        valor *= 1000

    referencia = ""
    if faixa and faixa.start() >= escolhido.end():
        # Mesmo formato dos campos manuais do portal: "3.5 - 5.1", "4000 - 11000".
        try:
            referencia = " - ".join(_formatar(_para_numero(faixa.group(n), exame)) for n in (1, 2))
        except ValueError:
            referencia = ""

    return {
        "valor": _formatar(valor),
        "ref": referencia,
        "operador": operador,
        "suspeito": not (exame.minimo <= valor <= exame.maximo),
    }


def extrair_exames(linhas: list[str]) -> list[dict]:
    """Recebe as linhas do laudo e devolve os exames encontrados."""
    normalizadas = [sem_acento(linha) for linha in linhas]
    resultados: list[dict] = []

    for exame, padrao in _COMPILADOS:
        achado = None
        for i, linha in enumerate(normalizadas):
            for nome in padrao.finditer(linha):
                resto = linha[nome.end() :]
                achado = _ler_valor(resto, exame)
                origem = linhas[i]
                # Nome sozinho na linha e resultado na linha de baixo.
                if achado is None and i + 1 < len(linhas) and not re.search(r"\d", _apagar(_PARENTESES, resto)):
                    if not any(p not in _ENCHIMENTO for p in _PONTUACAO.sub(" ", _apagar(_PARENTESES, resto)).split()):
                        achado = _ler_valor(normalizadas[i + 1], exame)
                        origem = f"{linhas[i]} / {linhas[i + 1]}"
                if achado:
                    break
            if achado:
                resultados.append(
                    {
                        "nome": exame.nome,
                        "valor": achado["valor"],
                        "uni": exame.unidade,
                        "tipo": "lab",
                        "ref": achado["ref"],
                        "operador": achado["operador"],
                        "suspeito": achado["suspeito"],
                        "linha": origem.strip()[:200],
                    }
                )
                break

    return resultados


def extrair_id_paciente(linhas: list[str]) -> str | None:
    """Só aceita o número quando vem com um rótulo claro de paciente."""
    for linha in linhas:
        achado = _ID_PACIENTE.search(linha)
        if achado:
            return achado.group(1)
    return None


def linhas_do_pdf(documento) -> list[str]:
    """Reconstrói as linhas visuais do PDF (nome e valor na mesma altura)."""
    linhas: list[str] = []
    for pagina in documento:
        palavras = sorted(pagina.get_text("words"), key=lambda p: ((p[1] + p[3]) / 2, p[0]))
        atual: list = []
        centro = None
        for palavra in palavras:
            meio = (palavra[1] + palavra[3]) / 2
            if centro is not None and abs(meio - centro) > 3:
                linhas.append(" ".join(p[4] for p in sorted(atual, key=lambda p: p[0])))
                atual = []
            atual.append(palavra)
            centro = meio if len(atual) == 1 else centro
        if atual:
            linhas.append(" ".join(p[4] for p in sorted(atual, key=lambda p: p[0])))
    return linhas
