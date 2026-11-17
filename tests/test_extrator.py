"""Testes da leitura de laudos: o sistema nunca pode inventar um valor."""

import pytest

from _extrator import extrair_exames, extrair_id_paciente


def ler(*linhas: str) -> dict[str, str]:
    return {item["nome"]: item["valor"] for item in extrair_exames(list(linhas))}


# --- Casos que já deram errado em produção (docs/AUDITORIA.md, V1 a V11) ---


def test_v1_nao_pega_valor_de_referencia():
    assert ler("Glicose: 70 a 99 mg/dL") == {}


def test_v2_nao_pega_data():
    assert ler("Glicose 15/11/2026 92 mg/dL") == {"Glicose": "92"}
    assert ler("Glicose 15/11/2026") == {}


def test_v3_numero_que_faz_parte_do_nome():
    assert ler("VITAMINA D 25-OH ........ 32,1 ng/mL") == {"Vitamina D": "32.1"}
    assert ler("25-Hidroxivitamina D: 28,4 ng/mL") == {"Vitamina D": "28.4"}
    assert ler("Vitamina B12 450 pg/mL") == {"Vitamina B12": "450"}
    assert ler("CA 19-9 12,3 U/mL") == {"CA 19-9": "12.3"}
    assert ler("CA 125: 18 U/mL") == {"CA 125": "18"}
    assert ler("T4 Livre 1,2 ng/dL") == {"T4 Livre": "1.2"}


def test_v4_ponto_de_milhar():
    assert ler("Leucócitos 4.500 /mm³") == {"Leucócitos": "4500"}
    assert ler("Plaquetas 250.000 /mm³ 150.000 a 450.000") == {"Plaquetas": "250000"}
    assert ler("Plaquetas 250 mil/mm³") == {"Plaquetas": "250000"}
    assert ler("Leucócitos 6,5 mil/mm³") == {"Leucócitos": "6500"}


def test_v5_diferencial_pega_absoluto_e_nao_a_referencia():
    assert ler("Linfócitos 30 % 1350 /mm³ 900 a 2900") == {"Linfócitos Absolutos": "1350"}
    assert ler("Monócitos 8,0 360 80 a 1000") == {"Monócitos Absolutos": "360"}
    assert ler("Eosinófilos 2 % 90 /mm³") == {"Eosinófilos Absolutos": "90"}
    assert ler("Basófilos 0,5 % 22 /mm³ 0 a 200") == {"Basófilos Absolutos": "22"}


def test_v5_diferencial_so_com_porcentagem_fica_de_fora():
    assert ler("Linfócitos 30 %") == {}
    assert ler("Linfócitos 30") == {}


def test_v6_pontilhado_nao_vira_valor():
    assert ler("Fosfatase Alcalina ......: 80 U/L") == {"Fosfatase Alcalina": "80"}
    assert ler("Hemoglobina......13,5 g/dL") == {"Hemoglobina": "13.5"}
    assert ler("Fosfatase Alcalina ......") == {}


@pytest.mark.parametrize(
    "linha",
    [
        "RT-PCR 2 amostras",
        "EXAME COM CONTRASTE 3 fases",
        "ETAPA 2 concluída",
        "Paciente: JOSE FILHO 45 anos",
        "ALTURA 170 cm",
        "FALHA 3",
    ],
)
def test_v7_sigla_curta_nao_casa_dentro_de_outra_palavra(linha):
    assert ler(linha) == {}


def test_v10_ferro_serico():
    assert ler("Ferro Sérico 80 µg/dL") == {"Ferro Sérico": "80"}
    assert ler("Ferritina 120 ng/mL") == {"Ferritina": "120"}
    assert ler("Capacidade total de ligação do ferro 300 µg/dL") == {"TIBC": "300"}


def test_v11_id_do_paciente_exige_rotulo():
    assert extrair_id_paciente(["ID do Paciente: 510004"]) == "510004"
    assert extrair_id_paciente(["Código do Paciente 123456"]) == "123456"
    assert extrair_id_paciente(["Prontuário nº 7654321"]) == "7654321"
    assert extrair_id_paciente(["Paciente: MARIA 12345678900", "Registro ANVISA 123456"]) is None
    assert extrair_id_paciente(["ID do Paciente: 123456789012"]) is None


# --- Exames parecidos não podem se confundir ---


