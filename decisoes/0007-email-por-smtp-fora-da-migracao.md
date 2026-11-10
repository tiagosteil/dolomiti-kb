# 0007 — E-mail por SMTP fica fora da migração

- **Status:** Aceita
- **Data:** 2026-11-10
- **Quem decidiu:** Tiago
- **Revisar em:** ao contratar o serviço de e-mail por API, ou se algum cliente precisar do envio antes disso

## Contexto

O TF envia e-mail por `UTL_SMTP` (`TF_PCK_SENDMAIL_UTL_SMTP`), com ACL para `smtp.dolomiti.inf.br` e dois jobs diários (`JOB_ADD_EMAIL_MED_FILA` e `JOB_ENVIA_EMAIL_MED_FILA`). Ninguém usa o envio hoje.

A OCI [bloqueia a porta 25](https://docs.oracle.com/en-us/iaas/releasenotes/changes/f7e95770-9844-43db-916c-6ccbaf2cfe24) por padrão, e no 26ai o pacote de envio fica inválido sem `V$PARAMETER`.

## Opções consideradas

- **Migrar o SMTP como está:** exige tratar o bloqueio da porta 25 ou trocar a porta, recriar a ACL e o grant de `UTL_SMTP` e liberar `V$PARAMETER`, tudo para um recurso sem uso.
- **Trocar já por um serviço de e-mail por API:** é o destino planejado, mas acrescenta escolha de fornecedor e reescrita do envio à migração.
- **Deixar o e-mail para depois:** escolhida.

## Decisão

O envio por SMTP **não migra**. No destino:

- sem ACL de SMTP e sem `EXECUTE` em `UTL_SMTP`;
- os dois jobs de e-mail ficam desligados, inclusive depois da virada;
- o `TF_PCK_SENDMAIL_UTL_SMTP` fica inválido, e isso é esperado.

Quando o serviço for contratado, o envio sai por HTTPS (`APEX_WEB_SERVICE`), com ACL para o host do provedor na porta 443.

## Consequências

### O que fica mais fácil

- O bloqueio da porta 25 na OCI deixa de importar.
- Menos ACLs, grants e jobs a recriar e conferir na migração.

### O que fica mais difícil

- A aplicação fica sem e-mail até o serviço ser contratado.
- A senha temporária do [ADR 0006](0006-reset-de-senhas-com-hash-novo.md) não pode ir por e-mail.
- Um inválido esperado entra na conferência pós-import e precisa estar na lista, para não esconder outro.

## Como reverter

Recriar a ACL de SMTP e o grant de `UTL_SMTP`, conceder `SELECT` em `V_$PARAMETER`, recompilar o pacote, usar um relay numa porta liberada e religar os dois jobs.

## Fontes

- [migracao-oci-importacao-tf.md](../migracao-oci-importacao-tf.md), §2, §3 (item 2) e §5 (2026-11-10).
- [OCI: bloqueio da porta 25](https://docs.oracle.com/en-us/iaas/releasenotes/changes/f7e95770-9844-43db-916c-6ccbaf2cfe24), consultado em 2026-11-10.
