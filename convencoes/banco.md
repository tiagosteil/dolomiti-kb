# Convenções — Banco de dados

Padrões de PL/SQL válidos para todo o sistema (schema `TF`).

## Nomenclatura
- Tabelas com prefixo **`TF_`**; PKs com prefixo **`ID_`**.
- Objetos e colunas em **MAIÚSCULO**.
- **Comentários em português** (aceita acentuação — o banco usa `ç`, `ã`, etc.).
- Views do CRM: prefixo **`VW_CRM_`** (ex.: `VW_CRM_CARTEIRA_VIGENTE`).

## Chaves primárias
- Populadas por **SEQUENCE + TRIGGER `BEFORE INSERT`** (não usar IDENTITY).
- Padrão de trigger:
  ```sql
  CREATE OR REPLACE TRIGGER tf.trgb_<tabela> BEFORE INSERT ON tf.<tabela>
      FOR EACH ROW WHEN ( new.<id> IS NULL )
  BEGIN
      :new.<id> := tf.<sequence>.nextval;
  END;
  /
  ```

## Auditoria
- **Inclusão:** `DATA_INCLUSAO` (`DATE DEFAULT SYSDATE`) + `USUARIO_INCLUSAO` (`VARCHAR2`).
- **Alteração:** `DATA_ALTERACAO` + `USUARIO_ALTERACAO`.
- Algumas tabelas têm **trigger de log** própria que grava histórico numa tabela sombra `L<tabela>` (ex.: `TF_PESSOA_REPRESENTANTE` → `LTF_PESSOA_REPRESENTANTE`). Onde existir, o log de alteração já é automático; as colunas `DATA_ALTERACAO/USUARIO_ALTERACAO` da própria linha são preenchidas pelo processo da tela.
- **O log não guarda arquivo nem senha** (decisão de 2026-11-10). Colunas BLOB/CLOB com PDF ou imagem e hashes de senha ficam vazios na tabela `L<tabela>`; o nome e o tipo do arquivo continuam no log. O jeito usado é uma trigger `BEFORE INSERT` na própria tabela de log que zera essas colunas (ex.: `TRGB_LTF_BOLETO_COBRANCA`), sem mexer na trigger de log. Detalhes em [migracao-oci-importacao-tf.md](../migracao-oci-importacao-tf.md) §8.

## Domínios (status/flags)
- Representados por `VARCHAR2(1)` + `CHECK`. Prefira **constraint nomeada** (`..._CK`) para facilitar manutenção.
- Documente o significado dos códigos em `COMMENT ON COLUMN`.

## Multitenancy
- Toda tabela de negócio é segmentada por empresa. Ver [multiempresa.md](multiempresa.md).
