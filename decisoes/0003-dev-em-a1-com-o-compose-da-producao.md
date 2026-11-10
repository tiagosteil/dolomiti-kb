# 0003 — Desenvolvimento em VM A1 Always Free, com o compose e as imagens da produção

- **Status:** Aceita
- **Data:** 2026-11-05
- **Quem decidiu:** Tiago
- **Revisar em:** primeiro `docker pull` na VM (se as imagens `arm64` não existirem), falta de capacidade A1 em São Paulo, ou recolhimento da instância por ociosidade

## Contexto

O desenvolvimento rodava numa VM de R$ 70/mês em outro provedor, e depois no ADB `DEVDOLOMITI`, que não se parece com a produção do [ADR 0001](0001-producao-em-oracle-free-em-duas-vms.md). A home region é São Paulo, confirmada em 2026-11-05, onde a franquia Always Free inclui VMs A1 (ARM).

## Opções consideradas

- **Continuar no ADB `DEVDOLOMITI`:** é outro produto (Autonomous, com APEX e ORDS gerenciados). Não testa o compose nem a operação da produção. O ADB foi encerrado em 2026-11-10.
- **Usar o projeto de referência (uc-local-apex-dev) como está:** é bom para desenvolvimento, mas relaxa a segurança e difere da produção em portas, segredos, archive log e backup ([análise, §2](../analise-producao-oci-vm-docker.md#2-o-que-os-links-entregam)). Fica só como referência de configuração.
- **VM E4.Flex de 1 OCPU / 6 GB ligada em horário de trabalho:** ~R$ 39/mês por 220 h, x86 como a produção. Fica como **plano B**.
- **VM A1.Flex de 2 OCPU / 12 GB com o mesmo compose e as mesmas imagens da produção:** R$ 0. Escolhida.

## Decisão

O desenvolvimento roda numa VM **A1.Flex de 2 OCPU / 12 GB (Always Free)**, com Ubuntu 24.04, no compartimento `dolomiti-dev`, numa VCN própria (`vcn-dev`, `10.1.0.0/16`) que não enxerga a da produção. Usa **o mesmo compose e as mesmas imagens da produção**.

As únicas diferenças devem ser as intencionais: jobs desligados, sem ACL de SMTP, integrações apontando para a homologação dos bancos e acesso restrito ou dados mascarados.

## Consequências

### O que fica mais fácil

- Custo de R$ 0 no lugar de R$ 70/mês.
- O compose, as imagens, o backup e o restore da produção são ensaiados no dev antes da virada.

### O que fica mais difícil

- **ARM no dev e x86 na produção:** os relatórios do JRI, principalmente as fontes, precisam de teste final em x86.
- **O dev não mede desempenho:** a A1 tem 2 núcleos inteiros e roda banco e aplicação juntos. O teste de carga é feito nas VMs de produção.
- **Imagens `arm64` não confirmadas:** o registro da Oracle exige login, e só o primeiro `docker pull` responde.
- **Capacidade e recolhimento:** a A1 pode faltar em São Paulo (um único availability domain), e, enquanto a conta for Free Tier, a Oracle pode recolher instância Always Free ociosa; na conta paga, não ([lição](../licoes/2026-09-16-conta-oci-paga-e-franquia-a1.md)). O ambiente precisa ser reproduzível.
- **Dados reais:** se o dev receber uma cópia do TF, mascarar os dados ou manter a VM sem acesso público.

## Como reverter

Plano B: VM E4.Flex de 1 OCPU / 6 GB, parada fora do horário de trabalho. A cobrança só pausa se a VM for parada pelo console. O compose é o mesmo, então a troca é só de shape.

## Fontes

- [analise-producao-oci-vm-docker.md](../analise-producao-oci-vm-docker.md), §6, "Ambiente de desenvolvimento" e "Montagem da VM de desenvolvimento" (2026-11-05 e 2026-11-10).
- [Recursos Always Free](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm) e [cobrança de instâncias paradas](https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/resource-billing-stopped-instances.htm), consultados de 2026-11-03 a 2026-11-05.
