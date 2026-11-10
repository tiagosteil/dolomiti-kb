# 0009 — O JRI lê pelo `APEXREP`, vazio e só de leitura

- **Status:** Aceita
- **Data:** 2026-11-10
- **Quem decidiu:** Tiago
- **Revisar em:** se um relatório precisar gravar no banco, ou se a leitura de tudo pelo `APEXREP` (inclusive `TF_USUARIO`) passar a ser problema

## Contexto

O JRI roda a query de cada relatório conectado ao banco por JDBC. Na produção, o owner `APEXREP` foi criado para isolar o TF do Jasper, com sinônimos públicos para o TF.

Na OCI, o JRI fica na VM de aplicação, a exposta à internet, e o banco não recebe patches ([ADR 0001](0001-producao-em-oracle-free-em-duas-vms.md)). Os objetos do `APEXREP` ficam para trás ([ADR 0005](0005-importar-so-o-owner-tf.md)). Os relatórios leem direto do `tf.`, exceto um que cita `tf_pessoa` sem prefixo.

## Opções consideradas

- **JRI conectado como TF:** é o mais simples, mas a senha do TF fica num arquivo da VM exposta, e com ela vêm escrita e DDL no schema inteiro.
- **`APEXREP` com grants por objeto e sinônimos:** isola, mas cada tabela ou view nova usada por relatório exige grant e sinônimo.
- **`APEXREP` vazio, com privilégio de schema e `current_schema`:** isola sem trabalho por relatório novo. Escolhida.

## Decisão

O usuário `APEXREP` é recriado **vazio e só de leitura**:

- `grant select any table on schema tf to apexrep`, o [privilégio de schema do 23ai/26ai](https://oracle-base.com/articles/23/schema-privileges-23), cobre tabelas, views e views materializadas, inclusive as criadas depois;
- uma trigger de logon faz `alter session set current_schema = TF`, então nomes sem prefixo são procurados no TF, sem sinônimos;
- função ou pacote chamado na query de um relatório recebe `grant execute` individual. Nunca `EXECUTE ANY PROCEDURE ON SCHEMA`: o código do TF roda com os direitos do TF, e um procedimento que grava quebraria o isolamento.

O script está na [importação, §4](../migracao-oci-importacao-tf.md#4-script-de-pré-import).

## Consequências

### O que fica mais fácil

- Senha vazada do JRI não dá escrita nem DDL.
- Relatório novo não exige grant nem sinônimo, salvo se chamar função do TF.

### O que fica mais difícil

- **O ganho é bloquear escrita, não esconder dados:** o grant de schema libera a leitura de tudo, inclusive `TF_USUARIO` e os logs.
- Depende do privilégio de schema do 23ai em diante. Na saída para o APEX Service, a questão some, porque lá o JRI nem conecta.
- Mais um usuário e mais uma senha para guardar e trocar.

## Como reverter

Conectar o JRI como TF, trocando usuário e senha no datasource do JRI. Ou voltar aos grants por objeto, se for preciso esconder tabelas.

## Fontes

- [migracao-oci-importacao-tf.md](../migracao-oci-importacao-tf.md), §3 (item 6) e §4 (2026-11-10).
- [Schema privileges no 23ai (oracle-base)](https://oracle-base.com/articles/23/schema-privileges-23), consultado em 2026-11-10.
