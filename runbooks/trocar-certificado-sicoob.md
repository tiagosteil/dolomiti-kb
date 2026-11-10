# Runbook — trocar o certificado do Sicoob no suez

- **Quando usar:** o certificado A1 (PFX) de um cliente Sicoob vai vencer ou foi reemitido. Vale enquanto a produção estiver na VM da Locaweb, com o suez. Na OCI, o nginx usa PEM e o procedimento muda ([proxy-reverso.md, §6](../proxy-reverso.md#6-migração-para-a-oci-nginx-no-lugar-dos-apps-node)).
- **Tempo estimado:** não medido; registrar na próxima execução.
- **Pré-requisitos:**
  - acesso root ao servidor da produção;
  - o PFX novo e a senha, recebidos do cliente por canal seguro, nunca guardados em texto no Drive ou na KB;
  - conexão ao banco como TF para buscar o token;
  - de preferência, fora do horário de emissão de boletos: enquanto a senha estiver errada, o erro aparece para o cliente na tela de boletos.
- **Última execução real:** 2026-11-05 (certificado do Jornal Repercussão), corrigida em 2026-11-06 ([lição](../licoes/2026-11-06-senha-do-pfx-em-todas-as-ocorrencias.md)).

## Passos

Um passo por vez: conferir o resultado antes de seguir.

1. **Backup** do PFX e do settings atuais, com a data no nome:
   ```bash
   cd /opt/suez/config
   cp settings.json settings.json.antes-AAAA-MM-DD
   cp cert/<pfx-atual>.pfx cert/<pfx-atual>.pfx.antes-AAAA-MM-DD
   ```
2. **Copiar o PFX novo** para `/opt/suez/config/cert/` e restringir o acesso com `chmod 600`.
3. **Conferir se a senha abre o arquivo** e anotar a validade:
   ```bash
   openssl pkcs12 -in cert/<novo>.pfx -noout -info     # pede a senha
   openssl pkcs12 -in cert/<novo>.pfx -nokeys -clcerts | openssl x509 -noout -subject -enddate
   ```
   O `subject` tem de ser o do cliente certo. Num PFX antigo, o OpenSSL 3 pode exigir `-legacy`.
4. **Atualizar `pfxPath` e `passphrase` em todas as ocorrências** do settings. Listar antes e depois, e conferir que a quantidade de linhas trocadas bate:
   ```bash
   grep -n -e pfxPath -e passphrase /opt/suez/config/settings.json
   ```
   No JSON, `"` e `\` na senha precisam de escape.
5. **Reiniciar:** `pm2 restart proxy-suez`, e conferir em `pm2 logs proxy-suez --lines 50` que não apareceu `Error loading certificate`. O restart passa sem erro mesmo com a senha errada: o suez só testa a senha na primeira chamada.
6. **Buscar um token pelo banco** com o bloco de [Simular a busca do token](../proxy-reverso.md#simular-a-busca-do-token), conectado como TF. Só este teste valida a senha.
7. **Registrar a nova validade** no changelog do [proxy-reverso.md](../proxy-reverso.md) e atualizar o alerta de vencimento, quando existir.

## Verificação

- O passo 6 devolve `HTTP 200` com `access_token` no corpo.
- Um boleto do cliente é registrado ou consultado sem erro na tela de boletos.

## Se der errado

- Buscar o sintoma na tabela de [diagnóstico](../proxy-reverso.md#diagnóstico). `Status: 500` com `mac verify failure` quer dizer que o PFX não abre com a senha: voltar ao passo 4 e conferir todas as ocorrências.
- Para voltar ao certificado anterior, enquanto ele não tiver vencido:
  ```bash
  cd /opt/suez/config
  cp settings.json.antes-AAAA-MM-DD settings.json
  pm2 restart proxy-suez
  ```
  Depois, repetir o passo 6.

## Histórico de ajustes

- 2026-11-10: runbook criado a partir de [proxy-reverso.md, §4](../proxy-reverso.md#trocar-o-certificado-do-sicoob), promovido da [lição](../licoes/2026-11-06-senha-do-pfx-em-todas-as-ocorrencias.md) de 2026-11-06. Acrescentados o `chmod 600`, a conferência do `subject`, a do log do pm2 e o caminho de volta.
- 2026-11-05: na troca do certificado do Jornal Repercussão, a senha nova ficou em só uma das duas ocorrências do settings, e a busca do token falhou no dia seguinte. O passo 4 passou a exigir a conferência de todas as ocorrências.
