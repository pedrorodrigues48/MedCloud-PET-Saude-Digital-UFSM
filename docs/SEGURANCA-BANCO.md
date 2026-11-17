# Segurança do banco (Supabase)

Itens S1 a S5 da [auditoria](AUDITORIA.md). **Nada aqui foi aplicado ainda**: precisa de acesso
ao painel do Supabase, e parte depende do código do app do paciente.

## Como é hoje (pelo código do portal)

- Tabela `exames`: `paciente_id`, `url_laudo`, `categoria`, `nome_arquivo`, `dados_estruturados`.
- Bucket `laudos`, público.
- Portal e app usam a mesma chave pública. O "login" do portal é só visual.

## Fase 1: só o laboratório envia (não quebra o app)

1. No Supabase, em **Authentication > Users**, criar um usuário para cada pessoa do laboratório.
2. Rodar [`supabase/fase1_so_laboratorio_envia.sql`](../supabase/fase1_so_laboratorio_envia.sql).
3. No portal, trocar o login falso por `supabase.auth.signInWithPassword` (próximo PR, depois dos passos 1 e 2).

Resultado: resolve S2 e S3. Ninguém de fora consegue mais enviar exame falso.

## Fase 2: paciente só vê o que é dele (mexe no app)

1. Trocar o ID de 6 dígitos por um código secreto longo, gerado no app e guardado no celular.
2. Fechar o `SELECT` público. O app passa a ler por uma função do banco que exige o código secreto.
3. Bucket `laudos` privado. O app pede um link assinado com validade curta para abrir o PDF.
4. Parar de gravar usuário e senha do PACS em `dados_estruturados`.

Resultado: resolve S1, S4 e S5. Só dá para fazer junto com uma nova versão do app.

## Fase 3: QR code do médico

Com a fase 2 pronta, o app gera um QR com um código temporário (ex.: 30 minutos).
O médico abre uma página só de leitura, e cada acesso fica registrado (LGPD).
