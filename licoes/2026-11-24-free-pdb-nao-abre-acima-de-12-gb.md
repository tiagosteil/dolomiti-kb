---
data: 2026-11-24
area: oracle
ocorrencias: 1
---

# No Oracle Free, a PDB não abre mais se os datafiles passarem de 12 GB

## Regra
No Free, todo datafile da PDB nasce com teto, menos SYSTEM e SYSAUX: undo 2 GB, USERS e auditoria 1 GB, e os da aplicação conforme a [importação, §4](../migracao-oci-importacao-tf.md#4-script-de-pré-import). O undo fica com `undo_retention` 900 e sem garantia. Alertar quando o total passar de 9 GB.

## Contexto
Produção e dev no Oracle AI Database Free 26ai ([ADR 0001](../decisoes/0001-producao-em-oracle-free-em-duas-vms.md), [ADR 0003](../decisoes/0003-dev-em-a1-com-o-compose-da-producao.md)), que limita os datafiles da PDB a 12 GB. Achado em 2026-11-24, ao ler o projeto de referência uc-local-apex-dev para montar o [compose](../compose/README.md).

## O que aconteceu
No uc-local-apex-dev, o datafile de undo cresceu sozinho até 3.810 MB, sem ninguém ver, e levou a PDB além dos 12 GB. O `ORA-12954` sai durante a abertura, antes de a PDB abrir. Por isso `open read only` e `open upgrade` também falham, e nenhum comando dentro da PDB consegue reduzir o espaço. A volta é um reparo manual com o CDB em `MOUNT`. O caso está documentado no `cap-tablespaces.sh` do projeto (branch `26-4`).

## Causa raiz
A imagem cria o undo, o USERS, o SYSTEM e o SYSAUX com autoextend sem teto. O autoajuste do undo cresce o datafile para cumprir o `undo_retention`, e o limite do Free conta todos os datafiles da PDB juntos. Um datafile sem teto pode consumir sozinho toda a folga.

## Como foi resolvido
Preventivamente:
- o [`pos-instalacao.sql`](../compose/banco/pos-instalacao.sql) aplica os tetos de undo, USERS, auditoria e APEX, a retenção do undo e a limpeza diária da auditoria;
- a importação já criava `TS_TF` e `TS_LOG` com teto.

Os tetos somam mais de 12 GB de propósito. Eles não reservam espaço: garantem que um datafile sozinho não tome toda a folga. Com teto, quem estoura é uma sessão (`ORA-01653` ou `ORA-30036`), e o banco continua aberto. Manter o total baixo é papel do alerta de 9 GB ([análise, §7](../analise-producao-oci-vm-docker.md#7-o-que-precisa-mudar-em-relação-à-imagem-dos-links)).

## Sinais de alerta
- Soma dos datafiles da PDB acima de 9 GB.
- Datafile de undo crescendo entre uma conferência e outra.
- `ORA-01653` ou `ORA-30036` numa sessão: o teto funcionou, e é hora de olhar o espaço.
- `ORA-12954` na abertura da PDB: o limite já passou.

## Onde se aplica
Dev e produção, na primeira subida e em todo tablespace novo, que já nasce com `MAXSIZE`. SYSTEM e SYSAUX ficam sem teto: um erro de espaço no meio de uma operação de dicionário é pior que o disco poupado.
