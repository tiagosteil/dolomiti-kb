# Análise: produção em VM na OCI com Oracle Free em Docker

> **Status:** decisão em andamento: seguir com Oracle Free em 2 VMs, condicionada ao teste de carga (§8): [ADR 0001](decisoes/0001-producao-em-oracle-free-em-duas-vms.md). Nada foi provisionado.
> **Última atualização:** 2026-11-10
> **Complementa:** [arquitetura-migracao-oci.md](arquitetura-migracao-oci.md), cujo desenho com ATP deixa de ser o plano se o teste de carga passar.

Pergunta: dá para trocar os serviços gerenciados por uma ou duas VMs Linux na OCI Brasil, com banco, APEX e ORDS em Docker, pagando só a infraestrutura?

---

## 1. Conclusão

**Com os dados reais, a proposta fica viável: ~R$ 277/mês para produção e desenvolvimento, contra R$ 370/mês hoje. Falta o teste de carga, e a produção deve usar as imagens oficiais da Oracle com compose próprio, não o projeto dos links.**

- **Decisão (2026-11-04):** Tiago decidiu não consultar a Oracle e assumir o risco de licença (§3.1, [ADR 0002](decisoes/0002-risco-de-licenca-do-free-assumido.md)).
- **Espaço:** o Free atende com folga. O owner TF tem 1,84 GB, cerca de 20% dos ~9 GB úteis, e deve chegar ao destino com ~1 GB sem as cópias de PDF no log (§4).
- **Carga:** provavelmente atende. O XE roda hoje com 1 CPU e 1 GB, o Free permite o dobro, e o pico de 80 sessões cobre ~16 meses. O 26ai tende a consumir mais, então é preciso testar (§4).
- **Custo:** a economia sobre hoje é de ~R$ 93/mês, em preços de lista sem impostos. Ela não paga o trabalho de migrar: o ganho real é sair de um banco e de um sistema operacional muito antigos (§5).
- **Riscos que continuam:** sem patches, sem suporte e licença não confirmada (§3).
- **Import só do TF:** é uma boa escolha. O inventário de 2026-11-05 e a terceira rodada, de 2026-11-10, mostraram o que fica fora do schema: a aplicação APEX, o contexto `CTX`, grants, ACLs e um módulo REST. Os owners `APEXREP` e `DOLOMITI` ficam para trás ([importação](migracao-oci-importacao-tf.md)).
- **Achados do inventário** ([importação, §3](migracao-oci-importacao-tf.md)):
  - O TF tem a role `DBA`.
  - O login usa o MD5 do `DBMS_OBFUSCATION_TOOLKIT`, que não existe no 26ai: as senhas serão redefinidas com hash novo.
  - Os logs `LTF_` guardam ~840 MB de cópias de PDFs, que saem por patch na produção antes do export.
  - O e-mail por SMTP não migra.
- **Saída:** o APEX Service (R$ 779/mês) ficou mais acessível, porque há no máximo 5 relatórios Jasper para reescrever (§5.2).

### Recomendação

1. **Produção:** 2 VMs E4.Flex de 1 OCPU / 6 GB, com o banco sem IP público (§6 e §7).
2. **Desenvolvimento:** VM A1 Always Free com o mesmo compose e as mesmas imagens da produção (§6).
3. **Antes de importar:** aplicar na produção o patch que tira os PDFs do log ([importação, §8](migracao-oci-importacao-tf.md)) e fazer o upgrade da conta OCI (§10).
4. **Antes da virada:** teste de carga nas VMs de produção, teste de restore e ensaio da saída para o APEX Service (§9).
5. **Se o teste de carga falhar:** otimizar a aplicação. Se não bastar, migrar para o APEX Service, porque o Free não escala além de 2 CPUs e 2 GB.

---

## 2. O que os links entregam

