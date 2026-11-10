# Importação do owner TF no Oracle Free

> **Status:** preparação. Nada foi executado no destino. Terceira rodada de consultas feita em 2026-11-10.
> **Última atualização:** 2026-11-10
> **Parte de:** [analise-producao-oci-vm-docker.md](analise-producao-oci-vm-docker.md), §9

Como levar o owner TF do XE 11.2.0.2 para o Oracle Free 26ai, com base no inventário da produção (2026-11-05) e na terceira rodada de consultas (2026-11-10). **Só o TF migra:** os owners `APEXREP` e `DOLOMITI` ficam para trás (decisão de Tiago, 2026-11-10).

**Teste anterior no ATP.** Em 2026-02, o mesmo schema foi importado no ADB `DEVDOLOMITI`, que hoje roda a versão 23.26.4, da mesma família do Free. As anotações ficam em `Infra/OCI/` e confirmam o caminho deste documento: usuário criado antes do import, `EXECUTE` em `DBMS_CRYPTO` e `DBMS_SESSION` e o contexto `CTX` recriado depois. No ADB, o TF compilou com só três objetos inválidos, todos explicados na §7.

---

## 1. Linha de base

Objetos do TF em 2026-11-05. Depois do import, a contagem tem de bater.

| Tipo | Qtd | Tipo | Qtd |
|---|---:|---|---:|
| TABLE | 299 | PACKAGE | 35 |
| INDEX | 376 | PACKAGE BODY | 35, dos quais 2 já inválidos na produção |
| TRIGGER | 268 | VIEW | 19 |
| SEQUENCE | 120 | TYPE | 4 |
| LOB | 40 | PROCEDURE | 3 |
| JOB | 3 | FUNCTION | 2 |

- **Tablespaces:** `TS_TF` com 1.422 MB e `TS_LOG` com 474 MB.
- **Relógio:** o `SYSDATE` da produção marcou 19:49 numa consulta salva às 19:51 de Brasília. O servidor roda no horário local, e o `dbtimezone` (+00:00) não afeta o `SYSDATE`. O destino precisa de `TZ=America/Sao_Paulo`.
- **Picos:** a instância está no ar desde 2025-07-16, então o pico de 80 sessões cobre ~16 meses.

---

## 2. O que fica fora do schema

O próprio banco confirmou: no modo schema, o Data Pump leva só `RLS_CONTEXT`, que são políticas VPD. `CONTEXT` e `DIRECTORY` aparecem apenas no modo full (`database_export_objects`).

| Item | Na produção | No destino |
|---|---|---|
| Aplicação APEX | App 130 "Sistema de Gestão", 293 páginas, workspace `PROD`. Os outros apps são exemplos ou internos do APEX | Exportar do 20.1 e importar no 26.1 com o mesmo ID |
| Contexto | `CTX`, via `TF.TF_PCK_CONTEXTO`, `ACCESSED GLOBALLY` | Recriar (§4) |
| Roles | `DBA`, `CONNECT` e `RESOURCE` | Não replicar o `DBA` (§3) |
| Privilégios de sistema | `CREATE SESSION`, `CREATE VIEW`, `CREATE SYNONYM`, `UNLIMITED TABLESPACE` | Privilégios diretos (§4) |
| Pacotes do SYS | `EXECUTE` em `DBMS_CRYPTO`, `DBMS_SESSION`, `UTL_FILE`, `UTL_HTTP`, `UTL_INADDR`, `UTL_SMTP`, `UTL_TCP` e `UTL_URL` | Reaplicar, menos o `UTL_SMTP` (§3, item 2) |
| Views `V$` | `SELECT` em ~620 views `V_$`. O código usa só `V$SESSION` e `V$PARAMETER` | Só `V_$SESSION` (§3, item 5) |
| ACLs de rede | 5 ACLs com 17 concessões | Recriar com a sintaxe atual, sem a de SMTP (§5) |
| Sinônimos públicos | 31 apontando para o TF. Um deles, `TF_FNC_EXTENSO`, aponta para objeto que não existe mais. Serviam a outros owners, como o `APEXREP` | Não recriar. Os relatórios citam `tf.` ou conectam com `current_schema = TF`. Se algo quebrar na homologação, recriar só o que faltar |
| Owner `APEXREP` | 5 pacotes e 2 tabelas, criado para isolar o TF do Jasper | Os objetos ficam para trás (decisão de 2026-11-10). O usuário pode ser recriado vazio, só de leitura, para o JRI (§3, item 6) |
| Owner `DOLOMITI` | 16 tabelas, 9 triggers e 1 procedure, sem dependência com o TF | Fica para trás (decisão de 2026-11-10) |
| Módulo REST | `os` (prefixo `/os/`), com um template, `itemos/:id`, publicado em 2025-09-17. O export está nos scripts do SQL Workshop (`ORDS_REST_TF_os_2025_09_17.sql`) | Recriar com o mesmo alias de schema, para a URL não mudar |
| `FLOWS_FILES` | 52 arquivos, 31 MB: 27 backups automáticos de aplicação (25 do app 130), 20 PDFs de NF enviados pelo app 130, 4 scripts e 1 imagem | Fica para trás. O export do app 130 de 2026-02 não lê `APEX_APPLICATION_FILES` |
| Diretórios | Só `DATA_PUMP_DIR` e `XMLDIR`, do próprio banco | Nada da aplicação a recriar |
| Referências ao APEX | O TF depende de 2 funções, 3 pacotes e 1 tipo do `APEX_200100`, mas o código não cita `APEX_200100.` por extenso | Nada a mudar: as referências passam pelos sinônimos públicos do próprio APEX |
| Jobs | 3 jobs do scheduler (abaixo) | Voltam com o import, **ligados**: desligar (§6) |

