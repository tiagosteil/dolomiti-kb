# 0008 — Os logs `LTF_` não guardam arquivo nem senha

- **Status:** Aceita — aplicada no desenvolvimento e na produção em 2026-11-10
- **Data:** 2026-11-10
- **Quem decidiu:** Tiago
- **Revisar em:** se alguém precisar recuperar um PDF pelo log, ou se uma trigger de log nova copiar outra coluna de arquivo

## Contexto

As triggers de log copiam a linha inteira para a tabela `L<tabela>` a cada insert, update ou delete ([convenção de banco](../convencoes/banco.md)). Com isso, em 2026-11-10 os logs guardavam:

- 457 MB de PDFs de boleto, em 15.307 linhas da `LTF_BOLETO_COBRANCA`, mais a coluna `BUFFER_PDF` (CLOB);
- 386 MB de DANFEs, em 11.787 linhas da `LTF_NOTA_FISCAL_ITEM_PEDIDO`.

São 843 MB de um owner de 1,84 GB, que o export levaria para o Free, limitado a 12 GB ([ADR 0001](0001-producao-em-oracle-free-em-duas-vms.md)). Nenhum pacote local e nenhuma página do app 130 leem essas colunas do log.

## Opções consideradas

- **Manter as cópias:** cabe nos 12 GB, mas quase dobra o dump e o crescimento do log.
- **Reescrever as triggers de log sem as colunas de arquivo:** a regra se perde se as triggers forem regeradas.
- **Uma trigger `BEFORE INSERT` em cada tabela de log, que zera as colunas de arquivo:** as triggers de log não mudam. Escolhida.

## Decisão

As tabelas de log não guardam conteúdo de arquivo nem hash de senha:

- `TRGB_LTF_BOLETO_COBRANCA` zera `PDF_BOLETO` e `BUFFER_PDF`;
- `TRGB_LTF_NF_ITEM_PEDIDO` zera `IMAGEM_DANFE`;
- as cópias que já estavam no log foram apagadas por update.

O log continua registrando `NOME_ARQUIVO`, `MIME_TYPE` e `FILENAME`, então ainda mostra quando um arquivo foi gerado ou trocado. O mesmo vale para a `SENHA` da `LTF_USUARIO`, se ela existir (pendente de conferência). O patch está na [importação, §8](../migracao-oci-importacao-tf.md#8-patch-na-produção-pdfs-fora-do-log).

## Consequências

### O que fica mais fácil

- O TF chega ao destino com ~1 GB, e os PDFs de boleto crescem ~90 MB/ano.
- A regra sobrevive à regeração das triggers de log.

### O que fica mais difícil

- **Não tem volta:** para boletos e notas excluídos, o log era a única cópia do PDF. O boleto pode ser reemitido pelo banco, e a DANFE sai da NF-e.
- Toda tabela nova com arquivo e trigger de log precisa da trigger que zera a coluna, ou o problema volta.

## Como reverter

Apagar as triggers `TRGB_LTF_*`: as próximas linhas de log voltam a copiar os arquivos. As cópias apagadas só voltam de um backup da produção anterior a 2026-11-10.

## Fontes

- [migracao-oci-importacao-tf.md](../migracao-oci-importacao-tf.md), §3 (item 3), §7 e §8 (2026-11-10).
- [convencoes/banco.md](../convencoes/banco.md), "Auditoria".
