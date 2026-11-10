# 0011 — Um NSG por VM; as security lists não abrem nenhuma porta

- **Status:** Aceita
- **Data:** 2026-11-10
- **Quem decidiu:** Tiago
- **Revisar em:** ao montar a rede da produção, ou se o IP de quem acessa mudar com frequência (ver OCI Bastion em *Opções consideradas*)

## Contexto

O assistente *Create VCN with Internet Connectivity* cria a VCN com uma security list padrão que abre a porta 22 para `0.0.0.0/0`. A `vcn-dev` nasceu assim em 2026-11-10, e o passo 3 da VM de dev era restringir essa regra ao IP do Tiago.

A produção terá duas VMs com regras diferentes entre elas ([ADR 0001](0001-producao-em-oracle-free-em-duas-vms.md)): 1521 da aplicação para o banco e 3000 do banco para o nginx ([ADR 0004](0004-nginx-no-lugar-de-node4ords-e-suez.md)).

Na OCI, as regras das security lists da subnet e as dos NSGs da VM **se somam**: um pacote passa se qualquer uma delas permitir. Um NSG restrito não fecha o que a security list abre.

## Opções consideradas

- **Security list por subnet:** a mais simples, com um lugar só para editar. Toda VM que entrar na subnet herda as portas abertas, e a origem só pode ser uma faixa de IPs. As regras entre as VMs da produção ficariam presas aos IPs das subnets.
- **OCI Bastion, sem porta 22 aberta para a internet:** não tem custo e dispensa a regra por IP, mas cada sessão é criada no console e dura no máximo 3 h. Fica como complemento, se o IP de quem acessa mudar com frequência.
- **Um NSG por VM, com as security lists sem nenhuma porta de entrada:** é o padrão que a ExpertBase usa em produção desde 2026-09-29. Escolhida.

## Decisão

- **Security lists** das subnets: só ICMP (como o assistente cria) e saída livre. Nenhuma porta de entrada, nem a 22.
- **Um NSG por VM**, com o nome `nsg-<vm>`, ligado na criação da VM. Regras *stateful*.
- **Origem por referência** entre NSGs sempre que a origem for outra VM. IP só para quem vem de fora.
- **IPs de pessoas não entram no repositório:** ficam só no console da OCI, com a descrição da regra dizendo de quem é.

| NSG | Entrada | Origem |
|---|---|---|
| `nsg-vm-dev` | TCP 22 | IP de cada sócio, um `/32` por lugar |
| VM de aplicação (produção) | TCP 80 e 443 | `0.0.0.0/0` |
| | TCP 22 | IP de cada sócio, um `/32` por lugar |
| | TCP 3000 | NSG da VM banco |
| VM banco (produção) | TCP 1521 | NSG da VM de aplicação |
| | TCP 22 | NSG da VM de aplicação (a VM banco não tem IP público) |

Os nomes dos NSGs da produção ficam para o runbook de subida. No dev, APEX, ORDS e a 1521 continuam só por túnel SSH, então basta a 22.

## Consequências

### O que fica mais fácil

- As regras entre as VMs da produção não dependem de IP: se uma VM for recriada, basta ligar o NSG.
- VM nova nasce fechada, até receber um NSG.
- Dev e produção seguem o mesmo modelo ([ADR 0003](0003-dev-em-a1-com-o-compose-da-producao.md)), e um runbook serve para os dois.

### O que fica mais difícil

- **A armadilha da soma:** esquecer uma porta aberta na security list anula o NSG. A cada VCN nova, apagar as regras de entrada que o assistente cria.
- Um objeto a mais por VM para criar e manter.
- Quando o IP de um sócio muda, a regra 22 é editada em cada NSG que a tem (dev e aplicação). Se isso ficar frequente: um NSG `nsg-ssh-equipe` compartilhado entre as VMs, ou o OCI Bastion.
- O `iptables` da imagem Ubuntu continua sendo uma segunda camada a abrir ([lição](../licoes/2026-09-30-iptables-da-imagem-ubuntu-e-docker.md)).

## Como reverter

Recriar as regras de entrada na security list da subnet e desligar os NSGs das VMs. Nada muda dentro das VMs.

## Fontes

- [Regras de segurança da OCI](https://docs.oracle.com/en-us/iaas/Content/Network/Concepts/securityrules.htm) e [Network Security Groups](https://docs.oracle.com/en-us/iaas/Content/Network/Concepts/networksecuritygroups.htm): soma das regras das security lists e dos NSGs, e NSG como origem de regra.
- KB da ExpertBase, `docs/arquitetura.md`, "Regras de rede" (aplicadas em 2026-09-29).
- [analise-producao-oci-vm-docker.md](../analise-producao-oci-vm-docker.md), §6, "Montagem da VM de desenvolvimento" (2026-11-10).
