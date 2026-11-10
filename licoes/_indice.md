# Lições ativas

Regras aprendidas na operação. Carregado em toda sessão pelo `CLAUDE.md`: manter **curto** (até ~40 linhas). Formato: `- **regra** — [detalhe](arquivo.md) (AAAA-MM-DD)`, numa seção por área (OCI, Oracle, APEX e ORDS, Docker, nginx, Integrações bancárias, JRI). A seção nasce com a primeira lição da área.

Passou do limite: consolidar lições parecidas, promover as maduras para o `CLAUDE.md` ou para um runbook, e retirar daqui.

## OCI

- **Upgrade da conta para Pay As You Go só com cartão de crédito físico internacional (nunca virtual ou pré-pago); a A1 grátis é 2 OCPU / 12 GB no total da conta; alerta de orçamento antes de subir recursos** — conta Free Tier tem menos capacidade A1 e sofre recolhimento por ociosidade — [lição](2026-09-16-conta-oci-paga-e-franquia-a1.md) (2026-09-16, ExpertBase)
- **Em VM Ubuntu da OCI, liberar cada porta no NSG e no `iptables` da imagem (só a 22 vem aberta), antes do Docker; depois dele, nunca `netfilter-persistent save`; porta publicada pelo Docker passa por fora do `INPUT`, então publicar só em `127.0.0.1` ou no IP privado** — [lição](2026-09-30-iptables-da-imagem-ubuntu-e-docker.md) (2026-09-30, ExpertBase)
- **Para pausar a cobrança, parar a VM pelo console, CLI ou API, nunca com `shutdown` no sistema operacional** — [lição](2026-11-05-parar-a-vm-pelo-console.md) (2026-11-05)

## Oracle

- **Antes de levar código do 11g para o 21c ou mais novo, procurar no `dba_source` os recursos removidos (`dbms_obfuscation_toolkit`, `wm_concat`) e tratar cada um antes do import; senha só com `DBMS_CRYPTO` e salt por usuário, nunca `APEX_UTIL.GET_HASH`** — [lição](2026-11-10-recursos-removidos-no-21c.md) (2026-11-10)

## Docker

- **No compose do banco, `TZ=America/Sao_Paulo`, e conferir `select sysdate from dual` logo depois de subir** — o contêiner vem em UTC, e a produção roda no horário de Brasília — [lição](2026-11-05-conteiner-oracle-vem-em-utc.md) (2026-11-05)
- **No contêiner, `localhost` é o próprio contêiner: o banco chama o proxy pelos nomes `*.localhost`, apontados por `extra_hosts` para o IP privado da VM de aplicação** — [lição](2026-11-05-localhost-no-conteiner-e-o-proprio-conteiner.md) (2026-11-05)

## Integrações bancárias

- **Ao trocar o PFX do Sicoob, atualizar a senha em todas as ocorrências do settings do suez e validar buscando um token pelo banco; `mac verify failure` = o PFX não abre com a senha, e o restart passa mesmo com a senha errada** — [lição](2026-11-06-senha-do-pfx-em-todas-as-ocorrencias.md) (2026-11-06)