def test_hemoglobina_nao_confunde_com_glicada_nem_hcm():
    resultado = ler(
        "Hemoglobina Corpuscular Média 29,5 pg",
        "Conc. de Hemoglobina Corpuscular Média 33,1 g/dL",
        "Hemoglobina Glicada (HbA1c) 5,4 %",
        "Hemoglobina 14,2 g/dL 13,5 a 17,5",
    )
    assert resultado == {"Hemoglobina": "14.2", "Hemoglobina Glicada": "5.4"}


def test_colesterol_e_fracoes():
    resultado = ler(
        "Colesterol Total 180 mg/dL Desejável: < 190",
        "Colesterol HDL 55 mg/dL",
        "Colesterol não-HDL 125 mg/dL",
        "LDL - Colesterol 100 mg/dL",
        "VLDL - Colesterol 25 mg/dL",
        "Relação Colesterol Total/HDL 3,3",
    )
    assert resultado == {
        "Colesterol Total": "180",
        "Colesterol HDL": "55",
        "Colesterol LDL": "100",
        "Colesterol VLDL": "25",
    }


def test_variantes_que_nao_sao_o_exame():
    assert ler("Glicose média estimada 117 mg/dL") == {}
    assert ler("Sódio urinário 120 mEq/L") == {}
    assert ler("Cálcio iônico 1,20 mmol/L") == {}
    assert ler("Clearance de creatinina 95 mL/min") == {}
    assert ler("Relação Albumina/Globulina 1,5") == {}
    assert ler("PSA Livre/Total 25 %") == {}


def test_psa_e_testosterona():
    resultado = ler("PSA Total 1,20 ng/mL", "PSA Livre 0,30 ng/mL", "Testosterona Total 520", "Testosterona Livre 9,5")
    assert resultado == {
        "PSA Total": "1.2",
        "PSA Livre": "0.3",
        "Testosterona Total": "520",
        "Testosterona Livre": "9.5",
    }


# --- Texto explicativo não é resultado ---


def test_frases_explicativas_sao_ignoradas():
    assert ler("Valores de glicose acima de 126 mg/dL indicam diabetes") == {}
    assert ler("Leucócitos acima de 11.000 sugerem infecção") == {}
    assert ler("Creatinina: valores de referência 0,7 a 1,3") == {}
    assert ler("TSH - 3ª geração") == {}


# --- Formatos de laudo ---


def test_valor_na_linha_de_baixo():
    assert ler("GLICOSE", "Resultado: 92 mg/dL", "Valor de referência: 70 a 99 mg/dL") == {"Glicose": "92"}
    assert ler("GLICOSE", "Valor de referência: 70 a 99 mg/dL") == {}
    assert ler("GLICOSE", "Hematócrito 41 %") == {"Hematócrito": "41"}


def test_referencia_e_linha_original_sao_devolvidas():
    (item,) = extrair_exames(["Potássio (soro) ....: 4,3 mEq/L   3,5 a 5,1"])
    assert item["valor"] == "4.3"
    assert item["ref"] == "3.5 - 5.1"
    assert item["linha"] == "Potássio (soro) ....: 4,3 mEq/L   3,5 a 5,1"
    assert item["suspeito"] is False


def test_referencia_com_milhar():
    (item,) = extrair_exames(["Leucócitos 6.500 /mm³ 4.000 a 10.000"])
    assert item["ref"] == "4000 - 10000"


def test_operador_menor_que():
    (item,) = extrair_exames(["Proteína C Reativa < 0,5 mg/L"])
    assert (item["valor"], item["operador"]) == ("0.5", "<")


def test_valor_impossivel_e_marcado_como_suspeito():
    (item,) = extrair_exames(["Potássio 45 mEq/L"])
    assert item["suspeito"] is True
    (item,) = extrair_exames(["Leucócitos 6,5"])
    assert item["suspeito"] is True


def test_formato_americano_de_decimal():
    assert ler("Creatinina 0.95 mg/dL") == {"Creatinina": "0.95"}
    assert ler("Hemoglobina 13.5 g/dL") == {"Hemoglobina": "13.5"}


def test_laudo_vazio():
    assert extrair_exames([]) == []
    assert extrair_exames(["LAUDO DE ULTRASSONOGRAFIA", "Fígado de dimensões normais."]) == []
