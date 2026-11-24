-- Pós-instalação do banco: rodar UMA vez, depois que o contêiner ficar saudável
-- e antes de instalar o APEX e o ORDS. Dentro do contêiner, como SYS:
--
--   docker exec -i dolomiti-banco sqlplus -s / as sysdba < pos-instalacao.sql
--
-- Tetos de datafile, undo e limpeza da auditoria adaptados do uc-local-apex-dev
-- (United Codes, licença MIT), scripts after-first-db-start.sh e cap-tablespaces.sh.
-- Ficam de fora, de propósito: desligar archive log, desligar expiração de senha
-- e afrouxar as regras de senha do APEX (análise, §7).

whenever sqlerror exit failure
set serveroutput on size unlimited
set linesize 200

-- 0. Conferências da criação (na raiz do CDB)
prompt == Modo de log: tem de ser ARCHIVELOG
select log_mode from v$database;

alter session set container = FREEPDB1;

prompt == Relógio: tem de ser a hora de Brasília (TZ no compose)
select to_char(sysdate, 'yyyy-mm-dd hh24:mi') agora from dual;

prompt == Conjunto de caracteres: tem de ser AL32UTF8, como na produção atual
select value from nls_database_parameters where parameter = 'NLS_CHARACTERSET';

-- Pasta dos datafiles da PDB. Conferir com: select file_name from dba_data_files
define dir_dados = /opt/oracle/oradata/FREE/FREEPDB1

-- 1. Teto em todo datafile, menos SYSTEM e SYSAUX.
--    Se os datafiles da PDB passarem de 12 GB, ela não abre mais (ORA-12954), em
--    nenhum modo. A imagem cria o undo e o USERS sem teto; no projeto de referência,
--    o undo cresceu sozinho até 3,8 GB e passou do limite. Com teto, quem estoura
--    é uma sessão (ORA-01653 ou ORA-30036), e o banco continua aberto.
begin
  for r in (select file_name, tablespace_name from dba_data_files
             where tablespace_name like 'UNDOTBS%' or tablespace_name = 'USERS') loop
    execute immediate 'alter database datafile ''' || r.file_name ||
      ''' autoextend on next 32m maxsize ' ||
      case when r.tablespace_name = 'USERS' then '1024m' else '2048m' end;
    dbms_output.put_line('teto em ' || r.tablespace_name || ': ' || r.file_name);
  end loop;
end;
/

-- 2. Undo: retenção padrão (900 s) e sem garantia, para o teto degradar em vez de
--    travar. Retenção maior faz o autoajuste crescer o datafile.
alter system set undo_retention = 900 scope = both;
begin
  for r in (select tablespace_name from dba_tablespaces
             where contents = 'UNDO' and retention = 'GUARANTEE') loop
    execute immediate 'alter tablespace ' || r.tablespace_name || ' retention noguarantee';
  end loop;
end;
/

-- 3. Auditoria num tablespace próprio, com teto, e limpeza diária.
--    Cada dia de auditoria unificada vira partições de ~41 MB, quase independente
--    do volume de registros. Retenção de 7 dias: REVER para a produção.
create tablespace audit_trail
  datafile '&dir_dados/audit01.dbf' size 20m autoextend on next 8m maxsize 1g;

begin
  dbms_audit_mgmt.set_audit_trail_location(
    audit_trail_type           => dbms_audit_mgmt.audit_trail_unified,
    audit_trail_location_value => 'AUDIT_TRAIL');
end;
/

begin
  dbms_scheduler.create_job(
    job_name        => 'DOLOMITI_LIMPA_AUDITORIA',
    job_type        => 'PLSQL_BLOCK',
    job_action      => q'[begin
  dbms_audit_mgmt.set_last_archive_timestamp(
    audit_trail_type  => dbms_audit_mgmt.audit_trail_unified,
    last_archive_time => systimestamp - 7);
  dbms_audit_mgmt.clean_audit_trail(
    audit_trail_type        => dbms_audit_mgmt.audit_trail_unified,
    use_last_arch_timestamp => true);
end;]',
    start_date      => systimestamp,
    repeat_interval => 'FREQ=DAILY;BYHOUR=3;BYMINUTE=15',
    enabled         => true,
    auto_drop       => false,
    comments        => 'Mantém 7 dias de auditoria unificada');
end;
/

-- 4. Retenções internas em 7 dias (AWR, histórico de estatísticas e de jobs)
exec dbms_workload_repository.modify_baseline_window_size(window_size => 7);
exec dbms_workload_repository.modify_snapshot_settings(retention => 7 * 1440);
exec dbms_stats.alter_stats_history_retention(7);
exec dbms_scheduler.set_scheduler_attribute('log_history', 7);

-- 5. Tablespace do APEX, com teto. Usado na instalação: apexins.sql TBS_APEX TBS_APEX TEMP /i/
create bigfile tablespace tbs_apex
  datafile '&dir_dados/tbs_apex.dbf' size 20m autoextend on next 20m maxsize 3g;

-- 6. Cursores abertos: importar uma aplicação APEX grande falha com ORA-01000 no padrão
alter system set open_cursors = 1000 scope = both;

prompt == Datafiles e tetos: só SYSTEM e SYSAUX podem ficar sem MAX_MB
select tablespace_name, round(bytes / 1048576) mb, autoextensible,
       case when autoextensible = 'YES' then round(maxbytes / 1048576) end max_mb
  from dba_data_files order by 1;
