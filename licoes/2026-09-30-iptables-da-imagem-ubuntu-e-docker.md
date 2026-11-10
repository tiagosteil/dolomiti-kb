---
data: 2026-09-30
area: oci
ocorrencias: 1
---

# A imagem Ubuntu da OCI só abre a porta 22 no `iptables`, e o Docker passa por fora

## Regra
Em VM Ubuntu da OCI, liberar cada porta duas vezes: na security list ou no NSG, e no `iptables` da imagem, antes de instalar o Docker, gravando com `netfilter-persistent save`. Depois do Docker, nunca mais `netfilter-persistent save`: mudança de firewall vai à mão em `/etc/iptables/rules.v4`. Porta publicada pelo Docker não passa pela cadeia `INPUT`, então publicar só em `127.0.0.1` ou no IP privado.

## Contexto
Lição aprendida na ExpertBase, ao montar as VMs Ubuntu de produção na OCI São Paulo (2026-09-16 a 2026-09-30), e trazida para a Dolomiti em 2026-11-10. A Dolomiti usa Ubuntu 24.04 com Docker ([ADR 0003](../decisoes/0003-dev-em-a1-com-o-compose-da-producao.md)).

## O que aconteceu
- A imagem Ubuntu da Oracle traz regras de `iptables` que aceitam a 22 e rejeitam todo o resto, na última linha da cadeia `INPUT`. Com o NSG aberto, o serviço parecia fora do ar.
- Depois do Docker instalado, um `netfilter-persistent save` gravaria as regras do Docker junto com as da imagem.

## Causa raiz
São dois firewalls independentes: o da OCI (security list e NSG) e o do sistema operacional. Já o Docker publica portas por NAT e pela cadeia `FORWARD`, e assim escapa das regras de `INPUT`.

## Como foi resolvido
Na ExpertBase: as regras entram antes do `REJECT` (`iptables -I INPUT 5 ...`), com cópia do `rules.v4` original e `netfilter-persistent save`, tudo antes do Docker. Na Dolomiti, o compose publica o ORDS só em `127.0.0.1` e a 1521 só no IP privado, com o NSG como segunda barreira ([análise, §7](../analise-producao-oci-vm-docker.md#7-o-que-precisa-mudar-em-relação-à-imagem-dos-links)).

## Sinais de alerta
- Porta aberta no NSG que não responde de fora, mas responde de dentro da VM.
- `sudo iptables -S INPUT` com o `REJECT` antes da regra da porta.
- Porta de contêiner acessível de fora mesmo sem regra no `iptables`.

## Onde se aplica
VMs Ubuntu da Dolomiti na OCI. No dev, APEX, ORDS e 1521 ficam só por túnel SSH, então basta a 22, que já vem aberta. Na produção: 80 e 443 na VM de aplicação, 3000 da VM banco para a de aplicação e 1521 da VM de aplicação para a banco.
