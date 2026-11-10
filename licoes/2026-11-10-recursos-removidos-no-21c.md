---
data: 2026-11-10
area: oracle
ocorrencias: 1
---

# O código do 11g usa recursos que não existem mais no 26ai

## Regra
Antes de levar código do 11g para o 21c ou mais novo, procurar no `dba_source` os recursos removidos (`dbms_obfuscation_toolkit`, `wm_concat`) e decidir o que fazer com cada ocorrência antes do import. Senha nunca com `APEX_UTIL.GET_HASH`: só `DBMS_CRYPTO`, com salt por usuário.

## Contexto
Migração do TF do XE 11.2.0.2 para o Oracle Free 26ai ([ADR 0001](../decisoes/0001-producao-em-oracle-free-em-duas-vms.md)).

## O que aconteceu
No teste de import no ADB, em 2026-02, os pacotes de autenticação não compilaram, porque chamam `DBMS_OBFUSCATION_TOOLKIT.MD5`. A correção feita no teste trocou o MD5 por `APEX_UTIL.GET_HASH`, e o login com as senhas antigas deixou de funcionar. A terceira rodada de consultas, em 2026-11-10, confirmou o MD5 em `TF_PCK_AUTENTICACAO` (linha 149) e `TF_PCK_AUTENTICACAO_E` (linha 117) ([importação, §3, item 4](../migracao-oci-importacao-tf.md#3-achados-que-pedem-decisão)).

## Causa raiz
O `DBMS_OBFUSCATION_TOOLKIT` [foi removido no 21c](https://docs.oracle.com/en/database/oracle/oracle-database/21/rnrdm/deprecated-desupported-features.html). O `APEX_UTIL.GET_HASH` foi feito para detectar alteração concorrente de registros e gera outro hash, sem salt nem iterações.

## Como foi resolvido
Reset geral de senhas com hash novo pelo `DBMS_CRYPTO` ([ADR 0006](../decisoes/0006-reset-de-senhas-com-hash-novo.md)). A consulta de recursos antigos está na [importação, §7](../migracao-oci-importacao-tf.md#7-terceira-rodada-de-consultas) e deve ser repetida antes da virada.

## Sinais de alerta
- `PLS-00201` ou pacote inválido depois do import, citando um pacote do SYS.
- Login que falha para todos os usuários depois de uma migração de versão.

## Onde se aplica
Todo código PL/SQL que sai do 11g: patches antigos em `app/patch/`, fontes de `app/prod/` e o que vier de outros owners.
