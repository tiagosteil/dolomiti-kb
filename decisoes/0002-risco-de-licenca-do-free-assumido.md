# 0002 — Risco de licença do Oracle Free assumido, sem consulta à Oracle

- **Status:** Aceita
- **Data:** 2026-11-04
- **Quem decidiu:** Tiago
- **Revisar em:** questionamento ou auditoria da Oracle, exigência contratual de cliente, mudança nos Oracle Free Use Terms, ou posição oficial da Oracle sobre o Free nesse cenário

## Contexto

O [ADR 0001](0001-producao-em-oracle-free-em-duas-vms.md) põe a produção no Oracle Free. Os [Oracle Free Use Terms](https://www.oracle.com/downloads/licenses/oracle-free-license.html) permitem o uso para "your own internal business operations", mas não definem o termo.

O documento [Oracle Technology Hosting](https://www.oracle.com/a/ocom/docs/oracle-technology-hosting-1531497.pdf) chama de *hosting* o uso para as operações de terceiros. Ele também descreve o "Proprietary Application Hosting", que é muito parecido com o ERP multiempresa da Dolomiti, usado por clientes pagantes. O documento é de 2012, educativo e não contratual, e trata da licença padrão, não dos Free Use Terms. Não há posição oficial da Oracle sobre o Free nesse cenário, e as consultorias divergem ([análise, §3.1](../analise-producao-oci-vm-docker.md#31-licença-o-maior-risco)).

A dúvida provavelmente já existe hoje, com o XE 11g. O texto da licença do XE não foi verificado.

## Opções consideradas

- **Consultar a Oracle por escrito antes de migrar:** daria uma resposta da própria Oracle. Tiago decidiu não consultar; o motivo não ficou registrado na análise.
- **Usar só serviço de nuvem (APEX Service, ATP ou Base Database):** o contrato de nuvem trata terceiros que usam a aplicação como "Users", o que indica que o modelo é coberto. Custa de R$ 779 a R$ 2.912/mês, contra ~R$ 277 ([ADR 0001](0001-producao-em-oracle-free-em-duas-vms.md)). Fica como saída.
- **Comprar SE2 avulso:** não resolve sozinho, porque o pedido precisa incluir a permissão de hosting, e o custo foge do porte da Dolomiti.
- **Assumir o risco e manter a saída ensaiada:** escolhida.

## Decisão

Tiago decidiu não consultar a Oracle e assumir o risco de licença enquanto a operação estiver no Free. Não há confirmação por escrito.

## Consequências

### O que fica mais fácil

- A migração segue sem esperar resposta da Oracle, e o custo continua o do ADR 0001.

### O que fica mais difícil

- O risco fica aberto enquanto durar a operação no Free: auditoria ou notificação da Oracle, com cobrança retroativa ou migração às pressas.
- O plano de saída para o APEX Service precisa continuar ensaiado e atualizado, ou a reação a uma notificação fica lenta.
- Um cliente que exija licença regular em contrato força a saída.

## Como reverter

Migrar para o APEX Service pelo plano ensaiado no [ADR 0001](0001-producao-em-oracle-free-em-duas-vms.md), ou consultar a Oracle a qualquer momento e seguir a resposta.

## Fontes

- [analise-producao-oci-vm-docker.md](../analise-producao-oci-vm-docker.md), §3.1 e §8, critério 1 (2026-11-04).
- [Oracle Free Use Terms](https://www.oracle.com/downloads/licenses/oracle-free-license.html), [FAQ do Oracle AI Database Free](https://www.oracle.com/database/free/faq/) e [Oracle Technology Hosting](https://www.oracle.com/a/ocom/docs/oracle-technology-hosting-1531497.pdf), consultados de 2026-11-03 a 2026-11-05. Esta análise não é parecer jurídico.