| Job | Agenda | Na virada |
|---|---|---|
| `JOB_ADD_EMAIL_MED_FILA` | Todo dia, 06:00 | Continua desligado: e-mail fica para depois (§3, item 2) |
| `JOB_ENVIA_EMAIL_MED_FILA` | Todo dia, 07:00 e 15:00 | Continua desligado |
| `JOB_SEM_ADM` | Segunda, 00:10 | Religar |

---

## 3. Achados que pedem decisão

1. **O TF tem a role `DBA`.** O TF é o schema da aplicação, e num banco sem patches uma senha do TF vazada daria controle total. Em PL/SQL com direitos do definidor, que é o padrão, roles não valem, e o APEX na prática também não as considera. Assim, o código e as páginas não devem depender do `DBA`. Quem depende são as conexões diretas como TF, como o SQLcl. **Recomendo não conceder `DBA` no destino** e usar um usuário administrativo à parte. Testar em homologação. *Pendente: decisão de Tiago.*

2. **E-mail fica para depois.** *Decisão (2026-11-10):* o envio por SMTP não migra. Ninguém usa o envio hoje, e o plano é contratar um serviço de e-mail por API. Com isso, o [bloqueio da porta 25 na OCI](https://docs.oracle.com/en-us/iaas/releasenotes/changes/f7e95770-9844-43db-916c-6ccbaf2cfe24) deixa de importar. No destino:
   - sem ACL de SMTP e sem `EXECUTE` em `UTL_SMTP`;
   - os dois jobs de e-mail ficam desligados, inclusive depois da virada;
   - o `TF_PCK_SENDMAIL_UTL_SMTP` fica inválido, porque precisa de `V$PARAMETER`. É esperado.

   Quando o serviço for contratado, o envio sai por HTTPS (`APEX_WEB_SERVICE`), com ACL para o host do provedor na porta 443.

3. **PDFs no log.** *Decisão (2026-11-10):* tirar as cópias. Os logs `LTF_` ([convenção](convencoes/banco.md)) guardam 457 MB de PDFs de boleto em 15.307 linhas e 386 MB de DANFEs em 11.787 linhas, 843 MB no total. A causa: as triggers de log copiam a linha inteira, PDF incluído, a cada insert, update ou delete. O boleto tem ainda a coluna `BUFFER_PDF` (CLOB), copiada do mesmo jeito. Nenhum pacote local e nenhuma página do export do app 130 leem essas colunas do log. O patch está na §8 e roda na produção **antes do export**, para o dump já sair sem as cópias.

4. **Login: o MD5 está confirmado.** `TF_PCK_AUTENTICACAO` (linha 149) e `TF_PCK_AUTENTICACAO_E` (linha 117) chamam `DBMS_OBFUSCATION_TOOLKIT.MD5`, que [foi removido no 21c](https://docs.oracle.com/en/database/oracle/oracle-database/21/rnrdm/deprecated-desupported-features.html). No ADB, os dois compilam porque o pacote foi alterado no teste de 2026-02, e lá o login com as senhas antigas não funcionou. *Decisão (2026-11-10):* o reset geral de senhas é aceitável. Então:
   - **Hash novo:** trocar o MD5 por SHA-512 com salt aleatório por usuário, via `DBMS_CRYPTO` (`HASH_SH512`, ou PBKDF2 com `HMAC_SH512` e iterações). Conferir o tamanho da coluna `SENHA`.
   - **Virada:** todos recebem uma senha temporária com `SENHA_EXPIRADA` ligado. O campo já existe; confirmar que ele obriga a troca no primeiro acesso. Como o e-mail não migra, a senha temporária chega aos clientes por outro canal.
   - **Hashes no log:** a versão 1.0 da trigger de log da `TF_USUARIO` copia a coluna `SENHA`. Se a atual ainda copia, os hashes MD5 antigos continuam no log depois do reset. A §8 traz a mesma solução dos PDFs.
   - **ADB:** os dois pacotes alterados no teste de 2026-02 estão salvos em `app/desenv/TF_PCK_AUTENTICACAO_ADB.sql` e `app/desenv/TF_PCK_AUTENTICACAO_E_adb.sql`. O ADB foi encerrado em 2026-11-10. Os dois trocam o MD5 por `APEX_UTIL.GET_HASH`, que não serve para senha: a função foi feita para detectar alteração concorrente de registros, sem salt por usuário e sem iterações. O resto do pacote serve de ponto de partida.

5. **`V$SESSION` é obrigatória.** Das ~620 views `V$` liberadas hoje, o código usa só `V$SESSION` e `V$PARAMETER`. A `TF_PRC_BUSCA_DADOS_LOG` lê `V$SESSION` e é chamada pelas triggers de log mais antigas, as que começam com `tf_prc_busca_dados_log(userenv('sessionid'), ...)`. No ADB ela ficou inválida por falta do grant. Sem ele, insert, update e delete nas tabelas com essas triggers falham. O script da §4 concede `SELECT` em `V_$SESSION`.

6. **Usuário do JRI.** O `APEXREP` foi criado para isolar o TF do Jasper. Os relatórios leem direto do `tf.`, exceto um que cita `tf_pessoa` sem prefixo. O JRI pode conectar como TF, mas a senha fica num arquivo na VM de aplicação, a exposta à internet, e com ela vêm escrita e DDL no schema inteiro de um banco sem patches. *Decisão (2026-11-10):* manter o isolamento, com o `APEXREP` recriado vazio e só de leitura. No 26ai isso não dá trabalho a cada relatório novo:
   - **Sem sinônimos:** uma trigger de logon faz `alter session set current_schema = TF`, e os nomes sem prefixo passam a ser procurados no TF.
   - **Um grant só:** o [privilégio de schema do 23ai/26ai](https://oracle-base.com/articles/23/schema-privileges-23), `grant select any table on schema tf to apexrep`, cobre tabelas, views e views materializadas, inclusive as criadas depois.
   - **Exceção:** função ou pacote chamado na query de um relatório precisa de `grant execute` individual. Não usar `EXECUTE ANY PROCEDURE ON SCHEMA`: o código do TF roda com os direitos do TF, e um procedimento que grava quebraria o isolamento.
   - **Limite:** o grant de schema libera a leitura de tudo, inclusive `TF_USUARIO` e os logs. O ganho é bloquear escrita e DDL, não esconder dados.

7. **Endereços fixos no código.** Nada a mudar no código:
   - As linhas com `localhost` no `TF_PCK_BOLETO_COBRANCA` são comentários.
   - No `XLIB_JASPERREPORTS`, `'localhost'` é só o valor padrão de um parâmetro. O servidor real vem da tabela `XLIB_JASPERREPORTS_CONF`, que precisa apontar para o IP privado da VM de aplicação depois do import (§6). Conferir na homologação.
   - O `UTL_FILE` do `ZT_QR` está na rotina que grava o QR em arquivo, e o banco não tem diretório da aplicação.

---

## 4. Script de pré-import

Rodar no destino com SQLcl, conectado como SYS. As senhas são pedidas na hora, para não ficarem em arquivo.

```sql
define ip_app      = 10.0.1.10     -- IP privado da VM de aplicação
define porta_jri   = 8090          -- exemplo: conferir no Tomcat do JRI
define apex_schema = APEX_260100   -- conferir: select schema from dba_registry where comp_id = 'APEX'

-- 1. No CDB$ROOT: anotar o valor atual e parar os jobs até a virada
show parameter job_queue_processes
alter system set job_queue_processes = 0 scope = both;

-- 2. Na PDB
alter session set container = FREEPDB1;
select sysdate from dual;   -- tem de mostrar a hora de Brasília

-- 3. Tablespaces com teto abaixo dos 12 GB do Free. Estourar um tablespace dá erro
--    de gravação; estourar os 12 GB impede a PDB de abrir.
--    Conferir o caminho com: select file_name from dba_data_files
create tablespace ts_tf  datafile '/opt/oracle/oradata/FREE/FREEPDB1/ts_tf01.dbf'
  size 2g autoextend on next 256m maxsize 6g;
create tablespace ts_log datafile '/opt/oracle/oradata/FREE/FREEPDB1/ts_log01.dbf'
  size 512m autoextend on next 128m maxsize 1g;

-- 4. Usuário com senha nova e sem DBA. O import não recria usuário nem grants (§6)
create user tf identified by "&senha_tf"
  default tablespace ts_tf quota unlimited on ts_tf quota unlimited on ts_log;
grant create session, create table, create view, create sequence, create procedure,
      create trigger, create type, create synonym, create job to tf;

-- 5. Contexto do filtro multiempresa
create or replace context ctx using tf.tf_pck_contexto accessed globally;

-- 6. Pacotes do SYS, como hoje, menos o UTL_SMTP (e-mail fica para depois, §3)
grant execute on sys.dbms_crypto  to tf;
grant execute on sys.dbms_session to tf;
grant execute on sys.utl_file     to tf;
grant execute on sys.utl_http     to tf;
grant execute on sys.utl_inaddr   to tf;
grant execute on sys.utl_tcp      to tf;
grant execute on sys.utl_url      to tf;
-- Das views V$, só a que o código usa. Sem ela, as triggers de log antigas falham (§3, item 5)
grant select on sys.v_$session to tf;

-- 7. APEXREP vazio e só de leitura, usado pelo JRI (§3, item 6). Os 31 sinônimos
--    públicos não são recriados (§2).
create user apexrep identified by "&senha_apexrep";
grant create session to apexrep;
grant select any table on schema tf to apexrep;   -- tabelas e views, atuais e futuras
-- grant execute on tf.<função> to apexrep;       -- só se um relatório chamar função do TF
create or replace trigger apexrep.trg_logon_apexrep after logon on apexrep.schema
begin
  execute immediate 'alter session set current_schema = TF';
end;
/
```

As ACLs vêm em seguida, no mesmo script (§5).

---

## 5. ACLs de rede

| ACL hoje | Hosts | Quem usa | No destino |
|---|---|---|---|
| `power_users` | `*` | APEX 19.1 e 20.1 | `*` para o schema do APEX 26.1, até mapear os destinos reais |
| `smtp_permissions` | `127.0.0.1` e `smtp.dolomiti.inf.br` | TF | Não recriar: e-mail fica para depois (§3) |
| `JasperReportsIntegration-tf` | `127.0.0.1`, `localhost` e `dolomiti.inf.br`, portas 80 a 10000 | TF, APEXREP e APEX | IP privado da VM de aplicação, só na porta do JRI, para TF e APEX |
| `http_permissions` | `viacep.com.br`, porta 80 | TF | Igual |
| `apex_rest_acl` | `apisicredi.localhost`, `apisicoob.localhost` e `apisicoobauth.localhost` | TF e APEX | Mesmos nomes, apontados para a VM de aplicação |

**Os nomes `*.localhost` não exigem mudança no código.** Eles são resolvidos pelo `/etc/hosts`, e no compose do banco o `extra_hosts` aponta esses nomes para o IP privado da VM de aplicação, onde fica o proxy reverso. Hoje esse papel é do suez; na OCI, passa para o nginx ([proxy-reverso.md](proxy-reverso.md) §6). O nginx passa a escutar no IP privado, na porta 3000, com um `server` por nome, e o NSG libera só a VM banco, no [padrão do documento de arquitetura](arquitetura-migracao-oci.md) (§5). Já `localhost` e `127.0.0.1` no código não têm como ser redirecionados; a §3, item 7, mostra que nenhuma linha ativa depende deles.

```yaml
# Trecho do compose da VM banco
services:
  db:
    environment:
      TZ: America/Sao_Paulo
    extra_hosts:
      - "apisicredi.localhost:10.0.1.10"
      - "apisicoob.localhost:10.0.1.10"
      - "apisicoobauth.localhost:10.0.1.10"
```

```sql
-- Continuação do script da §4 (mesma sessão, na PDB)
declare
  procedure ace(p_host varchar2, p_user varchar2,
                p_de pls_integer default null, p_ate pls_integer default null) is
  begin
    dbms_network_acl_admin.append_host_ace(
      host => p_host, lower_port => p_de, upper_port => p_ate,
      ace  => xs$ace_type(privilege_list => xs$name_list('connect', 'resolve'),
                          principal_name => p_user,
                          principal_type => xs_acl.ptype_db));
  end;
begin
  ace('viacep.com.br', 'TF', 80, 80);
  for u in (select 'TF' nome from dual union all select '&apex_schema' from dual) loop
    ace('apisicredi.localhost',    u.nome);
    ace('apisicoob.localhost',     u.nome);
    ace('apisicoobauth.localhost', u.nome);
    ace('&ip_app', u.nome, &porta_jri, &porta_jri);
  end loop;
  -- Como hoje. Ao restringir, basta apagar esta linha: os destinos acima já estão liberados
  ace('*', '&apex_schema');
end;
/
```

Quando o serviço de e-mail por API for contratado, liberar o host do provedor na porta 443 para o TF.

---

## 6. Import e conferência

**O patch da §8 já está na produção** (2026-11-10). Assim o dump sai sem os ~840 MB de PDFs dos logs.

```bash
# Origem (XE 11g). Sem senha na linha: o expdp pergunta, e ela não fica no histórico nem na lista de processos
expdp system schemas=TF directory=DATA_PUMP_DIR dumpfile=tf_%U.dmp filesize=1G logfile=tf_exp.log flashback_time=systimestamp

# Destino. O usuário e os grants já existem (§4); o exclude impede que o dump traga o DBA de volta
impdp system@//<IP privado>:1521/FREEPDB1 schemas=TF directory=DP_DIR dumpfile=tf_%U.dmp logfile=tf_imp.log exclude=user,system_grant,role_grant,default_role,tablespace_quota
```

- **Transferência:** o servidor da Locaweb já tem o OCI CLI configurado desde o teste no ATP. O caminho é o mesmo: `oci os object put` para um bucket e, na VM banco, `oci os object get`.
- **Sem `compression=all`:** o teste no ATP usou essa opção, mas compressão de dados no Data Pump faz parte do Advanced Compression, um opcional pago.

```sql
alter session set container = FREEPDB1;

-- Jobs desligados explicitamente, além do job_queue_processes = 0
begin
  for j in (select job_name from dba_scheduler_jobs where owner = 'TF') loop
    dbms_scheduler.disable('TF.' || j.job_name);
  end loop;
end;
/

-- Recompilar e comparar com a linha de base (§1)
exec dbms_utility.compile_schema('TF', compile_all => false)
select object_type, status, count(*) qtd
  from dba_objects where owner = 'TF' group by object_type, status order by 1, 2;
select name, type, line, text from dba_errors where owner = 'TF' order by 1, 2, 3;

-- As 06:00 dos jobs têm de ser no horário de Brasília
select job_name, start_date, next_run_date from dba_scheduler_jobs where owner = 'TF';
```

**Inválidos esperados:**

| Objeto | Motivo |
|---|---|
| `TF_PCK_ECOMMERCE` | Já inválido na produção: coluna `STATUS` inexistente (ORA-00904) |
| `TF_PCK_SENDMAIL_UTL_SMTP` | Sem `V$PARAMETER` e sem `UTL_SMTP` (§3, item 2) |
| `TF_PCK_AUTENTICACAO` e `TF_PCK_AUTENTICACAO_E` | MD5 removido no 21c, até o hash novo entrar (§3, item 4) |

O `TF_PCK_TRANSPORTE`, inválido na produção, compilou no ADB. Qualquer outro inválido é novidade a investigar.

**Depois:**
1. Criar o workspace `PROD` com o TF como schema e importar o app 130.
2. Recriar o módulo `/os/`.
3. Instalar o JRI e apontar a `XLIB_JASPERREPORTS_CONF` para o IP privado da VM de aplicação.
4. Trocar o hash de senha (§3, item 4).

**Testes mínimos:**
- login com o filtro multiempresa;
- um boleto na homologação do banco;
- um relatório;
- uma alteração numa tabela com trigger de log antiga, como a `TF_USUARIO`, para provar o grant de `V$SESSION`.

**Jobs:**
- **Homologação:** com os jobs do TF desligados, o `job_queue_processes` pode voltar ao valor anotado.
- **Virada:** depois que a origem parar, religar só o `JOB_SEM_ADM` e o `job_queue_processes`.

---

## 7. Terceira rodada de consultas

Executada em 2026-11-10, na produção e no ADB `DEVDOLOMITI`. As consultas ficam abaixo dos resultados, para repetir antes da virada.

| Consulta | Resultado |
|---|---|
| Endereços fixos e recursos antigos | MD5 nos 2 pacotes de autenticação; `localhost` só em comentários e num valor padrão; `UTL_FILE` no `ZT_QR`; nenhuma citação a `APEX_200100.` (§3) |
| Inválidos na produção | `TF_PCK_ECOMMERCE` (DDL em 2025-05) e `TF_PCK_TRANSPORTE` (DDL em 2024-06) |
| O que o TF usa do SYS | Pacotes `DBMS_*` e `UTL_*` já concedidos; das `V$`, só `V$SESSION` e `V$PARAMETER` |
| Como o e-mail sai | Não executada: o e-mail fica para depois (§3) |
| Sinônimo órfão | `TF_FNC_EXTENSO` |
| `FLOWS_FILES` | 27 backups de aplicação, 20 PDFs de NF, 4 scripts e 1 imagem |
| Módulo `/os/` | Um template, `itemos/:id` |
| Crescimento dos boletos | 2025: 736 boletos, 46 MB. 2026, até novembro: 1.430 boletos, 78 MB. O resultado das DANFEs não veio |
| Cópias nos logs | Boleto: 15.307 linhas, 457 MB. DANFE: 11.787 linhas, 386 MB |
| ADB: inválidos | `TF_PCK_ECOMMERCE` (ORA-00904 `STATUS`), `TF_PCK_SENDMAIL_UTL_SMTP` (sem `V_$PARAMETER`) e `TF_PRC_BUSCA_DADOS_LOG` (sem `V_$SESSION`) |

**Leitura do espaço:** sem as cópias no log, os PDFs de boleto crescem ~90 MB/ano. O TF deve chegar ao destino com cerca de 1 GB, e o limite de 12 GB deixa de ser preocupação próxima. Falta só o crescimento das DANFEs, que não muda a conclusão.

Somente leitura, na produção, compatível com 11g. Se alguma consulta der erro, as demais continuam úteis. As de LOB leem só o tamanho dos arquivos, mas é melhor rodá-las fora do horário de pico.

```sql
-- Linhas que citam localhost, 127.0.0.1, recurso antigo ou o schema do APEX por extenso
select name, type, line, trim(text) texto
  from dba_source
 where owner = 'TF'
   and regexp_like(text, 'localhost|127\.0\.0\.1|wm_concat|utl_file|dbms_obfuscation|apex_[0-9]{6}', 'i')
 order by 1, 2, 3;

-- Os 2 package bodies já inválidos
select object_name, last_ddl_time from dba_objects
 where owner = 'TF' and status = 'INVALID';

-- O que o TF usa do SYS de fato (SQL dinâmico não aparece aqui)
select referenced_owner, referenced_name, referenced_type, count(*) qtd
  from dba_dependencies
 where owner = 'TF' and referenced_owner in ('SYS', 'PUBLIC')
   and (referenced_name like 'V$%' or referenced_name like 'V\_$%' escape '\'
        or referenced_name like 'UTL%' or referenced_name like 'DBMS%')
 group by referenced_owner, referenced_name, referenced_type order by 2;

-- Sinônimo público que aponta para objeto inexistente
select s.synonym_name, s.table_name
  from dba_synonyms s
 where s.owner = 'PUBLIC' and s.table_owner = 'TF'
   and not exists (select 1 from dba_objects o
                    where o.owner = 'TF' and o.object_name = s.table_name);

-- Arquivos em FLOWS_FILES: exports de aplicação ou arquivos da aplicação?
select flow_id, filename, file_type, mime_type, round(doc_size/1024) kb, created_on
  from flows_files.wwv_flow_file_objects$ order by created_on;

-- Módulo REST /os/: o que ele expõe
select * from ords_metadata.ords_templates where module_id = 10023;

-- Crescimento dos anexos por ano (DATA_INCLUSAO é o padrão da KB)
select to_char(data_inclusao, 'yyyy') ano, count(*) qtd,
       round(sum(dbms_lob.getlength(pdf_boleto))/1024/1024) mb
  from tf.tf_boleto_cobranca group by to_char(data_inclusao, 'yyyy') order by 1;
select to_char(data_inclusao, 'yyyy') ano, count(*) qtd,
       round(sum(dbms_lob.getlength(imagem_danfe))/1024/1024) mb
  from tf.tf_nota_fiscal_item_pedido group by to_char(data_inclusao, 'yyyy') order by 1;

-- Cópias nos logs: depois do patch da §8, as duas têm de dar 0 MB
select count(*) qtd, round(sum(dbms_lob.getlength(pdf_boleto))/1024/1024) mb
  from tf.ltf_boleto_cobranca;
select count(*) qtd, round(sum(dbms_lob.getlength(imagem_danfe))/1024/1024) mb
  from tf.ltf_nota_fiscal_item_pedido;
```

**No ADB `DEVDOLOMITI`, como ADMIN.** O ADB mostra o que quebrou ao compilar o TF em 23.26. O usuário `TIAGO.STEIL` não enxerga o TF.

```sql
select object_type, object_name from dba_objects
 where owner = 'TF' and status = 'INVALID' order by 1, 2;
select name, type, line, text from dba_errors where owner = 'TF' order by 1, 2, 3;
```

---

## 8. Patch na produção: PDFs fora do log

Decidido e **aplicado em 2026-11-10**, no desenvolvimento e na produção (§3, item 3). As triggers de log (`TRGL_TF_BOLETO_COBRANCA` e `TRGL_TF_NOTA_FISCAL_ITEM_PEDID`) **não mudam**. Uma trigger nova em cada tabela de log zera as colunas de arquivo antes da gravação. Assim não é preciso reescrever as triggers de log, e a regra continua valendo se elas forem regeradas. O log continua registrando `NOME_ARQUIVO`, `MIME_TYPE` e `FILENAME`, então ainda mostra quando um PDF foi gerado ou trocado.

Rodar como TF, fora do horário de pico, primeiro no ambiente de desenvolvimento atual e depois na produção.

```sql
-- 1. Novas linhas de log sem os arquivos
create or replace trigger tf.trgb_ltf_boleto_cobranca
  before insert on tf.ltf_boleto_cobranca
  for each row
begin
  :new.pdf_boleto := null;
  :new.buffer_pdf := null;
end;
/

create or replace trigger tf.trgb_ltf_nf_item_pedido
  before insert on tf.ltf_nota_fiscal_item_pedido
  for each row
begin
  :new.imagem_danfe := null;
end;
/

-- 2. Apagar as cópias que já estão no log. Não tem volta.
update tf.ltf_boleto_cobranca
   set pdf_boleto = null, buffer_pdf = null
 where pdf_boleto is not null or buffer_pdf is not null;

update tf.ltf_nota_fiscal_item_pedido
   set imagem_danfe = null
 where imagem_danfe is not null;

commit;

-- 3. Hashes de senha no log (§3, item 4). Rodar só se a coluna existir:
--    select column_name from dba_tab_columns
--     where owner = 'TF' and table_name = 'LTF_USUARIO' and column_name = 'SENHA';
-- create or replace trigger tf.trgb_ltf_usuario
--   before insert on tf.ltf_usuario
--   for each row
-- begin
--   :new.senha := null;
-- end;
-- /
-- update tf.ltf_usuario set senha = null where senha is not null;
-- commit;
```

**Conferência:** as consultas de cópias nos logs (§7) têm de dar 0 MB. Depois do próximo boleto gerado, a linha nova do log tem de ter `NOME_ARQUIVO` preenchido e `PDF_BOLETO` vazio.

- **Espaço na produção:** o update libera o espaço dentro dos segmentos de LOB, mas não o devolve ao tablespace. Não importa, porque a produção vai ser desligada, e o dump sai menor.
- **Linhas excluídas:** para boletos e notas apagados, o log era a única cópia do PDF. O boleto pode ser reemitido pelo banco, e a DANFE sai da NF-e.

---

## Fontes

Consultadas de 2026-11-05 a 2026-11-10.

- [OCI: bloqueio da porta 25](https://docs.oracle.com/en-us/iaas/releasenotes/changes/f7e95770-9844-43db-916c-6ccbaf2cfe24) · [Troubleshooting do Email Delivery](https://docs.oracle.com/en-us/iaas/Content/Email/Concepts/troubleshooting.htm)
- [Recursos e limites removidos no 21c](https://docs.oracle.com/en/database/oracle/oracle-database/21/rnrdm/deprecated-desupported-features.html)
- [Data Pump: modo schema](https://docs.oracle.com/en/database/oracle/oracle-database/19/sutil/oracle-data-pump-export-utility.html) · [Data Pump e sinônimos públicos (Pythian)](https://www.pythian.com/blog/oracle-data-pump-schema-export-and-public-synonyms)
- [FAQ das imagens Oracle: fuso horário em contêiner](https://github.com/oracle/docker-images/blob/main/OracleDatabase/SingleInstance/FAQ.md)
- Fontes locais: triggers de log em `app/patch/8.0/tf_boleto_cobranca.sql` e `app/patch/5.2/tabelas_etapas_prod_REVO.sql`; relatórios em `app/reports/app130/`; export do app 130 em `Infra/OCI/f130_17022026.sql`.

---

## Changelog

- **2026-11-10 (3):** Tiago decidiu manter o `APEXREP`, vazio e só de leitura, com o grant de schema (script da §4 ativado). Pacote `TF_PCK_AUTENTICACAO_E` do ADB salvo; ADB `DEVDOLOMITI` encerrado e dump do bucket apagado.
- **2026-11-10 (2):** patch dos PDFs aplicado no desenvolvimento e na produção. Pacote de autenticação do ADB salvo. Usuário do JRI: proposta de recriar o `APEXREP` vazio e só de leitura, com privilégio de schema e `current_schema`, sem grants nem sinônimos por relatório.
- **2026-11-10:** terceira rodada de consultas incorporada (§7). Tiago decidiu: reset geral de senhas aceito, com hash novo; e-mail por SMTP não migra, e os dois jobs de e-mail ficam desligados; PDFs saem do log (patch na §8); `APEXREP` e `DOLOMITI` ficam para trás. Sinônimos públicos não são recriados. Achado: a `TF_PRC_BUSCA_DADOS_LOG` precisa do grant de `V$SESSION`, senão as triggers de log antigas falham. Pendentes: role `DBA` e usuário do JRI.
- **2026-11-06:** os nomes `*.localhost` passam a apontar para o nginx, não para o node4ords. Hoje quem atende esses nomes é o suez ([proxy-reverso.md](proxy-reverso.md)).
- **2026-11-05:** criado a partir da segunda rodada do inventário da produção. Inclui linha de base, o que fica fora do schema, achados, script de pré-import, ACLs, comandos de import e terceira rodada de consultas. Incorporadas as anotações do teste de import no ATP (2026-02).
