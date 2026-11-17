-- MedCloud - Segurança do banco, FASE 1
-- Objetivo: só o laboratório logado consegue enviar exames e laudos.
--
-- ATENÇÃO: proposta ainda NÃO aplicada e NÃO testada no banco real.
-- Leia docs/SEGURANCA-BANCO.md antes. Rode no SQL Editor do Supabase.
-- Esta fase NÃO muda a leitura, então o app do paciente continua funcionando.

-- 1) Veja as regras que existem hoje (anote os nomes):
--    select policyname, cmd, roles from pg_policies where tablename = 'exames';
--    select policyname, cmd, roles from pg_policies where schemaname = 'storage' and tablename = 'objects';

-- 2) Apague as regras que deixam QUALQUER PESSOA (anon) inserir.
--    Troque os nomes abaixo pelos que apareceram no passo 1.
-- drop policy "NOME_DA_REGRA_DE_INSERT_ANON" on public.exames;
-- drop policy "NOME_DA_REGRA_DE_UPLOAD_ANON" on storage.objects;

-- 3) Garanta que a proteção por linha está ligada.
alter table public.exames enable row level security;

-- 4) Só usuário autenticado (laboratório) insere exame.
create policy "laboratorio insere exames"
  on public.exames
  for insert
  to authenticated
  with check (true);

-- 5) Só usuário autenticado envia PDF para o bucket de laudos.
create policy "laboratorio envia laudos"
  on storage.objects
  for insert
  to authenticated
  with check (bucket_id = 'laudos');

-- 6) Limite de tamanho e tipo de arquivo direto no bucket (10 MB, só PDF).
update storage.buckets
   set file_size_limit = 10485760,
       allowed_mime_types = array['application/pdf']
 where id = 'laudos';
