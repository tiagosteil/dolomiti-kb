# 0010 — O TF nasce sem a role `DBA`; privilégios só diretos e conforme a necessidade

- **Status:** Aceita
- **Data:** 2026-11-10
- **Quem decidiu:** Tiago
- **Revisar em:** na homologação, se a lista de grants crescer a ponto de se aproximar do `DBA`, ou se algo só funcionar com a role

## Contexto

Na produção, o owner TF tem as roles `DBA`, `CONNECT` e `RESOURCE` ([importação, §2](../migracao-oci-importacao-tf.md#2-o-que-fica-fora-do-schema)). No Oracle Free do [ADR 0001](0001-producao-em-oracle-free-em-duas-vms.md), o banco não recebe patches, e uma senha do TF vazada daria controle total sobre ele.

O código não deveria depender da role: PL/SQL com direitos do definidor, o padrão, ignora roles, e o APEX na prática também. Quem depende são as conexões diretas como TF, como o SQLcl ([importação, §3, item 1](../migracao-oci-importacao-tf.md#3-achados-que-pedem-decisão)).

## Opções consideradas

- **Replicar o `DBA`, como hoje:** nada quebra na migração, mas o schema da aplicação continua com controle total de um banco sem patches.
- **TF sem login (*schema-only account*), com deploy por um usuário com *proxy authentication*:** isola mais, mas muda o jeito de aplicar patch e de conectar pelo SQLcl. Dá para chegar nele depois, partindo da opção escolhida.
- **TF sem `DBA`, só com privilégios diretos, e um usuário administrativo à parte:** escolhida.

## Decisão

O TF é criado **sem a role `DBA`**, só com os privilégios diretos do [script de pré-import](../migracao-oci-importacao-tf.md#4-script-de-pré-import): `CREATE SESSION`, `CREATE TABLE`, `CREATE VIEW`, `CREATE SEQUENCE`, `CREATE PROCEDURE`, `CREATE TRIGGER`, `CREATE TYPE`, `CREATE SYNONYM` e `CREATE JOB`, as quotas, o `EXECUTE` nos pacotes do SYS e o `SELECT` em `V_$SESSION`.

**Os acessos são liberados conforme a necessidade.** Cada erro de privilégio na homologação vira um grant direto e específico, acrescentado ao script de pré-import com o motivo. Não se concede de volta o `DBA` nem privilégio `ANY` sobre o banco inteiro.

Tarefas de administração (usuários, ACLs, contexto, parâmetros, jobs do sistema) são feitas por um usuário administrativo à parte.

## Consequências

### O que fica mais fácil

- Senha do TF vazada dá acesso ao schema da aplicação, não ao banco inteiro.
- Os privilégios do TF ficam listados num script, com o motivo de cada um.

### O que fica mais difícil

- A homologação pode revelar privilégios que faltam. Código que lê views `DBA_` ou `V$` além da `V$SESSION`, ou SQL dinâmico que cria objetos de outros tipos, falha até receber o grant.
- O que hoje se faz conectado como TF e exige `DBA` passa a exigir o usuário administrativo: mais uma credencial para guardar.

## Como reverter

`grant dba to tf`, conectado como administrador. O efeito é imediato.

## Fontes

- [migracao-oci-importacao-tf.md](../migracao-oci-importacao-tf.md), §2, §3 (item 1) e §4 (2026-11-05 a 2026-11-10).
