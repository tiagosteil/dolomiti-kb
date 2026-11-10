# 0001 — Produção em Oracle Free 26ai, em Docker, em duas VMs na OCI

- **Status:** Proposta — passa a Aceita se o teste de carga nas VMs de produção passar
- **Data:** 2026-11-04
- **Quem decidiu:** Tiago
- **Revisar em:** resultado do teste de carga; depois, a cada gatilho de saída (ver *Como reverter*)

## Contexto

A produção roda numa VM da Locaweb com Oracle XE 11.2.0.2, APEX 20.1 e CentOS, todos sem suporte. Hoje custa R$ 370/mês: R$ 300 da produção e R$ 70 do desenvolvimento em outro provedor (informado por Tiago em 2026-11-04).

O plano anterior ([arquitetura-migracao-oci.md](../arquitetura-migracao-oci.md), §9, de 2026-10-06) era o ATP com VMs auxiliares. Ficou caro para o porte da Dolomiti. A pergunta passou a ser se o banco, o APEX e o ORDS cabem em VMs próprias, pagando só a infraestrutura ([análise](../analise-producao-oci-vm-docker.md)).

Dados da produção em 2026-11-04 e 2026-11-05 ([análise, §4](../analise-producao-oci-vm-docker.md#4-comparação-com-o-ambiente-atual)): owner TF com 1,84 GB, pico de 80 sessões em ~16 meses e XE limitado a 1 CPU e 1 GB.

## Opções consideradas

Preços de lista em BRL, sem impostos, da API do Cost Estimator em 2026-11-03 ([análise, §5.2](../analise-producao-oci-vm-docker.md#52-comparação-das-opções)):

| Opção | R$/mês | Por que perdeu |
|---|---:|---|
| A. ATP + 2 VMs | 2.912 | ~8× o custo de hoje para o mesmo porte |
| B. APEX Service + VM de borda | 779 | Sem SQL*Net: até 5 relatórios do JRI a reescrever e administração só pelo navegador. Fica como **saída** |
| C. Base Database SE + VM de aplicação | ~1.821 | Mais caro que B, e a única vantagem sobre B é manter o JRI e o SQL*Net |
| D. Oracle Free em 2 VMs E4.Flex de 1 OCPU / 6 GB | ~277 | **Escolhida** |
| D′. Oracle Free em 1 VM de 1 OCPU / 8 GB | 144 | Banco sem patches na mesma máquina exposta à internet, disputando 2 vCPUs com ORDS, JRI e proxy |
| D″. Produção em A1 (Always Free) | 0 | A franquia A1 fica com o dev ([ADR 0003](0003-dev-em-a1-com-o-compose-da-producao.md)) e o Free Tier não tem SLA |

O Autonomous Always Free foi descartado: não aceita private endpoint nem restore.

## Decisão

Produção em **Oracle AI Database Free 26ai** com as imagens oficiais da Oracle (`database/free` e `database/ords`), em **duas VMs E4.Flex de 1 OCPU / 6 GB** na OCI São Paulo:

- **VM banco:** sem IP público. A porta 1521 fica aberta só para a VM de aplicação, e os dados ficam num block volume próprio.
- **VM aplicação:** nginx ([ADR 0004](0004-nginx-no-lugar-de-node4ords-e-suez.md)), ORDS com as imagens do APEX e Tomcat com o JRI.

O compose é próprio, não o do projeto de referência (uc-local-apex-dev), que a própria documentação diz não servir para produção ([análise, §7](../analise-producao-oci-vm-docker.md#7-o-que-precisa-mudar-em-relação-à-imagem-dos-links)).

O risco de licença foi aceito à parte, no [ADR 0002](0002-risco-de-licenca-do-free-assumido.md).

## Consequências

### O que fica mais fácil

- Custo de ~R$ 277/mês com o dev incluído, contra R$ 370 hoje.
- Sai do XE 11g, do APEX 20.1 e do CentOS. O Free dá o dobro do teto de hoje: 2 CPUs, 2 GB de RAM e 12 GB de dados.
- Mantém o JRI, o SQL*Net, o SQLcl (inclusive o MCP usado com o Claude) e o Data Pump.
- Duas VMs isolam o banco da internet, separam os picos do JRI do banco e permitem reconstruir a aplicação sem tocar nos dados.

### O que fica mais difícil

- **Nenhum patch do banco, nem de segurança**, e nenhum suporte da Oracle. A proteção principal passa a ser a rede.
- Limites rígidos: com 12 GB de dados a PDB não abre, e não há como passar de 2 CPUs e 2 GB. Na prática, ~9 GB úteis.
- Backup (RMAN, archive log, Data Pump, cópia no Object Storage), restore, atualização de imagens e monitoramento ficam por nossa conta. São 4 a 8 h por mês, mais 80 a 160 h para montar (estimativa da análise, §5.3).
- Sair para uma versão paga só por Data Pump, com janela de parada.
- Continua havendo ponto único de falha: se qualquer VM cair, o sistema para.

## Como reverter

A saída é o **APEX Service** (opção B), ensaiada antes da virada com uma importação do TF num APEX Service Always Free ([análise, §9](../analise-producao-oci-vm-docker.md#9-plano-se-os-critérios-passarem)). Custa reescrever até 5 relatórios Jasper e perder o acesso por SQL*Net.

Gatilhos para sair: teste de carga reprovado mesmo depois de otimizar a aplicação, dados acima de 10 GB, CPU ou memória saturadas, vulnerabilidade crítica sem correção, questionamento da Oracle ou exigência contratual de cliente.

## Fontes

- [analise-producao-oci-vm-docker.md](../analise-producao-oci-vm-docker.md): §1, §3 a §9 (2026-11-03 a 2026-11-10).
- [arquitetura-migracao-oci.md](../arquitetura-migracao-oci.md), §9 e §10: ATP × APEX Service (2026-10-06). Substituída por este ADR como plano; continua valendo como referência de rede, JRI e integrações.
- [FAQ do Oracle AI Database Free](https://www.oracle.com/database/free/faq/) e [API de preços do Cost Estimator (BRL)](https://apexapps.oracle.com/pls/apex/cetools/api/v1/products/?currencyCode=BRL), consultadas em 2026-11-03.
