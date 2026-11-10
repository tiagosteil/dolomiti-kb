---
data: 2026-11-05
area: docker
ocorrencias: 1
---

# O contêiner do Oracle vem em UTC, e a produção roda no horário de Brasília

## Regra
No compose do banco, definir `TZ=America/Sao_Paulo` e, logo depois de subir o contêiner, conferir que `select sysdate from dual` mostra a hora de Brasília.

## Contexto
Migração do XE 11g da Locaweb para o Oracle Free 26ai em Docker ([ADR 0001](../decisoes/0001-producao-em-oracle-free-em-duas-vms.md)).

## O que aconteceu
No inventário de 2026-11-05, o `SYSDATE` da produção marcou 19:49 numa consulta salva às 19:51 de Brasília: o servidor roda no horário local. O `dbtimezone` é `+00:00`, mas não afeta o `SYSDATE`. A [FAQ das imagens da Oracle](https://github.com/oracle/docker-images/blob/main/OracleDatabase/SingleInstance/FAQ.md) diz que o contêiner usa UTC por padrão.

## Causa raiz
O `SYSDATE` segue o relógio do sistema operacional do processo do banco. No contêiner, esse relógio é UTC, a menos que a variável `TZ` diga outra coisa.

## Como foi resolvido
Preventivamente: `TZ: America/Sao_Paulo` no compose ([importação, §5](../migracao-oci-importacao-tf.md#5-acls-de-rede)) e conferência do `SYSDATE` no script de pré-import ([importação, §4](../migracao-oci-importacao-tf.md#4-script-de-pré-import)).

## Sinais de alerta
- Datas de inclusão, boletos e agendamentos 3 h adiantados.
- Jobs rodando 3 h antes do previsto.
- Agendamento marcado como atrasado antes da hora, porque a regra usa `trunc(SYSDATE)`.

## Onde se aplica
Todo contêiner do banco: dev ([ADR 0003](../decisoes/0003-dev-em-a1-com-o-compose-da-producao.md)) e produção. Vale também para o ORDS e o Tomcat do JRI, se gravarem ou mostrarem hora.