O [artigo do One Oracle Developer](https://www.oneoracledeveloper.com/2026/06/apex-261-docker-images-for-your-local.html) apenas lista opções para **ambiente local**. A principal delas é o [uc-local-apex-dev](https://www.united-codes.com/products/uc-local-apex-dev/docs/), da United Codes.

| Componente | O que o projeto usa (branch `26-4`) | Licença |
|---|---|---|
| Banco | `container-registry.oracle.com/database/free:23.26.3.0` (nome comercial: 26ai Free) | Oracle Free Use Terms (§3.1) |
| ORDS | `container-registry.oracle.com/database/ords:26.3.0` | Sem custo; termos da imagem a confirmar |
| APEX | Instalado por script a partir do `apex-latest.zip` | Sem custo; termos a confirmar para o nosso uso |
| Scripts | Bash e compose da United Codes | MIT, que cobre só os scripts, não o software Oracle |

A documentação é direta sobre produção:

> "Never host this as a production database."
> "It is insecure by design. It stores the passwords in plain text and relaxes all security features."
> "Use it as a test database only."

O modo `--secure` também não torna o ambiente próprio para produção. Ele desliga a Database REST API, o SQL Developer Web e o debug na tela, mas, segundo a documentação, **não fecha portas e não protege os segredos do `.env`**. O guia de HTTPS traz o aviso "Not a hardening guide".

Conferido no repositório:

- O compose publica `1521`, `8181` e `8443` e usa `restart: no` por padrão.
- O script de pós-instalação desliga a expiração de senha e oferece desligar o archive log.
- O backup é só Data Pump, cobre os schemas criados pelo `create-user` e não tem RMAN nem recuperação até um ponto no tempo.

**Leitura:** é um ótimo ambiente de desenvolvimento e uma boa referência de configuração. A base de produção é montada à parte (§7).

---

## 3. O que pesa contra o Oracle Free em produção

A Oracle não proíbe o Free em produção pelo tipo de ambiente. O [FAQ oficial](https://www.oracle.com/database/free/faq/) diz:

> "Oracle AI Database Free does not restrict the environment in which it can be deployed. However, Oracle AI Database Free is not supported and does not receive any patches, including security patches. Oracle recommends running production deployments on fully supported Oracle AI Database editions or cloud services."

A proposta está certa em um ponto: **não há taxa de licença**. Os problemas estão abaixo.

### 3.1 Licença: o maior risco

Os [Oracle Free Use Terms](https://www.oracle.com/downloads/licenses/oracle-free-license.html) concedem o direito de:

> "internally use the unmodified Programs for the purposes of developing, testing, prototyping and demonstrating your applications, and running the Programs for your own internal business operations"

O termo não define "internal business operations". O documento [Oracle Technology Hosting](https://www.oracle.com/a/ocom/docs/oracle-technology-hosting-1531497.pdf) explica como a Oracle entende esse conceito:

> "When the licensed programs are used for the internal business operations of a third party, Oracle classifies this type of activity as hosting."

> "Proprietary Application Hosting: Companies that own and develop a commercially available application that is available to multiple end users and operates with an embedded Oracle program."

Pela KB, a Dolomiti desenvolve um ERP próprio, multitenant, usado por clientes pagantes ([analise-integracao-nfse.md](analise-integracao-nfse.md)). É muito parecido com essa descrição.

- **Ressalvas:** o documento é de 2012, tem caráter educativo, não é contrato e fala da licença padrão, não dos Free Use Terms. Não encontrei posição oficial da Oracle sobre o Free nesse cenário, e consultorias divergem. Esta análise também não é parecer jurídico.
- **Risco prático:** auditoria ou notificação da Oracle, com cobrança retroativa ou migração às pressas.
- **Comprar SE2 avulso não resolve sozinho:** o mesmo documento diz que o pedido de compra precisa incluir a permissão de hosting.
- **Serviços de nuvem:** a redação antiga do contrato de nuvem da Oracle trata terceiros que interagem com a aplicação como "Users", o que indica que ATP, APEX Service e Base Database comportam esse modelo. Não li a versão vigente do contrato.

> **Decisão (2026-11-04):** Tiago decidiu não consultar a Oracle e assumir este risco: [ADR 0002](decisoes/0002-risco-de-licenca-do-free-assumido.md).

### 3.2 Sem patches e sem suporte

| Item | Situação no Free |
|---|---|
| Patches do banco | Nenhum, nem de segurança (FAQ da Oracle) |
| Chamado na Oracle | Não pode; só fórum |
| Nova versão do banco | A Oracle publica imagens novas (ex.: 23.26.2 → 23.26.3), sem compromisso de correção. O dicionário de dados não é atualizado sozinho. O projeto da United Codes resolve isso com script próprio, ou seja, procedimento comunitário |
| Patch Set do APEX | Exige conta de suporte válida, segundo o FAQ da United Codes. Sem ela, só versões completas. Não confirmei se a conta OCI paga libera o download |
| ORDS, Linux, Docker, nginx, Node, Tomcat | Atualizáveis normalmente, por nossa conta |

Como o banco fica sem patches, a principal proteção passa a ser a rede: **banco sem IP público e porta 1521 acessível só pela VM de aplicação**. A LGPD também pesa, porque o banco guarda dados pessoais e fiscais dos clientes. Contratos com clientes podem trazer exigências próprias de segurança.

### 3.3 Limites rígidos

| Recurso | Limite | O que acontece |
|---|---|---|
| Dados | 12 GB | Erro ORA-12954. Segundo a United Codes, o limite vale para os datafiles da PDB, e a PDB **não abre** ao ultrapassá-lo: é parada total |
| RAM | 2 GB (SGA + PGA) | Memória adicional da VM não é usada pelo banco |
| CPU | 2 para processos de primeiro plano | Sem escala |
| Instalação | 1 por host, VM ou contêiner | ORA-00442 |
| Alta disponibilidade | Sem Data Guard | O SE2 também não tem |

- **Espaço útil:** como APEX, auditoria e undo ocupam espaço, considerar **cerca de 9 GB para a aplicação** (estimativa minha, a medir em homologação).
- **Saída para versão paga:** só por Data Pump, com janela de parada. A Oracle informa que plugar uma PDB do Free em EE/SE2 não é suportado.
- **Pontos positivos:** o [guia de licenciamento](https://docs.oracle.com/en/database/oracle/oracle-database/26/dblic/Licensing-Information.html) indica RMAN com compressão e criptografia, Flashback, TDE e Diagnostics/Tuning Pack incluídos no Free. Backup paralelo não está incluído. O Free também está disponível para Linux ARM.

---

## 4. Comparação com o ambiente atual

Confirmado pelo levantamento na produção: **Oracle Database 11g Express Edition 11.2.0.2.0**, com APEX 20.1.

| | [XE 11g](https://www.oracle.com/database/technologies/database-11g-express-edition.html) (hoje) | Free 26ai |
|---|---|---|
| Dados | 11 GB | 12 GB |
| RAM | 1 GB | 2 GB |
| CPU | 1 | 2 |
| Suporte | Fórum | Fórum |
| APEX | 20.1 | 26.1 |
| Charset | AL32UTF8 | AL32UTF8 (padrão; conferir na criação) |

### Dados reais da produção

| Medida | Valor | Leitura |
|---|---|---|
| Owner TF | 1,84 GB | ~20% dos 9 GB úteis |
| 4 maiores LOBs do TF | 1,41 GB | PDFs de boleto e DANFEs; ~930 MB são cópias nas tabelas de log `LTF_` |
| Tablespace `TS_LOG` | 0,46 GB | Candidato a limpeza antes da exportação |
| Três versões do APEX (4.0, 19.1 e 20.1) | 0,99 GB | Ficam para trás no import só do TF |
| Banco inteiro | 4,03 GB | Inclui dicionário e APEX |
| Pico de sessões | 80 de 172 | Desde o último restart, em 2025-07-16 (~16 meses) |
| Pico de processos | 66 de 100 | Idem |
| Memória (`memory_target`) | 1 GB | Teto do XE |
| CPUs da VM (`cpu_count`) | 4 | O XE só usa 1; o restante atende o que mais roda na VM |

**Leitura:**

- **Espaço passa com folga.** Mesmo dobrando a cada 2 anos, o TF chega a ~7,4 GB em 4 anos. Medido em 2026-11-10: os PDFs de boleto crescem ~90 MB/ano, e as cópias no log saem por patch ([importação, §7](migracao-oci-importacao-tf.md)).
- **Carga é provável, mas não garantida.** O Free dá o dobro do teto atual, mas o 26ai tem mais processos e usa uma arquitetura CDB + PDB, e APEX e ORDS são mais novos. O pico, por outro lado, é representativo: cobre ~16 meses.
- **O Free reduz o risco técnico atual**, mesmo sem patches futuros, porque o banco sai de uma versão muito antiga.
- **A dúvida de licença provavelmente já existe hoje.** Não verifiquei o texto da licença do XE 11g.

---

## 5. Custos

Premissas: preços de lista em BRL da [API do Cost Estimator](https://apexapps.oracle.com/pls/apex/cetools/api/v1/products/?currencyCode=BRL), consultada em 2026-11-03, 744 h/mês, **sem impostos**. Os preços de ATP, APEX Service e E4 usados no documento de arquitetura não mudaram desde 2026-10-06.

**Base de comparação (informada por Tiago em 2026-11-04):** R$ 300/mês da VM de produção na Locaweb + R$ 70/mês da VM de desenvolvimento em outro provedor = **R$ 370/mês**.

### 5.1 Proposta: Oracle Free com 2 VMs

| Item | Configuração | R$/mês |
|---|---|---:|
| VM banco | E4.Flex, 1 OCPU / 6 GB | 132,44 |
| VM aplicação | E4.Flex, 1 OCPU / 6 GB | 132,44 |
| VM desenvolvimento | A1.Flex, 2 OCPU / 12 GB (Always Free) | 0,00 |
| Discos | 3 boots de 50 GB + 50 GB de dados | 0,00 (franquia de 200 GB) |
| Backup no Object Storage | 100 GB (estimativa) | 12,02 |
| VCN, gateways, Bastion, saída até 10 TB | | 0,00 |
| **Total** | | **276,90** |

**Dimensionamento:** as duas VMs somam 4 vCPUs, o mesmo total da VM de hoje. A VM banco cobre o teto do Free com folga de memória para sistema e contêiner. A VM aplicação comporta ORDS, JRI com poucos relatórios e nginx. Como os shapes são flexíveis, dá para aumentar depois: **+1 OCPU = +R$ 97,38/mês** e **+1 GB = +R$ 5,84/mês**.

**Cuidados:**

- ✅ **Home region:** São Paulo, confirmada por Tiago em 2026-11-05. A franquia de disco e a A1 grátis só valem nela. A conta ainda é Free Tier e precisa do upgrade para Pay As You Go antes de criar as VMs E4 (§10).
- **Backup das VMs:** a franquia inclui [5 backups de volume](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm), somando boot e bloco. Acima disso, o armazenamento é cobrado e não está no total; medir na primeira fatura.
- **Impostos:** a conta empata com os R$ 370 de hoje se os impostos somarem ~34%.
- **WAF:** se decidirem usar, não está incluído.

**Variantes:**

- **1 VM de 1 OCPU / 8 GB:** R$ 144,13, cerca de R$ 121/mês a menos. Banco, ORDS, JRI e Node dividiriam 2 vCPUs, com o banco sem patches na máquina exposta à internet. Não recomendo.
- **Produção em A1:** a franquia grátis já fica com o dev, e a [documentação do Always Free](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm) cita 1.500 OCPU-h e 9.000 GB-h, enquanto o estimador ainda mostra 3.000 e 18.000. Além disso, o [Free Tier não tem SLA](https://www.oracle.com/cloud/free/faq/). Não recomendo como ponto de partida.

### 5.2 Comparação das opções

| | Hoje (Locaweb + dev) | A. ATP + 2 VMs | B. APEX Service + VM de borda | C. Base Database SE + VM aplicação | D. Oracle Free em 2 VMs (decisão) |
|---|---|---|---|---|---|
| **R$/mês** | **370** | **2.912** | **779** | **~1.821** | **~277** |
| **R$/ano** | 4.440 | 34.949 | 9.352 | 21.854 | 3.323 |
| Diferença/ano sobre hoje | | +30.509 | +4.912 | +17.414 | −1.117 |
| Licença para ERP hospedado | Dúvida (XE) | Serviço de nuvem | Serviço de nuvem | Serviço de nuvem | **Risco assumido (§3.1)** |
| Patches de segurança | Nenhum | Automáticos | Automáticos | Disponíveis; aplicados por nós | **Nenhum** |
| Suporte Oracle | Não | Sim | Sim | Sim | **Não** |
| Limite de dados | 11 GB | Pago por uso | Pago por uso | Conforme o storage | **12 GB** |
| JRI e SQL*Net | Sim | Sim | **Não** | Sim | Sim |
| Backup | Por nossa conta | Gerenciado | Gerenciado | Configurado por nós no console | **Por nossa conta** |
| ORDS e APEX | Por nossa conta | Gerenciados | Gerenciados | Por nossa conta | Por nossa conta |
| Esforço de operação | Atual | Baixo | Baixo | Médio | **Parecido com o atual** |
| Esforço de migração | | Em andamento | Reimportar e **reescrever até 5 relatórios** | Reimportar | Reimportar e montar tudo |

As opções A, B e C também podem usar a VM de desenvolvimento gratuita em A1, sem custo adicional.

Composição da opção C: mínimo de 4 ECPU (R$ 1.229,38), 712 GB de storage (R$ 447,34), VM aplicação (R$ 132,44) e backup (R$ 12,02). ⚠️ Assumi que os 712 GB mínimos da [documentação](https://docs.oracle.com/en/cloud/paas/base-database/about-dbs) são cobrados integralmente. Confirmar no estimador, caso a opção volte a ser considerada.

**Como ler a tabela:**

- **D é a única opção que reduz o custo de hoje.** Todas as outras aumentam a conta.
- **B é a saída natural.** Custa ~R$ 502/mês a mais que D (~R$ 6 mil/ano) e traz patches automáticos, suporte, backup gerenciado e contrato de nuvem. A reescrita ficou pequena, com até 5 relatórios. A perda continua sendo o acesso por SQLcl e SQL Developer desktop (§9 do documento de arquitetura).
- **C e A deixam de fazer sentido para este porte**, porque custam muito mais que B e D. A única vantagem real sobre B é manter JRI e SQL*Net.
- **O Autonomous Always Free não serve para produção:** a [versão gratuita](https://docs.oracle.com/iaas/autonomous-database-shared/doc/autonomous-always-free.html) não aceita private endpoint nem restore e suporta só 3 a 6 usuários simultâneos pela interface HTTP.

### 5.3 O custo que não aparece na fatura

Estimativas minhas, para substituir pelos números reais:

| Trabalho | Horas |
|---|---|
| Montar, endurecer, migrar e testar (uma vez) | 80 a 160 h |
| Operação mensal: backups, atualizações, monitoramento | 4 a 8 h |
| Incidente, atualização de versão ou migração por limite | Sem previsão |

A economia de R$ 93/mês **não paga esse trabalho**. A justificativa para migrar é outra: sair do XE 11.2.0.2, do APEX 20.1 e do CentOS sem suporte. A operação em si não é custo novo, porque banco, APEX e proxy já são operados em VM própria. O que aumenta é a disciplina de backup, restore e atualização de imagens.

### 5.4 Pagamento em reais

A [FAQ de faturamento da Oracle Brasil](https://www.oracle.com/br/corporate/invoicing/faqs/) confirma nota fiscal no Brasil, Pay As You Go cobrado no fim do mês pelo uso real e pagamento líquido em 30 dias. Não encontrei fonte oficial atual sobre dois pontos, que vale confirmar: **a carga de impostos sobre a nota** e **se a tabela em BRL acompanha o câmbio**.

---

## 6. Uma ou duas VMs

**Recomendo duas.** Com 1 OCPU em cada, custam R$ 264,88, o mesmo que uma única VM de 2 OCPU / 12 GB, e trazem três ganhos:

1. **Isolamento:** um banco sem patches não fica na mesma máquina exposta à internet. Se o nginx, o Node ou o ORDS forem comprometidos, o banco continua em outro host.
2. **Recursos:** picos de relatório do JRI não disputam memória e CPU com o banco.
3. **Manutenção:** dá para atualizar ou reconstruir a VM de aplicação sem tocar nos dados.

Continua existindo ponto único de falha, assim como hoje: se qualquer uma das VMs cair, o sistema para.

```
Internet
   │ 443
┌──────────────────── VCN 10.0.0.0/16 ─────────────────────┐
│  Subnet pública 10.0.1.0/24     Subnet privada 10.0.2.0/24│
│  ┌────────────────────────┐ 1521 ┌─────────────────────┐ │
│  │ VM aplicação           │─────►│ VM banco            │ │
│  │ nginx                  │      │ (sem IP público)    │ │
│  │ ORDS + imagens APEX    │ HTTP │ Docker: Oracle Free │ │
│  │ Tomcat + JRI           │◄─────│ PDB FREEPDB1        │ │
│  │ mTLS de saída Sicoob   │      │ Block volume próprio│ │
│  └────────────────────────┘      └──────────┬──────────┘ │
│                                             │ NAT GW     │
└─────────────────────────────────────────────┼────────────┘
                                              ▼ Sicredi e demais saídas
```

### Impacto no documento de arquitetura

| Item | O que acontece |
|---|---|
| VCN, subnets, NAT, NSGs, Bastion | Mantidos |
| Proxy reverso (node4ords e suez), TLS, mTLS do Sicoob, estáticos | Passam para o nginx na VM de aplicação. Os apps Node não migram ([proxy-reverso.md](proxy-reverso.md)) |
| Site institucional | Migra para a VM de aplicação ([site-institucional.md](site-institucional.md)) |
| JRI 2.11.0 + Jasper 6.20.6 | Mantido, agora na VM de aplicação |
| Wallet do JRI | Sai. Passa a usar `jdbc:oracle:thin:@//<IP privado>:1521/FREEPDB1` |
| ORDS e APEX gerenciados | Passam a ser nossos: instalação, atualização e imagens `/i/` |
| ACLs de rede | Continuam obrigatórias |
| Chamadas para `localhost` | Precisam mudar: no contêiner, `localhost` é o próprio contêiner. Usar o IP privado da VM de aplicação, como o documento já prevê |

### Ambiente de desenvolvimento

A VM A1 Always Free (2 OCPU / 12 GB) substitui a VM de R$ 70/mês por **R$ 0**.

> **Decisão (2026-11-05):** o dev roda o Oracle Free em Docker com o **mesmo compose e as mesmas imagens da produção**: [ADR 0003](decisoes/0003-dev-em-a1-com-o-compose-da-producao.md).

As diferenças em relação à produção devem ser só as intencionais: jobs desligados, sem ACL de SMTP, integrações apontando para a homologação dos bancos e acesso restrito ou dados mascarados ([importação](migracao-oci-importacao-tf.md)).

- **Imagens ARM:** o Oracle Free existe para Linux ARM, mas não consegui confirmar as imagens `arm64` do contêiner, porque o registro exige login. O primeiro `docker pull` na VM responde. O teste de capacidade em São Paulo acontece na mesma hora.
- **Plano B:** E4.Flex de 1 OCPU / 6 GB ligada só em horário de trabalho. A cobrança [pausa com a instância parada](https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/resource-billing-stopped-instances.htm), e 220 h/mês custam ~R$ 39. Parar pelo console, porque desligar pelo sistema operacional não pausa a cobrança.
- **Diferença de arquitetura:** com dev em ARM e produção em x86, os relatórios do JRI precisam de teste final em x86, principalmente fontes. O dev também não serve para medir desempenho: a A1 tem 2 núcleos inteiros e roda banco e aplicação na mesma VM. O teste de carga é feito nas VMs de produção, antes da virada.
- **Dados reais:** o projeto avisa "Do not use this environment for production data". Se o dev receber uma cópia do TF, mascarar os dados ou manter a VM sem acesso público, só por Bastion ou VPN.
- **Isolamento:** sem rota para a porta 1521 da produção, com jobs desligados e integrações apontando para homologação dos bancos.
- **Recolhimento:** a Oracle pode recolher instâncias Always Free ociosas. O critério exige CPU, rede e memória abaixo de 20% em 7 dias, e o banco com ORDS tende a manter a memória acima disso. Na conta Pay As You Go o recolhimento não se aplica ([lição](licoes/2026-09-16-conta-oci-paga-e-franquia-a1.md)). Mesmo assim, manter o ambiente reproduzível.

### Montagem da VM de desenvolvimento (andamento)

Escolhas (2026-11-10):
- **Rede própria:** VCN `vcn-dev`, `10.1.0.0/16`, no compartimento `dolomiti-dev`. A produção vai usar `10.0.0.0/16` no `dolomiti-prod`, e as redes não se enxergam.
- **Sistema:** Ubuntu 24.04, porque o Docker tem suporte oficial nele em ARM e em x86. O Oracle Linux não está na lista oficial do Docker.
- **Acesso:** só SSH por chave, com a porta 22 liberada para o IP do Tiago (`/32`). APEX, ORDS e a porta 1521 ficam acessíveis só por túnel SSH. Se o IP mudar com frequência, passar para o OCI Bastion.

| # | Passo | Situação |
|---|---|---|
| 1 | Compartimentos `dolomiti-dev` e `dolomiti-prod` | ✅ 2026-11-10 |
| 2 | VCN `vcn-dev` pelo assistente *Create VCN with Internet Connectivity*, com subnets pública e privada | ✅ 2026-11-10 |
| 3 | Na *default security list for vcn-dev*, trocar a origem da regra da porta 22 de `0.0.0.0/0` para o IP do Tiago com `/32` | ⏸️ **Parado aqui** (2026-11-10). Ao retomar, conferir o IP atual com `curl -4 ifconfig.me` |
| 4 | VM `vm-dev`: A1.Flex com 2 OCPU e 12 GB, Ubuntu 24.04, subnet pública com IPv4 público, chave SSH ed25519 e boot de 50 GB | Pendente |
| 5 | Testar `ssh ubuntu@<IP público>` | Pendente |
| 6 | Instalar o Docker e baixar as imagens do Oracle Free e do ORDS para ARM, o que confirma se as imagens `arm64` existem | Pendente |

Os passos são feitos um por vez, conferindo o resultado antes do próximo.

---

## 7. O que precisa mudar em relação à imagem dos links

Na produção, usar as mesmas imagens oficiais da Oracle, com compose próprio:

| Tema | No projeto dos links | Em produção |
|---|---|---|
| Portas | `1521`, `8181` e `8443` publicadas | ORDS só em `127.0.0.1`; `1521` só no IP privado; NSG como segunda barreira. Portas publicadas pelo Docker podem passar por fora do firewall do host |
| Segredos | `.env` em texto puro | Arquivos com acesso restrito ou OCI Vault; senhas diferentes para SYS, APEX e ORDS |
| Senhas | Sem expiração; regras do APEX relaxadas | Perfis e regras reativados |
| ORDS | Debug e REST API ligados por padrão | Desligados |
| Pool do ORDS | Padrão | Limitar conexões (`jdbc.MaxLimit`) para caber nos 2 GB, partindo do pico atual |
| Fuso horário | Contêiner em UTC por padrão | `TZ=America/Sao_Paulo` no compose e conferir `SYSDATE` (§9) |
| Archive log | Script oferece desligar | **Ligado**: sem ele não há recuperação até um ponto no tempo |
| Backup | Data Pump manual e local | RMAN com archive logs, Data Pump noturno e cópia no Object Storage com retenção, mais backup de volume das VMs |
| Restauração | Não documentada para produção | **Teste de restore trimestral**, com tempo medido |
| Dados | Volume Docker | Block volume dedicado em `/opt/oracle/oradata`, com política de backup |
| Reinício | `restart: no` | Subida automática com a VM |
| Imagens | Baixadas do registro da Oracle | Tag fixa e cópia no OCI Container Registry, para não depender de terceiros na reconstrução |
| Espaço | Limite de tablespaces (`cap-tablespaces`) | Manter a ideia e **alertar a partir de 9 GB** |
| Monitoramento | Nenhum | Alertas de VM, disco, banco, certificado e falha de backup |

O backup de volume copia o disco num instante. Com o banco ligado, a cópia volta como depois de uma queda de energia: o Oracle costuma se recuperar, desde que datafiles, redo e controlfiles fiquem no mesmo volume. Ele acelera a reconstrução da VM, mas o RMAN continua sendo o backup do banco.

Meta inicial, a validar no teste de restore: perda máxima de 1 h de dados e retorno em até 4 h.

---

## 8. Critérios para decidir

Situação em 2026-11-10:

| # | Critério | Situação | Se falhar |
|---|---|---|---|
| 1 | **Licença** | Sem consulta à Oracle; risco assumido por Tiago (§3.1) | Migrar para o APEX Service |
| 2 | **Espaço:** dados + APEX + 24 meses de crescimento em até 9 GB | ✅ TF com 1,84 GB, ~1 GB sem as cópias de PDF no log. Boletos crescem ~90 MB/ano (2026-11-10) | Limpar logs e anexos |
| 3 | **Carga:** o pico real funciona com 2 CPUs e 2 GB | ⏳ Pendente: teste nas VMs de produção, antes da virada, com telas e relatórios críticos. Pico de referência: 80 sessões em ~16 meses | Otimizar ou migrar para o APEX Service |
| 4 | **Operação:** definir quem responde a incidentes e avaliar LGPD e contratos | ✅ Decidido por Tiago em 2026-11-05: a equipe da Dolomiti responde, com backup das VMs e dos bancos para restaurar rápido. LGPD avaliada como ok, porque os dados continuam no Brasil | Rever a decisão |

> **Nota sobre a LGPD:** a lei não exige que os dados fiquem no Brasil. O que pesa aqui é o dever de adotar medidas de segurança (art. 46) e de comunicar incidentes (art. 48), porque o banco fica sem patches. Nomes de tabela como `TF_PRESCRICAO` e `TF_MEDICAMENTO` sugerem dado de saúde, que a lei trata como sensível (art. 11). As medidas do §7 respondem a isso; vale registrá-las para os contratos com clientes.

### Script de levantamento (somente leitura)

As duas rodadas foram executadas, em 2026-11-04 e 2026-11-05. Os resultados estão no §4 e na [importação](migracao-oci-importacao-tf.md), que também traz a terceira rodada, de 2026-11-10. Rodar esta de novo antes da virada, para comparar. É compatível com 11g. Rodar com um usuário que leia o dicionário. Se alguma consulta der erro, por exemplo a do ORDS, o resultado das demais continua útil.

```sql
-- Data do último restart (para interpretar os picos do §4) e hora do servidor
select startup_time from v$instance;
select dbtimezone, to_char(sysdate, 'yyyy-mm-dd hh24:mi') agora from dual;

-- Objetos do TF: guardar para comparar depois do import
select object_type, status, count(*) qtd
  from dba_objects where owner = 'TF'
 group by object_type, status order by 1, 2;

-- O que o Data Pump exporta em cada modo
select object_path from schema_export_objects
 where object_path like '%CONTEXT%' or object_path like '%DIRECTORY%';
select object_path from database_export_objects
 where object_path like '%CONTEXT%' or object_path like '%DIRECTORY%';

-- Contexto usado pelo filtro multiempresa
select namespace, schema, package, type
  from dba_context where namespace = 'CTX' or schema = 'TF';

-- Tablespaces usados pelo TF
select tablespace_name, round(sum(bytes)/1024/1024) mb
  from dba_segments where owner = 'TF' group by tablespace_name;

-- Privilégios, roles e grants recebidos pelo TF
select privilege from dba_sys_privs where grantee = 'TF';
select granted_role from dba_role_privs where grantee = 'TF';
select owner, table_name, privilege
  from dba_tab_privs where grantee = 'TF' order by 1, 2;

-- Grants dados pelo TF a outros usuários
select grantee, privilege, count(*) qtd
  from dba_tab_privs where owner = 'TF'
 group by grantee, privilege order by 1, 2;

-- Diretórios, ACLs e sinônimos públicos
select directory_name, directory_path from dba_directories;
select host, lower_port, upper_port, acl from dba_network_acls;
select acl, principal, privilege, is_grant from dba_network_acl_privileges;
select synonym_name, table_name
  from dba_synonyms where owner = 'PUBLIC' and table_owner = 'TF';

-- Dependências entre o TF e outros owners
select referenced_owner, referenced_type, count(*) qtd
  from dba_dependencies
 where owner = 'TF' and referenced_owner not in ('TF', 'SYS', 'PUBLIC')
 group by referenced_owner, referenced_type order by 1, 2;
select owner, type, count(*) qtd
  from dba_dependencies
 where referenced_owner = 'TF' and owner <> 'TF'
 group by owner, type order by 1, 2;

-- Owners pequenos fora do TF
select owner, object_type, count(*) qtd
  from dba_objects where owner in ('DOLOMITI', 'APEXREP')
 group by owner, object_type order by 1, 2;

-- Jobs
select job_name, enabled, state, repeat_interval
  from dba_scheduler_jobs where owner = 'TF';
select job, what, broken, interval from dba_jobs where schema_user = 'TF';

-- Aplicações APEX, arquivos em FLOWS_FILES e módulos REST
select workspace, application_id, application_name, pages, last_updated_on
  from apex_applications order by 1, 2;
select count(*) qtd, round(sum(doc_size)/1024/1024) mb,
       min(created_on) primeiro, max(created_on) ultimo
  from flows_files.wwv_flow_file_objects$;
select * from ords_metadata.ords_modules;

-- LOBs do TF: qual tabela guarda cada anexo
select l.table_name, l.column_name, round(s.bytes/1024/1024) mb
  from dba_lobs l
  join dba_segments s on s.owner = l.owner and s.segment_name = l.segment_name
 where l.owner = 'TF' order by s.bytes desc;

-- Código com endereço fixo ou recurso antigo
select name, type, count(*) linhas
  from dba_source
 where owner = 'TF'
   and regexp_like(text, 'localhost|127\.0\.0\.1|wm_concat|utl_file|dbms_obfuscation', 'i')
 group by name, type order by 1, 2;
```

---

## 9. Plano, se os critérios passarem

1. **Inventário:** o do banco foi feito em 2026-11-05 e completado em 2026-11-10 (§8). Falta a lista do que mais roda nas duas VMs atuais: site, crons, scripts, certificados.
2. **Homologação:** subir a VM de desenvolvimento com o compose da produção, importar o TF conforme abaixo, instalar a aplicação e o JRI e testar fluxos críticos e integrações.
3. **Ambiente de produção:** fazer o upgrade da conta (§10), criar rede e VMs, compose próprio (§7), backup e monitoramento.
4. **Ensaio:** teste de carga nas VMs de produção, migração completa com tempo medido, teste de restore e **uma importação de teste do TF em um APEX Service Always Free**, sem custo, para provar a saída do Free.
5. **Virada:** baixar o TTL do DNS antes, parar a aplicação e os jobs na origem, exportar, importar, testar e trocar o DNS. Manter a Locaweb como retorno por um período definido.
6. **Operação:** rotina mensal e estes gatilhos para sair do Free: dados acima de 10 GB, CPU ou memória saturadas, vulnerabilidade crítica sem correção, questionamento da Oracle ou exigência contratual de cliente.

### Importação só do owner TF

É uma boa escolha ([ADR 0005](decisoes/0005-importar-so-o-owner-tf.md)): as três versões antigas do APEX e o dicionário do 11g ficam para trás, e o Data Pump é o [caminho indicado pela Oracle](https://www.oracle.com/database/free/faq/) de XE para Free. Um teste em 2026-02 já importou o schema no ADB, com o mesmo caminho.

O detalhamento está em [migracao-oci-importacao-tf.md](migracao-oci-importacao-tf.md): linha de base, o que fica fora do schema, achados, script de pré-import, ACLs, comandos, conferência e terceira rodada de consultas. Os três cuidados que evitam dano real continuam valendo:

- **Jobs:** desligados até a virada. Os dois de e-mail continuam desligados depois dela, porque o e-mail fica para depois.
- **Fuso horário:** a produção roda no horário de Brasília, e o [contêiner usa UTC por padrão](https://github.com/oracle/docker-images/blob/main/OracleDatabase/SingleInstance/FAQ.md).
- **Código do 11g:** comparar os inválidos com a lista de esperados. O login para até o hash de senha ser trocado, e as triggers de log antigas dependem do grant de `V$SESSION`.

---

## 10. Itens em aberto

Concluídos:

- [x] Confirmar edição, tamanho e picos da produção: XE 11.2.0.2, TF com 1,84 GB (§4).
- [x] Levantar o custo atual: R$ 370/mês (§5).
- [x] Contar os relatórios Jasper: até 5 em uso.
- [x] Definir a consulta de licença: dispensada por decisão de Tiago ([ADR 0002](decisoes/0002-risco-de-licenca-do-free-assumido.md)).
- [x] Rodar o inventário do §8 (2026-11-05).
- [x] Confirmar a home region: São Paulo.
- [x] Definir quem responde a incidentes e avaliar LGPD e contratos: decidido por Tiago (§8).
- [x] Rodar a terceira rodada de consultas, na produção e no ADB (2026-11-10).
- [x] Decidir o hash de senha: reset geral com hash novo (2026-11-10, [ADR 0006](decisoes/0006-reset-de-senhas-com-hash-novo.md)).
- [x] Decidir o que fazer com as cópias de PDF nos logs `LTF_`: tirar, por patch (2026-11-10, [ADR 0008](decisoes/0008-arquivos-e-senhas-fora-dos-logs.md)).
- [x] Decidir o e-mail: SMTP não migra; no futuro, serviço por API. A porta 25 deixa de importar (2026-11-10, [ADR 0007](decisoes/0007-email-por-smtp-fora-da-migracao.md)).
- [x] Decidir os owners `APEXREP` e `DOLOMITI`: ficam para trás (2026-11-10, [ADR 0005](decisoes/0005-importar-so-o-owner-tf.md)).

Conta OCI, antes de criar as VMs de produção:

- [ ] Conferir o titular e os dados de cobrança da conta: a nota fiscal precisa sair com o CNPJ da Dolomiti. Pela [FAQ de faturamento](https://www.oracle.com/br/corporate/invoicing/faqs/), mudanças nesses dados passam pelo Suporte de Faturamento, então é melhor acertar antes do upgrade.
- [ ] Fazer o upgrade para Pay As You Go pelo [link **Upgrade** no banner do console](https://docs.oracle.com/iaas/Content/FreeTier/freetier.htm). Guias de terceiros indicam também *Billing & Cost Management* → *Upgrade and Manage Payment*, alguns dias de espera e um e-mail de confirmação. Cadastrar o cartão de crédito **físico** da empresa, habilitado para compras internacionais: cartão virtual ou pré-pago é recusado e pode levar ao encerramento da conta ([lição](licoes/2026-09-16-conta-oci-paga-e-franquia-a1.md)).
- [ ] Depois do upgrade, conferir que a VM A1 e os discos continuam grátis: a Oracle não cobra os recursos Always Free, só o que passa da franquia.
- [ ] Criar um orçamento (*Budgets*) com alertas, por exemplo em R$ 300 e R$ 400/mês, para pegar cobrança inesperada no mesmo mês.
- [ ] Ativar MFA no usuário administrador e criar compartimentos separados para produção e desenvolvimento.
- [ ] Na primeira fatura, confirmar impostos, moeda e se a tabela em BRL acompanha o câmbio.
- [ ] Revogar a credencial e o token de API usados no teste do ATP, se não forem mais usados.

Antes do import:

- [x] Aplicar o patch dos PDFs no log, no desenvolvimento atual e na produção ([importação, §8](migracao-oci-importacao-tf.md)): feito em 2026-11-10.
- [ ] Conferir se a `LTF_USUARIO` guarda a coluna `SENHA`; se guardar, aplicar o mesmo patch.
- [x] Decidir o usuário do JRI: `APEXREP` vazio e só de leitura, com grant de schema (2026-11-10, [ADR 0009](decisoes/0009-jri-le-pelo-apexrep-vazio-e-so-de-leitura.md)).
- [x] Decidir se o TF fica sem a role `DBA` no destino: sem `DBA`, com acessos liberados conforme a necessidade (2026-11-10, [ADR 0010](decisoes/0010-tf-sem-a-role-dba.md)).
- [ ] Levantar quem consome o módulo REST `/os/`.
- [ ] Listar o que mais roda nas duas VMs atuais.

Antes da virada:

- [ ] Trocar o hash de senha na homologação e preparar as senhas temporárias, com `SENHA_EXPIRADA` ligado.
- [ ] Fazer o teste de carga nas VMs de produção.
- [ ] Configurar backup de volume das VMs, RMAN e Data Pump, e fazer o teste de restore.
- [ ] Fazer o ensaio da saída para o APEX Service.

OCI:

- [ ] Confirmar imagens `arm64` e capacidade A1 em São Paulo.
- [x] ADB `DEVDOLOMITI`: encerrado em 2026-11-10, depois de salvar os dois pacotes de autenticação em `app/desenv/`. O dump do teste no Object Storage também foi apagado.
- Para a VM de desenvolvimento A1, **o upgrade da conta não é necessário**. A [documentação do Free Tier](https://docs.oracle.com/iaas/Content/FreeTier/freetier.htm) diz que, depois do trial, dá para criar e apagar recursos Always Free, e que eles continuam disponíveis depois do upgrade. Se der *out of host capacity*, tentar de novo mais tarde: São Paulo tem um único availability domain, então a dica de trocar de AD não se aplica.

Documentação:

- [ ] Revisar a variante A1 do §10 do documento de arquitetura, que usa a franquia de 3.000 OCPU-h e 18.000 GB-h. Com a franquia atual da documentação, o custo sobe ~R$ 11/mês.
- [ ] Atualizar o documento de arquitetura após o teste de carga.

---

## Fontes

Consultadas de 2026-11-03 a 2026-11-05.

**Projeto dos links**
- [Artigo: APEX 26.1 Docker images](https://www.oneoracledeveloper.com/2026/06/apex-261-docker-images-for-your-local.html)
- [uc-local-apex-dev: documentação](https://www.united-codes.com/products/uc-local-apex-dev/docs/) · [Host as a Test Database](https://www.united-codes.com/products/uc-local-apex-dev/docs/getting-started/host-test-db/) · [HTTPS](https://www.united-codes.com/products/uc-local-apex-dev/docs/getting-started/expose-https-reverse-proxy/) · [Backups](https://www.united-codes.com/products/uc-local-apex-dev/docs/getting-started/backups/) · [FAQ](https://www.united-codes.com/products/uc-local-apex-dev/docs/other/faq/) · [Migração 26.4](https://www.united-codes.com/products/uc-local-apex-dev/docs/migrations/26-4/)
- [uc-local-apex-dev: repositório](https://github.com/United-Codes/uc-local-apex-dev)

**Licença e limites**
- [Oracle Free Use Terms](https://www.oracle.com/downloads/licenses/oracle-free-license.html)
- [FAQ do Oracle AI Database Free](https://www.oracle.com/database/free/faq/)
- [Restrições de licença do Free](https://docs.oracle.com/en/database/oracle/oracle-database/26/xeinl/licensing-restrictions.html)
- [Guia de licenciamento do 26ai](https://docs.oracle.com/en/database/oracle/oracle-database/26/dblic/Licensing-Information.html)
- [Oracle Technology Hosting](https://www.oracle.com/a/ocom/docs/oracle-technology-hosting-1531497.pdf)
- [Oracle Database 11g XE](https://www.oracle.com/database/technologies/database-11g-express-edition.html)

**OCI e preços**
- [API de preços do Cost Estimator (BRL)](https://apexapps.oracle.com/pls/apex/cetools/api/v1/products/?currencyCode=BRL)
- [Preços do Base Database](https://www.oracle.com/database/base-database-service/pricing/) · [Sobre DB Systems](https://docs.oracle.com/en/cloud/paas/base-database/about-dbs)
- [Recursos Always Free](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm) · [FAQ do Free Tier](https://www.oracle.com/cloud/free/faq/) · [Always Free Autonomous](https://docs.oracle.com/iaas/autonomous-database-shared/doc/autonomous-always-free.html)
- [Cobrança de instâncias paradas](https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/resource-billing-stopped-instances.htm)
- [Free Tier e upgrade para conta paga](https://docs.oracle.com/iaas/Content/FreeTier/freetier.htm) · [Bloqueio da porta 25](https://docs.oracle.com/en-us/iaas/releasenotes/changes/f7e95770-9844-43db-916c-6ccbaf2cfe24)
- [FAQ de faturamento da Oracle Brasil](https://www.oracle.com/br/corporate/invoicing/faqs/)

**LGPD**
- [Lei 13.709/2018](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm)

**Migração**
- [Data Pump: modo schema e referências entre schemas](https://docs.oracle.com/en/database/oracle/oracle-database/19/sutil/oracle-data-pump-export-utility.html)
- [Data Pump e sinônimos públicos (Pythian)](https://www.pythian.com/blog/oracle-data-pump-schema-export-and-public-synonyms)
- [FAQ das imagens Oracle: fuso horário em contêiner](https://github.com/oracle/docker-images/blob/main/OracleDatabase/SingleInstance/FAQ.md)

---

## Changelog

- **2026-11-10 (5):** lição de OCI incorporada ([lição](licoes/2026-09-16-conta-oci-paga-e-franquia-a1.md)): o recolhimento por ociosidade só vale em conta Free Tier, e o upgrade exige cartão físico.
- **2026-11-10 (4):** Tiago decidiu que o TF nasce sem a role `DBA` ([ADR 0010](decisoes/0010-tf-sem-a-role-dba.md)).
- **2026-11-10 (3):** decisões passadas para ADRs: [ADR 0001](decisoes/0001-producao-em-oracle-free-em-duas-vms.md) a [ADR 0003](decisoes/0003-dev-em-a1-com-o-compose-da-producao.md) desta análise e [ADR 0005](decisoes/0005-importar-so-o-owner-tf.md) a [ADR 0009](decisoes/0009-jri-le-pelo-apexrep-vazio-e-so-de-leitura.md) da importação. Os trechos de decisão apontam para eles.
- **2026-11-10 (2):** patch dos PDFs aplicado. `APEXREP` mantido, vazio e só de leitura. ADB `DEVDOLOMITI` encerrado e dump apagado. Confirmado que a VM de desenvolvimento A1 não depende do upgrade da conta.
- **2026-11-10:** terceira rodada de consultas incorporada ([importação, §7](migracao-oci-importacao-tf.md)). Critério de espaço fechado: boletos crescem ~90 MB/ano, e o TF chega com ~1 GB sem as cópias de PDF no log. Tiago decidiu: reset geral de senhas com hash novo, e-mail por SMTP fora da migração, PDFs fora do log e `APEXREP` e `DOLOMITI` fora da migração.
- **2026-11-06:** o proxy reverso da VM de aplicação passa a ser só o nginx. node4ords e suez, os dois apps Node de hoje, não migram ([proxy-reverso.md](proxy-reverso.md)).
- **2026-11-05:** segunda rodada do inventário incorporada; o detalhamento da importação passou para [migracao-oci-importacao-tf.md](migracao-oci-importacao-tf.md). Pico de sessões passa a valer para ~16 meses. Home region confirmada (São Paulo) e upgrade da conta incluído nos itens em aberto. Critério de operação decidido por Tiago: a equipe da Dolomiti responde a incidentes, com backup das VMs e dos bancos. Dev passa a usar o mesmo compose e as mesmas imagens da produção, e o teste de carga vai para as VMs de produção.
- **2026-11-04:** incluídos os dados reais da produção (XE 11.2.0.2, TF com 1,84 GB), o custo atual (R$ 370/mês) e a quantidade de relatórios (até 5). Tiago decidiu não consultar a Oracle e assumir o risco de licença. VMs redimensionadas para 1 OCPU / 6 GB, total de ~R$ 277/mês com dev em A1. Incluídos o plano de importação só do TF e o inventário. APEX Service definido como saída.
- **2026-11-03:** análise criada. Conclusão: não usar a imagem dos links em produção; adotar o Oracle Free só se os critérios do §8 passarem, e reabrir o APEX Service se o Free cair.
