# Auditoria do MedCloud (16/11/2026)

Revisão de todo o código do repositório (portal do laboratório + API de leitura de PDF).
O app do paciente (React Native) **não está no repositório** e não foi revisado ainda.

Ferramentas usadas: leitura manual, `ruff` (lint + regras de segurança), `bandit`, `pip-audit`
(nenhuma vulnerabilidade conhecida nas dependências) e busca de segredos no histórico
(nenhuma chave secreta encontrada; só a chave pública do Supabase).

Prioridade: **P0** = corrigir antes de qualquer coisa, **P1** = logo depois, **P2** = quando der.

## Segurança

| ID | Prioridade | Problema | Onde |
| --- | --- | --- | --- |
| S1 | P0 | **Qualquer pessoa pode ler os exames de qualquer paciente.** O app lê a tabela `exames` com a chave pública filtrando só pelo ID do paciente, que tem 6 dígitos (dá para testar todos). Pelo relatório, o RLS libera `SELECT` para a chave pública. | Supabase (RLS) + app |
| S2 | P0 | **Qualquer pessoa pode enviar exames falsos.** O `INSERT` e o upload usam a chave pública, que está no `app.js`. O login não protege nada. | `app.js`, Supabase |
| S3 | P0 | **Login falso.** Usuário/senha `admin`/`1234` no `app.js` (em base64), e a mensagem de erro mostra a senha: "Dica: admin / 1234". | `app.js` `fazerLogin` |
| S4 | P0 | **Laudos com link público.** `getPublicUrl` no bucket `laudos`: quem tiver o link abre o PDF, para sempre. | `app.js` |
| S5 | P0 | **Senha do PACS em texto puro** no banco e enviada ao app. | `api/index.py`, `app.js` |
| S6 | P1 | API de leitura sem autenticação, sem limite de tamanho do PDF e sem limite de requisições (dá para derrubar). | `api/index.py` |
| S7 | P1 | CORS liberado para qualquer site (`*`) junto com `allow_credentials`. | `api/index.py` |
| S8 | P1 | Scripts de CDN sem versão fixa e sem verificação (`@phosphor-icons/web` sem versão, `supabase-js@2`). Se o CDN for comprometido, roda código no portal. | `index.html` |
| S9 | P1 | Sem cabeçalhos de segurança (CSP, X-Frame-Options etc.) na Vercel. | `vercel.json` |
| S10 | P1 | Arquivo enviado não é validado no servidor (só `accept=".pdf"` no navegador). | `app.js`, Supabase Storage |
| S11 | P2 | Erros internos devolvidos ao usuário (`{"error": str(e)}`) e status 200 em caso de erro. | `api/index.py` |
| S12 | P2 | APK baixado do repositório de outra pessoa (`tiaginhoeumesmo-oss`). Se mudar, os usuários baixam outra coisa. | `index.html` |
| S13 | P2 | LGPD: dados de saúde sem termo de consentimento, sem registro de quem acessou e sem prazo de guarda. | Projeto todo |

## Valores errados no exame ("inventa número")

| ID | Prioridade | Problema | Exemplo |
| --- | --- | --- | --- |
| V1 | P0 | Pega o número do valor de referência | `Glicose: 70 a 99` vira 70 |
| V2 | P0 | Pega a data | `Glicose 15/11/2026 92` vira 15 |
| V3 | P0 | Pega número que faz parte do nome | `Vitamina D 25-OH 32,1` vira 25 |
| V4 | P0 | Ponto de milhar lido como decimal | `Leucócitos 4.500` vira 4,5 |
| V5 | P0 | Linfócitos/monócitos/eosinófilos/basófilos pegam o maior número da linha (a referência) | `30 % 1350 /mm³ 900 a 2900` vira 2900 |
| V6 | P1 | Pontilhado vira valor e quebra (`NaN`) | `Fosfatase .... 80` vira `...` |
| V7 | P1 | Siglas curtas sem limite de palavra (FA, AST, ALT, LH, TAP, PCR) | `RT-PCR 2` vira Proteína C Reativa 2 |
| V8 | P1 | Valores digitados à mão são descartados sem aviso quando o ID do paciente fica vazio e a leitura automática acha algo | `app.js` `sendFile` |
| V9 | P1 | Nenhuma tela de conferência: o que foi lido vai direto para o paciente | `app.js` |
| V10 | P2 | Ferro Sérico nunca é lido (falta `\s*` no regex) | `Ferro Sérico 80` |
| V11 | P2 | ID do paciente pode pegar outro número após "Registro" ou "Paciente" | `api/index.py` |

## Desenvolvimento

| ID | Prioridade | Problema | Onde |
| --- | --- | --- | --- |
| D1 | P0 | App do paciente fora do repositório (só um `.rar` de 1,87 GB no Drive) | Drive |
| D2 | P0 | Nenhum teste automático, nem laudos de exemplo | repo |
| D3 | P1 | Código duplicado/morto: `medcloud-python-backend/` e `portal-laboratorio/backend/` são versões antigas da API | repo |
| D4 | P1 | Esquema do banco (tabelas, RLS, buckets) não está versionado; ninguém sabe como recriar | Supabase |
| D5 | P1 | Endereço e chave do Supabase fixos no código, sem separar desenvolvimento e produção | `app.js` |
| D6 | P1 | Leitura automática não funciona local (o portal chama `/api/...` no mesmo endereço) | `app.js`, README |
| D7 | P2 | Dependências Python sem versão fixa (`fastapi`, `PyMuPDF`) | `requirements.txt` |
| D8 | P2 | Muito estilo inline no HTML e funções globais em `window` | `index.html`, `app.js` |
| D9 | P2 | Relatório cita "IA na nuvem" e correção pelo nome do arquivo, mas o código só tem regex. Documentação desatualizada. | README, relatório |

## Ordem sugerida

1. **D1, D2**: trazer o app do paciente pro repo e criar laudos de teste.
2. **S1 a S5**: segurança dos dados (login real com Supabase Auth, RLS por usuário, links assinados com validade curta, tirar senha do PACS).
3. **V1 a V9**: leitura correta + tela de conferência.
4. **D3 a D6**: limpeza e ambiente local.
5. Funcionalidades novas (QR code do site, QR code do médico).
