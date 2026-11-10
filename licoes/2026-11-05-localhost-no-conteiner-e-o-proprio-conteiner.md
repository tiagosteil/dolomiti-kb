---
data: 2026-11-05
area: docker
ocorrencias: 1
---

# No contêiner, `localhost` é o próprio contêiner

## Regra
O banco em contêiner chama o proxy pelos nomes `*.localhost` (`apisicoob.localhost`, `apisicoobauth.localhost`, `apisicredi.localhost`), apontados por `extra_hosts` no compose para o IP privado da VM de aplicação. Nunca usar `localhost` ou `127.0.0.1` literais para falar com outro serviço.

## Contexto
Hoje banco, suez e JRI convivem na mesma VM da Locaweb, e o `/etc/hosts` resolve os nomes `*.localhost` para `127.0.0.1`. Na OCI, o banco fica num contêiner em outra VM ([ADR 0001](../decisoes/0001-producao-em-oracle-free-em-duas-vms.md)), e o proxy passa a ser o nginx da VM de aplicação ([ADR 0004](../decisoes/0004-nginx-no-lugar-de-node4ords-e-suez.md)).

## O que aconteceu
Na análise de 2026-11-05 ([análise, §6](../analise-producao-oci-vm-docker.md#6-uma-ou-duas-vms)), as chamadas para `localhost` apareceram como ponto que precisa mudar. A terceira rodada de consultas, em 2026-11-10, mostrou que nenhuma linha ativa do TF depende de `localhost` literal. O `XLIB_JASPERREPORTS` usa `'localhost'` só como valor padrão: o servidor real vem da `XLIB_JASPERREPORTS_CONF` ([importação, §3, item 7](../migracao-oci-importacao-tf.md#3-achados-que-pedem-decisão)).

## Causa raiz
Dentro do contêiner, `localhost` e `127.0.0.1` são a interface de loopback do próprio contêiner, não da VM, e muito menos de outra VM.

## Como foi resolvido
Os nomes `*.localhost` continuam no código e nas ACLs. O `extra_hosts` do compose do banco aponta esses nomes para o IP privado da VM de aplicação ([importação, §5](../migracao-oci-importacao-tf.md#5-acls-de-rede)). A `XLIB_JASPERREPORTS_CONF` passa a apontar para o IP privado da VM de aplicação depois do import.

## Sinais de alerta
- `ORA-29273` com `ORA-12541` (conexão recusada) ou `ORA-12545` (nome não resolvido) numa chamada que funcionava na Locaweb.
- Relatório do JRI que não abre depois do import.

## Onde se aplica
Toda chamada de saída do banco: integrações bancárias, JRI e serviços futuros, como o e-mail por API. O proxy escolhe o destino pelo nome, então chamar o IP direto também não funciona.
