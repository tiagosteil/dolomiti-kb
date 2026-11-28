# 0012 — A conta OCI que o Tiago já tinha passa a ser a conta da Dolomiti

- **Status:** Proposta. Falta a confirmação explícita do Tiago e a palavra do Chico, porque a conta vai guardar a produção.
- **Data:** 2026-11-27
- **Quem decidiu:** Tiago
- **Revisar em:** antes de criar as VMs da produção, que é o último momento barato para trocar de conta, ou se a contabilidade não aceitar a fatura no nome do Tiago

## Contexto

O dev (A1) e a produção (duas VMs) precisam de uma conta OCI Pay As You Go ([ADR 0001](0001-producao-em-oracle-free-em-duas-vms.md), [ADR 0003](0003-dev-em-a1-com-o-compose-da-producao.md)).

O Tiago tem uma conta Free Tier aberta em 2019-11-29 com o e-mail pessoal dele, e a home region dela é São Paulo. Nela já existem os compartimentos `dolomiti-dev` e `dolomiti-prod` e a VCN `vcn-dev`, criados em 2026-11-10.

O §10 da análise pedia que a nota fiscal saísse com o CNPJ da Dolomiti e que o titular fosse conferido antes do upgrade. Segundo a FAQ de faturamento da Oracle, depois do upgrade qualquer mudança nesses dados passa pelo Suporte de Faturamento.

No upgrade, pedido em 2026-11-27, o cadastro de cobrança perguntou só nome e endereço, e foram usados os do Tiago. O pagamento é feito com o cartão virtual da empresa. A Oracle aprovou em 2026-11-28 como *individual account*, ou seja, conta de pessoa física.

## Opções consideradas

- **Conta nova no nome da Dolomiti**, com e-mail e CNPJ da empresa: o titular fica certo desde o início. O custo é refazer os compartimentos e a VCN, que são poucos e ainda estão vazios, e abrir um cadastro novo com cartão. Perdeu pela praticidade: a conta existente já tem tudo pronto.
- **Manter a conta e pedir ao Suporte de Faturamento a troca dos dados para a Dolomiti:** mantém os recursos e acerta a fatura, mas depende de um chamado. Fica como a saída se a contabilidade precisar.
- **Manter a conta e fazer o upgrade com os dados como estão.** Escolhida.

## Decisão

- A conta (tenancy) que o Tiago abriu em 2019 é a conta da Dolomiti na OCI, com upgrade para Pay As You Go e dados de cobrança no nome do Tiago.
- Os recursos da Dolomiti ficam só nos compartimentos `dolomiti-dev` e `dolomiti-prod`.

## Consequências

### O que fica mais fácil

- Nada a refazer: home region, compartimentos, VCN e o upgrade já pedido continuam valendo.

### O que fica mais difícil

- **Fatura no nome do Tiago:** a despesa da Dolomiti sai em nome de uma pessoa física. Lançá-la na empresa depende do que a contabilidade aceitar, e corrigir depois exige um chamado no Suporte de Faturamento.
- **A conta depende de uma pessoa:** a recuperação de acesso e os avisos de cobrança vão para o e-mail pessoal do Tiago. Sem um usuário próprio do Chico, a produção fica fora do alcance dele se o Tiago estiver indisponível. A fazer antes da produção: criar um usuário administrador para o Chico, com MFA, e mandar os alertas de orçamento também para um e-mail da empresa.
- **Fatura misturada:** recursos pessoais criados desde 2019 fora dos compartimentos da Dolomiti entram na mesma conta. Depois do upgrade, conferir no *Cost Analysis* que só os compartimentos da Dolomiti geram custo.
- **Sócios e titularidade:** se a sociedade mudar, passar a conta para outro titular depende da Oracle, não só de quem administra a conta.

## Como reverter

- **Fatura:** pedir ao Suporte de Faturamento que troque os dados de cobrança para os da Dolomiti. A conta e os recursos continuam os mesmos.
- **Conta:** abrir uma conta da Dolomiti e recriar nela a rede e as VMs a partir do [compose](../compose/README.md) e dos runbooks. Antes da produção isso custa pouco; depois dela, vira uma nova migração.

## Fontes

- [analise-producao-oci-vm-docker.md](../analise-producao-oci-vm-docker.md), §6 "Montagem da VM de desenvolvimento (andamento)" e §10 "Itens em aberto", item *Conta OCI*.
- [FAQ de faturamento da Oracle](https://www.oracle.com/br/corporate/invoicing/faqs/): mudança nos dados de cobrança passa pelo Suporte de Faturamento. A FAQ é a que a análise já citava.
- Console da OCI, *Billing & Cost Management* → *Upgrade and Manage Payment*, consultado em 2026-11-27: *Plan type* Free Tier, *Start date* 2019-11-29, *upgrade in progress*.
