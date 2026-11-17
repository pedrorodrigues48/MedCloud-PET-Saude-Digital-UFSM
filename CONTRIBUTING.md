# Como desenvolver no MedCloud

Regras curtas para todo mundo trabalhar do mesmo jeito.

## 1. Fluxo de trabalho

1. Toda tarefa começa como uma **issue** (bug ou funcionalidade).
2. Crie uma branch a partir da `main` com o número da issue:
   - `fix/12-leucocitos-mil-vezes`
   - `feat/20-qrcode-medico`
   - `chore/5-remover-codigo-duplicado`
3. Faça commits pequenos, em português, começando com o tipo:
   - `fix: lê ponto de milhar em leucócitos`
   - `feat: gera QR code do portal`
   - `docs:`, `test:`, `chore:`, `refactor:`
4. Abra um **Pull Request** para a `main` e preencha o modelo.
5. O PR só entra quando o **CI estiver verde** e alguém revisar.
6. Nunca commitar direto na `main`.

## 2. Segurança (obrigatório)

- **Nunca** colocar chave secreta (`service_role`, `sb_secret_...`), senha ou token no código. Use variáveis de ambiente na Vercel.
- A chave pública do Supabase (`sb_publishable_...`) pode ficar no front, **desde que o RLS esteja certo**.
- **Nunca** subir laudo real. Para testes, use PDFs anonimizados em `tests/laudos/`.
- Dados de saúde são dados sensíveis pela LGPD: nada de link público para laudo.

## 3. Rodando local

```
pip install -r requirements-dev.txt
python scripts/dev.py
```

Abra http://localhost:8000.

Antes de abrir o PR:

```
ruff check .
pytest
```

Mudou a leitura do PDF? Adicione um teste em `tests/test_extrator.py` com a linha do laudo que deu problema.

## 4. Prioridade

Problemas de segurança e de valores errados no exame vêm antes de funcionalidades novas.
A lista completa está em [docs/AUDITORIA.md](docs/AUDITORIA.md).
