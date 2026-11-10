---
data: 2026-09-16
area: oci
ocorrencias: 1
---

# Conta OCI: Pay As You Go com cartão físico, e a A1 grátis é 2 OCPU / 12 GB no total

## Regra
Fazer o upgrade da conta OCI para Pay As You Go com cartão de crédito **físico** habilitado para compras internacionais, nunca virtual, pré-pago ou de uso único. Dimensionar a A1 grátis em **2 OCPU / 12 GB no total** da conta, e criar um alerta de orçamento antes de subir qualquer recurso.

## Contexto
Lição aprendida na ExpertBase, outro projeto do Tiago na OCI São Paulo, e trazida para a Dolomiti em 2026-11-10. Em 2026-11-10, a conta da Dolomiti ainda é Free Tier, e o dev usa uma A1 de 2 OCPU / 12 GB ([ADR 0003](../decisoes/0003-dev-em-a1-com-o-compose-da-producao.md)).

## O que aconteceu
No levantamento de 2026-09-16 da ExpertBase:

- A documentação do Always Free passou a dizer 1.500 OCPU-h e 9.000 GB-h por mês, equivalentes a 2 OCPU e 12 GB. As instâncias acima disso foram desligadas em 2026-08-18. A página de preços e o estimador ainda mostravam 3.000 e 18.000.
- Cartão virtual, pré-pago ou de uso único é recusado, e é causa relatada de encerramento de conta por suspeita de fraude.
- Havia relatos de falta de capacidade A1 em São Paulo para conta gratuita.

## Causa raiz
A Oracle cortou a franquia ARM pela metade em 2026 sem atualizar todas as páginas. A conta Free Tier tem menos garantias que a paga: menos prioridade de capacidade, recolhimento de instância ociosa (7 dias abaixo de 20% de CPU, rede e memória) e abandono de conta (30 dias sem login).

## Como foi resolvido
Na ExpertBase: conversão para Pay As You Go com cartão físico e staging dimensionado em 2 OCPU / 12 GB. Na Dolomiti, o upgrade está nos itens em aberto da [análise, §10](../analise-producao-oci-vm-docker.md#10-itens-em-aberto), antes de criar as VMs de produção.

## Sinais de alerta
- Cobrança de A1 na fatura: a conta passou da franquia.
- *Out of host capacity* ao criar a A1. São Paulo tem um único availability domain, então não há outro AD para tentar.
- Cartão recusado no cadastro ou no upgrade.

## Onde se aplica
Conta OCI da Dolomiti: upgrade, VM de dev A1 e qualquer outro recurso A1. Nenhuma fonte garante capacidade A1 em São Paulo, nem em conta paga.
