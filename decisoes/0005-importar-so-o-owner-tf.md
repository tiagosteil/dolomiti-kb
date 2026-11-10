# 0005 — Importar só o owner TF; APEXREP e DOLOMITI ficam para trás

- **Status:** Aceita
- **Data:** 2026-11-10
- **Quem decidiu:** Tiago
- **Revisar em:** se a homologação mostrar dependência de algum objeto que ficou para trás

## Contexto

O banco da produção (XE 11.2.0.2) tem, além do owner TF da aplicação:

- três versões do APEX (4.0, 19.1 e 20.1), que somam 0,99 GB;
- o owner `APEXREP`, com 5 pacotes e 2 tabelas, criado para isolar o TF do Jasper;
- o owner `DOLOMITI`, com 16 tabelas, 9 triggers e 1 procedure, sem dependência com o TF;
- 31 sinônimos públicos para o TF.

O destino é o Oracle Free 26ai do [ADR 0001](0001-producao-em-oracle-free-em-duas-vms.md). O plano de importar só o TF entrou na análise em 2026-11-04, e os owners pequenos foram decididos em 2026-11-10.

## Opções consideradas

- **Exportação full do banco:** traz as versões antigas do APEX e o dicionário do 11g para um banco novo e limitado a 12 GB.
- **TF mais `APEXREP` e `DOLOMITI`:** leva objetos que o TF não usa. Os do `APEXREP` serviam ao Jasper, e os relatórios leem direto do `tf.`.
- **Só o TF, recriando à parte o que fica fora do schema:** é o caminho de XE para Free indicado pela Oracle (Data Pump) e já foi testado no ADB em 2026-02. Escolhida.

## Decisão

Só o owner **TF** migra, por Data Pump em modo schema. Os objetos do `APEXREP` e o owner `DOLOMITI` ficam para trás. Os sinônimos públicos não são recriados; se algo quebrar na homologação, recria-se só o que faltar.

O que fica fora do schema é recriado à parte, conforme a [importação, §2](../migracao-oci-importacao-tf.md#2-o-que-fica-fora-do-schema): app 130 (exportado do 20.1 e importado no 26.1 com o mesmo ID), contexto `CTX`, grants, ACLs e o módulo REST `/os/`. Os jobs voltam desligados.

O usuário `APEXREP` volta vazio, para o JRI ([ADR 0009](0009-jri-le-pelo-apexrep-vazio-e-so-de-leitura.md)).

## Consequências

### O que fica mais fácil

- O banco novo nasce limpo: sem as versões antigas do APEX, sem o dicionário do 11g e com o TF em ~1 GB depois do [ADR 0008](0008-arquivos-e-senhas-fora-dos-logs.md).
- A contagem de objetos do TF (§1 da importação) serve de conferência objetiva.

### O que fica mais difícil

- Tudo o que fica fora do schema depende de uma lista mantida à mão. Item esquecido só aparece na homologação.
- Os objetos de `DOLOMITI` e `APEXREP` e os 52 arquivos de `FLOWS_FILES` não estarão no banco novo.
- Algum relatório ou consumidor externo pode depender de um sinônimo público não recriado.

## Como reverter

Enquanto a VM da Locaweb existir, exportar o que faltar (owner, objeto ou sinônimo) e importar no destino. Depois que ela for desligada, só pelo backup final, que precisa incluir o banco inteiro.

## Fontes

- [migracao-oci-importacao-tf.md](../migracao-oci-importacao-tf.md), §1, §2 e §6 (2026-11-05 a 2026-11-10).
- [analise-producao-oci-vm-docker.md](../analise-producao-oci-vm-docker.md), §9, "Importação só do owner TF".
- [FAQ do Oracle AI Database Free](https://www.oracle.com/database/free/faq/) e [Data Pump: modo schema](https://docs.oracle.com/en/database/oracle/oracle-database/19/sutil/oracle-data-pump-export-utility.html).
