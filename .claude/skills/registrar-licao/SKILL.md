---
name: registrar-licao
description: Registra uma lição operacional da Dolomiti — incidente, erro, pegadinha ou comportamento não-óbvio da OCI, do Oracle (XE 11g, Free 26ai), do APEX/ORDS, do Docker, do nginx/proxy, das integrações bancárias (Sicoob, Sicredi) ou do JRI — e promove a regra para o índice carregado em toda sessão. Usar depois de resolver um problema, quando algo surpreender ou custar tempo, ou quando o usuário disser "anota isso", "registra a lição", "isso não pode acontecer de novo".
---

# Skill: registrar-licao

É o mecanismo pelo qual esta KB aprende. Uma lição só vale se mudar o que o agente faz na próxima vez: por isso o produto final é uma **regra**, não um relato.

## Fluxo

1. **Extrair a regra primeiro**, em uma frase imperativa ("Antes de X, fazer Y"). Se não sai uma regra, não é lição: é diário, e não precisa de registro.
2. **Buscar duplicata:** `grep -ril "<termo>" licoes/`. Se a lição já existe:
   - incrementar `ocorrencias` no frontmatter, acrescentar data e novo contexto;
   - **na 2ª ocorrência, propor a promoção** (passo 5).
3. **Criar** `licoes/AAAA-MM-DD-titulo.md` a partir de `_template.md`: regra, contexto, o que aconteceu, causa raiz, como foi resolvido, sinais de alerta, onde se aplica. Áreas: `oci`, `oracle`, `apex-ords`, `docker`, `nginx`, `integracoes-bancarias`, `jri`, `outro`.
4. **Atualizar `licoes/_indice.md`** com a linha `- **regra** — [detalhe](arquivo.md) (AAAA-MM-DD)` na seção da área (criar a seção se ainda não existir). Esse índice é carregado em toda sessão: se passar de ~40 linhas, consolidar lições parecidas antes de acrescentar.
5. **Promover quando maduro** (2ª ocorrência, ou qualquer regra sobre segurança, produção ou perda de dado):
   - regra de comportamento → propor edição em `CLAUDE.md`;
   - sequência de passos → propor runbook em `runbooks/`;
   - mostrar o trecho e **pedir aprovação**. Depois de promovida, a linha sai do índice e aponta para o novo lugar.

## Regras

- Causa raiz, não sintoma. "O token do Sicoob falhou" é sintoma; "a senha do PFX ficou desatualizada em uma das ocorrências do settings do suez" é causa.
- Nunca incluir senha, PFX, conteúdo de wallet, IP público de produção ou dado de cliente.
- Se a lição corrige um documento da KB (análise, proxy, convenção), corrigir o documento também e citar a lição no changelog dele.
