---
data: 2026-11-05
area: oci
ocorrencias: 1
---

# Desligar a VM pelo sistema operacional não pausa a cobrança

## Regra
Para pausar a cobrança de uma VM da OCI, pará-la pelo console, pela CLI ou pela API, nunca com `shutdown` dentro do sistema operacional.

## Contexto
O plano B do desenvolvimento é uma VM E4.Flex ligada só em horário de trabalho, ~R$ 39/mês por 220 h ([ADR 0003](../decisoes/0003-dev-em-a1-com-o-compose-da-producao.md)). A conta só fecha se a VM ficar parada de verdade fora desse horário.

## O que aconteceu
Achado na análise de 2026-11-05, na documentação da OCI sobre [cobrança de instâncias paradas](https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/resource-billing-stopped-instances.htm).

## Causa raiz
A cobrança acompanha o estado da instância na OCI. Um `shutdown` pelo sistema operacional desliga a máquina por dentro, mas não leva a instância ao estado que pausa a cobrança.

## Como foi resolvido
Preventivamente: o ADR 0003 e a [análise, §6](../analise-producao-oci-vm-docker.md#6-uma-ou-duas-vms) mandam parar pelo console. Um agendamento de liga e desliga, se vier, usa a CLI ou a API.

## Sinais de alerta
- A VM aparece como *Running* no console, mas não responde ao SSH.
- A fatura mostra horas de OCPU nos períodos em que a VM deveria estar parada.

## Onde se aplica
VMs pagas (E4 e outras). A A1 Always Free não tem custo dentro da franquia, mas a regra vale se ela passar dela.
