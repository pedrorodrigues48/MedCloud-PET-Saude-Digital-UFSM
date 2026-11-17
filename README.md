# MedCloud

Projeto do PET Saúde Digital (UFSM). O laboratório envia o laudo em PDF pelo portal, o sistema lê os
valores dos exames e o paciente recebe tudo no aplicativo.

## O que tem aqui

| Pasta | O que é |
| --- | --- |
| `portal-laboratorio/` | Portal web do laboratório (HTML, CSS e JavaScript puros) |
| `portal-laboratorio/api/` | API em Python (FastAPI) que lê o PDF. Roda na Vercel |
| `tests/` | Testes automáticos da leitura e da API |
| `supabase/` | Regras do banco prontas para aplicar |
| `docs/` | Auditoria, segurança e próximos passos |

O aplicativo do paciente (React Native) ainda não está neste repositório.

## Rodando no seu computador

```
pip install -r requirements-dev.txt
python scripts/dev.py
```

Abra http://localhost:8000. O portal e a leitura de PDF funcionam juntos, como na Vercel.

## Testes

```
pytest
ruff check .
```

Os PDFs de teste são gerados na hora pelos próprios testes. **Nunca** suba laudo real.

## Como a leitura do PDF funciona

A leitura não usa inteligência artificial: são regras fixas em
[`portal-laboratorio/api/_extrator.py`](portal-laboratorio/api/_extrator.py). A regra principal é
**nunca inventar um valor**. Um número só é aceito se estiver logo depois do nome do exame, e nunca
se for data, valor de referência ou parte do nome (como o 25 de "Vitamina D 25-OH"). Na dúvida, o
exame fica de fora.

Antes de enviar, o portal mostra cada valor ao lado da linha original do laudo para o laboratório
conferir, corrigir ou desmarcar.

## Documentos

- [CONTRIBUTING.md](CONTRIBUTING.md): como desenvolver
- [docs/AUDITORIA.md](docs/AUDITORIA.md): problemas encontrados e o que já foi resolvido
- [docs/SEGURANCA-BANCO.md](docs/SEGURANCA-BANCO.md): plano de segurança do banco
- [BUGS.md](BUGS.md): primeiros testes manuais (histórico)
