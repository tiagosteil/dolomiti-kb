---
data: 2026-11-06
area: integracoes-bancarias
ocorrencias: 1
---

# Senha do PFX trocada em só uma das ocorrências do settings do suez

## Regra
Ao trocar o PFX do Sicoob, atualizar `pfxPath` e `passphrase` em todas as ocorrências do settings do suez (`grep -n -e pfxPath -e passphrase`) e validar buscando um token pelo banco. `mac verify failure` quer dizer que o PFX não abre com a senha.

## Contexto
O suez faz o mTLS de saída para o Sicoob na produção. Cada destino com mTLS tem o seu bloco no `settings.json`, com o caminho do PFX e a senha. Em 2026-11-06, o settings do servidor tinha a senha em dois lugares. Quais destinos usam mTLS ainda está por conferir no servidor ([proxy-reverso.md, §3](../proxy-reverso.md#3-suez-saída)).

## O que aconteceu
O certificado do Jornal Repercussão foi trocado em 2026-11-05. A senha nova foi colocada em só um dos dois lugares do settings. Em 2026-11-06, a busca do token passou a falhar com `ORA-20001 ... Erro HTTP ao buscar token Sicoob. Status: 500`, com `Error: mac verify failure` no corpo, e o erro apareceu para o cliente na tela de boletos.

## Causa raiz
A senha do PFX fica repetida em mais de um bloco do settings do suez. Trocar um lugar só deixa o outro com a senha antiga. E o erro não aparece na troca: o suez lê o PFX na subida, mas só testa a senha na primeira chamada, então o `pm2 restart` passa sem erro mesmo com a senha errada.

## Como foi resolvido
A senha foi trocada nos dois lugares e o suez reiniciado. O procedimento de troca, com o `grep` e o teste do token, está em [proxy-reverso.md, §4](../proxy-reverso.md#trocar-o-certificado-do-sicoob). Na OCI, o nginx guarda cada senha num único arquivo ([ADR 0004](../decisoes/0004-nginx-no-lugar-de-node4ords-e-suez.md)).

## Sinais de alerta
- `Status: 500` com `mac verify failure` na busca do token.
- Restart do suez sem erro não prova nada: só a busca do token valida a senha.
- Erro de boleto na tela do cliente logo depois de uma troca de certificado.

## Onde se aplica
Toda troca de certificado de cliente no suez, enquanto a produção estiver na Locaweb. No nginx, a mesma ideia vale para o arquivo `.pass` de cada certificado.
