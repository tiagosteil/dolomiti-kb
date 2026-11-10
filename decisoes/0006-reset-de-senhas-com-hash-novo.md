# 0006 — Reset geral de senhas, com hash novo, na virada

- **Status:** Aceita
- **Data:** 2026-11-10
- **Quem decidiu:** Tiago
- **Revisar em:** na homologação, ao implementar o hash novo e testar o `SENHA_EXPIRADA`

## Contexto

O login da aplicação (`TF_PCK_AUTENTICACAO`, linha 149, e `TF_PCK_AUTENTICACAO_E`, linha 117) grava a senha como MD5 do `DBMS_OBFUSCATION_TOOLKIT`. Esse pacote [foi removido no 21c](https://docs.oracle.com/en/database/oracle/oracle-database/21/rnrdm/deprecated-desupported-features.html) e não existe no Free 26ai do [ADR 0001](0001-producao-em-oracle-free-em-duas-vms.md). Sem mudança, o login para depois do import.

No teste do ADB, em 2026-02, os dois pacotes foram alterados para `APEX_UTIL.GET_HASH`, e o login com as senhas antigas não funcionou ([importação, §3, item 4](../migracao-oci-importacao-tf.md#3-achados-que-pedem-decisão)).

## Opções consideradas

- **`APEX_UTIL.GET_HASH`, como no teste do ADB:** a função foi feita para detectar alteração concorrente de registros. Não tem salt por usuário nem iterações, e não serve para senha.
- **Manter as senhas atuais, refazendo o MD5 com `DBMS_CRYPTO` (`HASH_MD5`) e trocando para o hash novo no próximo login de cada usuário:** evita o reset em massa. Em troca, o MD5 sem salt de quem não logar continua no banco sem patches por tempo indeterminado, e o login fica com dois caminhos. Que o `DBMS_CRYPTO` reproduz o mesmo hash do toolkit é suposição, não testada. Esta opção não estava na análise; foi acrescentada ao registrar o ADR.
- **Reset geral com hash novo:** escolhida.

## Decisão

Na virada, **todas as senhas são redefinidas**:

- **Hash novo:** SHA-512 com salt aleatório por usuário, via `DBMS_CRYPTO` (`HASH_SH512`), ou PBKDF2 com `HMAC_SH512` e iterações. A escolha entre os dois fica para a implementação na homologação, conferindo o tamanho da coluna `SENHA`.
- **Senha temporária:** todos recebem uma com `SENHA_EXPIRADA` ligado, que deve obrigar a troca no primeiro acesso (confirmar na homologação).
- **Hashes antigos no log:** se a trigger de log da `TF_USUARIO` ainda copia a `SENHA`, o MD5 antigo sai do log como no [ADR 0008](0008-arquivos-e-senhas-fora-dos-logs.md).

O resto dos pacotes alterados no ADB, salvos em `app/desenv/`, serve de ponto de partida.

## Consequências

### O que fica mais fácil

- Nenhum hash MD5 sem salt chega ao banco novo.
- Um só caminho de login, sem código de transição.

### O que fica mais difícil

- Todos os usuários de todos os clientes trocam de senha na virada.
- O e-mail não migra ([ADR 0007](0007-email-por-smtp-fora-da-migracao.md)), então a senha temporária chega aos clientes por outro canal, a definir antes da virada.
- Os pacotes de autenticação precisam ser reescritos e testados na homologação.

## Como reverter

Antes da virada, trocar para a opção de rehash no login: implementar a verificação do MD5 com `DBMS_CRYPTO`, conferindo antes que o hash bate com o do toolkit. Depois da virada não há volta, porque as senhas antigas já foram substituídas, e nem é preciso.

## Fontes

- [migracao-oci-importacao-tf.md](../migracao-oci-importacao-tf.md), §3, item 4, e §8 (2026-11-10).
- [Recursos removidos no 21c](https://docs.oracle.com/en/database/oracle/oracle-database/21/rnrdm/deprecated-desupported-features.html), consultado em 2026-11-10.
