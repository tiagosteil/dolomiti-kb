# Arquitetura da Migração para OCI — Dolomiti

> **Status:** rascunho para validação — revisar antes de iniciar a implementação.
> **Última atualização:** 2026-11-10
> **Atenção:** o plano em curso é o Oracle Free em VMs ([ADR 0001](decisoes/0001-producao-em-oracle-free-em-duas-vms.md), [análise](analise-producao-oci-vm-docker.md)). O ADB de teste citado no §1 foi encerrado em 2026-11-10. A rede, a VM de borda com nginx, o JRI e as integrações continuam valendo como referência.

Documento de referência agrupando as decisões de arquitetura para a migração
da infraestrutura da Dolomiti (hoje 100% em VM na Locaweb) para a Oracle Cloud
Infrastructure (OCI).

---

## 1. Visão geral

A migração sai de um modelo de **VM única** (onde banco, APEX e proxy conviviam
no mesmo host, comunicando por `localhost`) para um modelo de **serviço
gerenciado (ADB) + VMs auxiliares dentro de uma VCN**.

Estado já concluído:

- ADB (Autonomous Database) provisionado com APEX gerenciado — workload
  **Transaction Processing (ATP)**.
- Dump do banco 11 importado com sucesso no ADB.

Decisões desta arquitetura (a validar):

- Manter o ADB no workload **ATP**, sem migrar para o APEX Service, que é mais
  barato mas não aceita conexão SQL*Net e quebra o JRI (ver §9 e custos em §10).
- Reconfigurar o ADB de **acesso público** para **private endpoint** dentro de
  uma VCN.
- Subir uma **VM de borda** como único ponto exposto à internet, com **nginx**
  no lugar dos apps Node de hoje ([proxy-reverso.md](proxy-reverso.md)).
- Subir uma **VM dedicada para o JRI** (JasperReportsIntegration) numa subnet
  privada.
- Manter o **mTLS do Sicoob na VM de borda**, não no ADB.

---

## 2. Decisão-chave: ADB privado (private endpoint)

O ADB hoje está como *"Allow secure access from everywhere"* (endpoint público).
A decisão é movê-lo para **private endpoint** dentro da VCN.

### Por que privado

- Elimina a exposição do banco à internet.
- A VM do JRI pode ficar **privada** (sem IP público).
- A allowlist deixa de depender do range de saída instável do ADB — passa a ser
  por **CIDR fixo** da subnet (Security List).
- HTTPS entre ADB e JRI vira **opcional** (tráfego já isolado na VCN).
- Superfície de ataque concentrada num único ponto: a VM de borda.

### Trade-offs assumidos

- Mudança de rede no ADB, com janela de indisponibilidade. Como o ambiente está
  sendo montado agora, o momento é adequado.
- Acesso administrativo ao ADB deixa de ser direto pela internet: passa a exigir
  **bastion / OCI Bastion / VPN** para conectar via SQL Developer.
  > ⚠️ Impacto no dia a dia de desenvolvimento — validar o fluxo de acesso admin
  > antes de fechar.
- A URL pública Oracle do APEX/ORDS deixa de existir → o **proxy passa a ser
  obrigatório** para qualquer acesso ao APEX (não mais opcional).

---

## 3. Topologia de rede (VCN)

```
Internet
   │
   ├── Usuários (domínio) ──────────────┐
   │                                    ▼
┌──────────────────── VCN 10.0.0.0/16 ──────────────────────┐
│  Gateways: Internet GW · NAT GW · Service GW              │
│                                                            │
│  ┌── Subnet pública 10.0.1.0/24 ──┐  ┌── Subnet privada 10.0.2.0/24 ──┐
│  │                                │  │                                │
│  │   VM de borda (IP público)     │  │   ADB (private endpoint)       │
│  │   - nginx                      │  │   - Autonomous DB + APEX+ORDS  │
│  │   - TLS entrada APEX           │  │   - IP privado 10.0.2.x        │
│  │   - TLS entrada JRI            │  │                                │
│  │   - mTLS saída Sicoob          │  │   VM do JRI (privada)          │
│  │   - arquivos estáticos         │  │   - Tomcat 9 + Jasper 6.20.6   │
│  │                                │  │                                │
│  │                                │  │   Bastion (acesso admin)       │
│  └────────────────────────────────┘  └────────────────────────────────┘
└────────────────────────────────────────────────────────────┘
```

### Componentes de rede

| Componente | Papel |
|---|---|
| **VCN** | Rede privada isolada da Dolomiti. CIDR sugerido `10.0.0.0/16`. |
| **Subnet pública** (`10.0.1.0/24`) | Hospeda a VM de borda com IP público. |
| **Subnet privada** (`10.0.2.0/24`) | Hospeda ADB, VM do JRI e bastion. Sem IP público. |
| **Internet Gateway** | Entrada pública → VM de borda. |
| **NAT Gateway** | Saída à internet para recursos privados (ex.: ADB → Sicredi). |
| **Service Gateway** | Acesso a serviços Oracle sem sair para a internet. |
| **Security Lists / NSGs** | Firewalls por subnet/recurso. Desde o [ADR 0011](decisoes/0011-nsg-por-vm-e-security-list-fechada.md), as security lists não abrem porta, e cada VM tem o seu NSG. |

> ⚠️ **Ponto crítico:** a subnet do ADB **precisa de NAT Gateway** para que as
> chamadas de saída (`UTL_HTTP`/`APEX_WEB_SERVICE`) para bancos externos
> funcionem. Sem isso, integrações de saída falham com timeout.

---

## 4. VM de borda — os quatro papéis

A VM de borda é a peça central e o **único ponto exposto à internet**. Hoje esses
papéis estão divididos entre dois apps Node, o node4ords (entrada) e o suez
(saída). Na OCI, passam para o nginx ([proxy-reverso.md](proxy-reverso.md) §6).
Papéis:

1. **Terminação TLS de entrada — APEX**: usuário → proxy → ORDS/APEX do ADB.
   Reescreve a URL Oracle interna para o domínio próprio.
2. **Terminação TLS de entrada — JRI**: expõe `https://dominio/jri` para fora;
   o Tomcat serve o JRI em HTTP puro internamente.
3. **mTLS de saída — Sicoob**: segura o certificado + senha de cliente e faz o
   mTLS para fora. O ADB chama a VM em HTTP interno.
4. **Arquivos estáticos**: publica os estáticos como hoje.

> ⚠️ **SPOF (ponto único de falha):** se a VM de borda cai, param
> simultaneamente o acesso web (APEX/JRI) **e** a integração do Sicoob.
> - Aceitável para o porte atual (é o que já se opera hoje na Locaweb).
> - Mitigação: manter o provisionamento **documentado e reprodutível** para
>   reconstrução rápida. Considerar backup/imagem da VM.
> - Evolução futura: OCI Load Balancer + múltiplas VMs de borda quando alta
>   disponibilidade virar requisito (dá para adicionar depois sem redesenhar).

---

## 5. Integrações de saída (webservices de bancos)

O "privado" afeta a **entrada** e o tráfego **interno** da VCN. A **saída** para a
internet depende de caminho explícito (NAT Gateway) e de ACL de rede.

### Regras gerais no ADB

- **NAT Gateway** obrigatório na subnet do ADB para qualquer saída à internet.
- **ACL de rede** obrigatória e explícita por host de destino, via
  `DBMS_NETWORK_ACL_ADMIN` (ver §7).
- **Wallet de saída** é gerenciado pela Oracle e já confia nas **CAs públicas** —
  para HTTPS com certificado de CA pública, **não é preciso configurar wallet**.
- Certificado de servidor **não-público** (self-signed / CA interna) exigiria um
  **customer-managed wallet** — mais trabalhoso. Mapear se algum webservice usa
  isso.

### Sicredi — HTTPS simples

- HTTPS normal, sem certificado de cliente.
- Pode ir **direto do ADB pelo NAT Gateway**; o ADB confia na CA pública nativamente.
- Basta a ACL de rede para o host.
- Opcional: pode passar pela VM de borda também, se quiser centralizar/auditar saídas.

### Sicoob — mTLS (certificado de cliente)

- É **mTLS**: além do servidor, o **cliente** apresenta certificado + senha.
- ⚠️ O ADB **não** permite injetar um certificado de cliente com chave privada
  no wallet de saída gerenciado. mTLS de cliente a partir do PL/SQL do Autonomous
  é **limitado / não confiável** — não migrar para dentro do ADB.
- **Solução:** manter o mTLS na **VM de borda** (como já é hoje).
  - O PL/SQL no ADB chama a VM de borda em HTTP interno.
  - A VM segura o certificado de cliente e faz o mTLS para fora com o Sicoob.
  - A chave privada nunca entra no ADB (onde não caberia mesmo).

### Padrão de chamada (migração do `localhost`)

Hoje o banco chama o suez na mesma VM, por nome. O `/etc/hosts` resolve o nome
para `127.0.0.1`. Na VCN, o mesmo nome precisa resolver para o IP privado da VM
de borda:

```
Hoje:  http://apisicoobauth.localhost:3000/...   → 127.0.0.1 (suez)
Novo:  http://apisicoobauth.localhost:3000/...   → 10.0.1.10 (nginx na VM de borda)
```

O proxy escolhe o destino pelo nome, então chamar direto pelo IP não funciona. No
ADB, conferir se dá para resolver `*.localhost` por DNS privado da VCN. Se não der,
os parâmetros de URL passam a usar outro nome. O certificado sai do suez e vai
para o nginx ([proxy-reverso.md](proxy-reverso.md) §6). Adicionar a ACL de rede
no ADB para esses nomes.

---

## 6. VM do JRI (JasperReportsIntegration)

### Versão

- **JRI 2.11.0 / Jasper 6.20.6** — mantém compatibilidade com os `.jrxml`
  existentes.
- ❌ Evitar a **3.0.0 / Jasper 7.0.1**: quebra todos os relatórios (exigiria
  atualizar cada `.jrxml` no Jaspersoft Studio 7.0.x).

### Sistema operacional e shape

- **Oracle Linux 8** (CentOS 7 está EOL; OL9 complica o Java 8).
- Shape sugerido: **VM.Standard.E4.Flex** ou **A1.Flex (ARM Ampere)**,
  1 OCPU / 6–8 GB. A1 pode entrar no Always Free.
- Subnet **privada**, mesma VCN do ADB. **Não** abrir 8080 para o mundo.

### Servidor de aplicação

- **Apache Tomcat 9** → usar o `jri.war` padrão (NÃO o `-tomcat10`).
- **Modo headless obrigatório** (`-Djava.awt.headless=true` via `setenv.sh`),
  senão relatórios com gráficos/imagens quebram.
- Java 11 (OpenJDK).

### Conexão com o ADB (via wallet)

O Tomcat conecta no ADB **também via wallet** (não é só o banco que usa wallet):

1. Baixar o **Instance Wallet** do ADB (console → DB Connection → Download Wallet).
2. Copiar o unzip para a VM (ex.: `/opt/tomcat/adb_wallet`).
3. Configurar a datasource no `application.properties`:

```properties
[datasource:default]
type=jdbc
url=jdbc:oracle:thin:@dolomiti_high?TNS_ADMIN=/opt/tomcat/adb_wallet
username=SEU_SCHEMA
password=SUA_SENHA
```

   - O alias (`dolomiti_high` / `_medium` / `_low`) vem do `tnsnames.ora` do wallet.
   - No Linux usar `/` no path (o bug do `\` é só no Windows).
4. Criptografar a senha com `encryptPasswords.sh` (incluso no pacote).

### Segurança do servlet

- Servlet só deve ser acessível internamente. Com ADB privado, travar por
  **Security List / NSG** no CIDR da subnet do banco.
- `infoPageIsEnabled=false` em produção.
- `printDebugToScreen=false` em produção.
- Apagar `reports/demo`.

---

## 7. Checklist de itens em aberto

Rede / OCI:
- [ ] Confirmar procedimento exato de conversão do ADB para private endpoint.
- [ ] Definir CIDRs finais da VCN e subnets.
- [ ] Criar Internet GW, NAT GW e Service GW.
- [ ] Criar/ajustar **NAT Gateway na subnet do ADB** (saída das integrações).
- [ ] Fechar Security Lists / NSGs (entrada da borda, JRI restrito ao ADB).
- [ ] Definir mecanismo de acesso admin ao ADB (bastion / OCI Bastion / VPN).

ADB (SQL):
- [ ] Levantar ACLs existentes no banco atual:
      `SELECT host, lower_port, upper_port, ace_order, grantee, privilege FROM dba_host_aces ORDER BY host;`
- [ ] Recriar ACLs de rede (`DBMS_NETWORK_ACL_ADMIN.APPEND_HOST_ACE`) para:
      - host da VM do JRI
      - host da VM de borda (rota do Sicoob)
      - host do Sicredi (se saída direta pelo NAT)
- [ ] Mapear se algum webservice usa certificado não-público (→ customer wallet).

VM do JRI:
- [ ] Provisionar VM Oracle Linux 8 na subnet privada.
- [ ] Instalar Java 11 + Tomcat 9 + modo headless.
- [ ] Deployar `jri.war` 2.11.0.
- [ ] Configurar wallet do ADB + `application.properties`.
- [ ] Endurecer (infoPage/debug off, remover demo, criptografar senha).

VM de borda:
- [ ] Instalar o nginx na subnet pública, no lugar do node4ords e do suez
      ([proxy-reverso.md](proxy-reverso.md) §6).
- [ ] Configurar rota `/jri` (proxy → Tomcat interno).
- [ ] Configurar rota do APEX (proxy → ORDS do ADB).
- [ ] Portar o mTLS do Sicoob (PFX convertido para PEM no nginx).
- [ ] Migrar publicação de estáticos.
- [ ] Certificado (Certbot / Let's Encrypt) para o domínio.
- [ ] Documentar provisionamento para reconstrução rápida (mitigação de SPOF).

Roteamento de domínio (fase posterior, já mapeada):
- [ ] Apontar domínio da Dolomiti para o IP público da VM de borda.

Custos:
- [ ] Validar a decisão ATP × APEX Service (§9).
- [ ] Confirmar o storage real ocupado no ADB após o import e recalcular §10.
- [ ] Verificar se a Dolomiti tem licença Oracle Database com suporte ativo (BYOL).
- [ ] Criar **Budget** com alerta de gasto no OCI (Billing → Budgets).
- [ ] Decidir onde ficam dev/homologação (Developer Database ou Always Free).

---

## 8. Notas de decisão (racional)

- **A VM de borda fica no desenho por mérito, não por inércia:** o proxy dela
  cumpre uma função que o ADB genuinamente não consegue (mTLS de cliente na saída
  do Sicoob). Hoje quem faz isso é o suez; na OCI, o nginx.
- **Load balancer descartado por ora:** resolve entrada (não saída) e a VM de
  borda já é obrigatória para o mTLS. Adicionar LB só quando HA for requisito —
  possível depois sem redesenhar.
- **Sicredi pode simplificar:** sai direto pelo NAT, aposentando o proxy para
  essa chamada (opcional).
- **ATP em vez de APEX Service:** o APEX Service custa ~¼ da ECPU, mas não aceita
  SQL*Net de entrada: o JRI deixa de funcionar e o acesso admin fica só pelo
  navegador. A diferença (~R$ 2 mil/mês) paga o desenho atual sem reescrever
  relatórios. Detalhes em §9.

---

## 9. Workload do ADB: ATP × APEX Service

No estimador da Oracle, a mesma configuração (2 ECPU, 20 GB de storage, 60 GB de
backup) custa **~R$ 2.648/mês como ATP** e **~R$ 659/mês como APEX Service**.
A diferença está **só no preço da ECPU** (R$ 1,7592 × R$ 0,4225 por hora, ~4,2×).
Storage e backup custam o mesmo nos dois.

### O que é cada um

- **ATP (Autonomous Transaction Processing):** o ADB completo, com APEX e ORDS
  pré-instalados e gerenciados. É o que está provisionado hoje.
- **APEX Service** (workload type *APEX*, no estimador "APEX Application
  Development"): o mesmo motor Autonomous, com a mesma gestão de APEX e ORDS.
  A ECPU custa ~4× menos e, em troca, o banco **só é acessível por HTTP**:
  APEX, ORDS/REST e Database Actions.

### Diferenças que importam para a Dolomiti

| | ATP (atual) | APEX Service |
|---|---|---|
| ECPU/hora (lista, BRL) | R$ 1,7592 | R$ 0,4225 |
| APEX + ORDS gerenciados, vanity URL | ✅ | ✅ |
| Private endpoint na VCN (§2) | ✅ | ✅ |
| Saída `UTL_HTTP` / `APEX_WEB_SERVICE` + ACL (§5) | ✅ | ✅ |
| **Conexão de cliente via SQL*Net** (JDBC, SQL Developer desktop, SQLcl, `impdp`) | ✅ | ❌ **não disponível** |
| ORDS próprio (customer-managed) | ✅ | ❌ |
| BYOL (licença própria) | ✅ | ❌ |
| Converter para o outro workload | ❌ ATP → APEX não é permitido, nem por clone | ✅ APEX → ATP online, sem downtime |

Outros recursos ausentes no APEX Service, sem impacto direto hoje: refreshable
clones, registro no Data Safe, Graph Studio, notebooks OML, modo read-only e
APIs MongoDB.

> O proxy de entrada (hoje o node4ords; na OCI, o nginx) é **proxy reverso** para
> o ORDS da Oracle, não um ORDS próprio. A restrição de "customer-managed ORDS"
> não o afeta.

### Impacto na arquitetura deste documento

A falta de **SQL*Net de entrada** decide a questão:

1. **O JRI deixa de funcionar.** O JRI roda a query de cada relatório
   conectando no banco via JDBC + wallet (§6), e é justamente essa conexão que o
   APEX Service bloqueia. A chamada do banco para o JRI (HTTP de saída) funciona,
   mas a volta do JRI ao banco não. As alternativas exigem reescrever relatórios:
   - Mandar os dados prontos em JSON/XML para o Jasper. Cada `.jrxml` troca a
     query SQL por um datasource JSON/XML.
   - Trocar o JRI pela impressão nativa do APEX via **OCI Document Generator**,
     com templates Word/Excel. Todos os layouts são refeitos.
2. **O acesso administrativo fica só no navegador.** Não dá para conectar SQL
   Developer desktop nem SQLcl, nem mesmo pelo bastion de §2. Sobram Database
   Actions (SQL Developer Web) e o SQL Workshop do APEX. Scripts e automações via
   SQLcl, inclusive o MCP do SQLcl usado com o Claude, param de funcionar.
3. **A migração teria de ser refeita.** O ATP atual não pode ser convertido. Seria
   preciso provisionar um APEX Service novo e reimportar o dump do banco 11 só
   por `DBMS_CLOUD` + `DBMS_DATAPUMP` (Object Storage) ou pelo Data Pump do
   Database Actions, porque o `impdp` cliente não conecta.

Continua igual nos dois workloads: private endpoint, NAT Gateway, ACLs, saída
para o Sicredi e chamada HTTP para a VM de borda (mTLS do Sicoob). As §§2–5 não
mudam.

### Recomendação

**Manter ATP.** A diferença de **~R$ 1.989/mês (~R$ 23,9 mil/ano)** mantém o JRI
sem reescrever relatórios, o acesso admin por SQL Developer/SQLcl e o Data Pump
padrão.

O APEX Service passa a fazer sentido se os relatórios saírem do JRI e o time
aceitar administrar só pelo navegador. Ele também serve para **apps novos sem
relatório Jasper**: dá para começar no APEX Service e promover para ATP depois,
online, se precisar. O caminho inverso não existe.

Como reduzir o custo sem sair do ATP:

- **BYOL:** a ECPU cai para R$ 0,4225/h, o mesmo preço do APEX Service. Só vale se
  a Dolomiti tiver licença Oracle Database (EE ou SE2) com suporte ativo.
- **Liga/desliga agendado:** com o ADB parado não se paga ECPU, só storage. Por
  exemplo, 14 h/dia × 26 dias dá ~R$ 1.281 de ECPU no lugar de R$ 2.618.
  ⚠️ Com o banco parado, jobs (`DBMS_SCHEDULER`), integrações bancárias e
  qualquer acesso fora do horário também param. Só considerar se o uso real
  permitir.
- **Dev/homologação fora do ATP pago:** usar *Developer Database* (~R$ 152/mês;
  4 ECPU fixos, 20 GB, sem SLA, proibido para produção) ou Always Free.

Referências: [Limitações do APEX Service](https://docs.oracle.com/en/cloud/paas/apex/gsadd/restrictions-and-limitations.html) ·
[APEX → ATP](https://docs.oracle.com/en-us/iaas/autonomous-database-serverless/doc/upgrade-apex-transaction-processing.html) ·
[Clone entre workloads](https://docs.oracle.com/en/cloud/paas/autonomous-database/serverless/adbsb/autonomous-clone-cross-workload-type.html) ·
[Opções de APEX na OCI](https://docs.oracle.com/en/cloud/paas/apex/gsadd/welcome-to-oracle-apex-in-oracle-cloud.html)

---

## 10. Previsão de custos (mensal)

### Premissas

- Preços de **lista** da Oracle em **BRL**, pay-as-you-go, consultados em
  2026-10-06 na API pública do [Cost Estimator](https://www.oracle.com/br/cloud/costestimator.html).
  Sem impostos. Câmbio implícito na tabela da Oracle: ~R$ 5,24/US$.
- **744 h/mês** (24×7).
- ADB com **2 ECPU** (mínimo), sem consumo de autoscaling, **20 GB** de storage
  (mínimo; ajustar ao tamanho real após o import) e **60 GB** de backup (padrão
  do estimador).
- VMs em **E4.Flex** (x86), com boot volume de 50 GB cada.
- Conferência: o APEX Service bate com o estimador (R$ 658,55). No card do
  estimador, os R$ 29,84 são storage + backup.

### Por componente

| Componente | Configuração | ATP (recomendado) | APEX Service |
|---|---|---:|---:|
| ADB: ECPU | 2 ECPU × 744 h | R$ 2.617,68 | R$ 628,71 |
| ADB: storage | 20 GB × R$ 1,0225 | R$ 20,45 | R$ 20,45 |
| ADB: backup | 60 GB × R$ 0,1565 | R$ 9,39 | R$ 9,39 |
| VM de borda | E4.Flex 1 OCPU / 4 GB | R$ 120,76 | R$ 120,76 |
| VM do JRI | E4.Flex 1 OCPU / 8 GB | R$ 144,13 | — (JRI não funciona, §9) |
| Boot volumes | 50 GB por VM | R$ 0 (Always Free: 200 GB) | R$ 0 |
| VCN, Internet GW, NAT GW, Service GW | — | R$ 0 | R$ 0 |
| OCI Bastion | — | R$ 0 | R$ 0 |
| Tráfego de saída | até 10 TB/mês | R$ 0 | R$ 0 |
| **Total** | | **R$ 2.912,41** | **R$ 779,31** + reescrita dos relatórios |

### Variante: VMs em A1.Flex (ARM) no Always Free

As duas VMs em A1.Flex (borda com 1 OCPU / 6 GB e JRI com 1 OCPU / 8 GB) somam
1.488 OCPU-h e 10.416 GB-h por mês. Isso cabe na franquia gratuita de 3.000 OCPU-h
e 18.000 GB-h por tenancy, então as VMs saem por **R$ 0** e o **total com ATP cai
para R$ 2.647,53**.

- ⚠️ É preciso validar a stack em ARM (aarch64): nginx, Java 11,
  Tomcat 9 e JRI/Jasper (fontes, modo headless).
- ⚠️ É comum faltar capacidade A1 na região São Paulo. A franquia também é
  compartilhada com qualquer outro recurso A1 da tenancy.
- Fora da franquia, a A1 paga custa ~R$ 74/mês para 1 OCPU / 6 GB.

### O que mexe na conta

| Variável | Impacto mensal |
|---|---|
| +1 ECPU fixa, 24×7 | ATP +R$ 1.308,84 · APEX +R$ 314,36 |
| Autoscaling (até 3× a base) | cobrado pelo uso efetivo acima da base. Monitorar picos. |
| +100 GB de storage | +R$ 102,25 |
| +100 GB de backup | +R$ 15,65 |
| BYOL no ATP | ECPU de R$ 1,7592 → R$ 0,4225/h (−R$ 1.988,97 com 2 ECPU) |
| Liga/desliga agendado (14 h × 26 dias) | ECPU ATP de R$ 2.617,68 → ~R$ 1.280,69 |
| Ambiente de dev/homolog (Developer Database) | +R$ 152,31 |

---

## Changelog

- **2026-11-10 (2):** security lists fechadas e um NSG por VM ([ADR 0011](decisoes/0011-nsg-por-vm-e-security-list-fechada.md)).
- **2026-11-10:** o plano passou a ser o Oracle Free em VMs ([ADR 0001](decisoes/0001-producao-em-oracle-free-em-duas-vms.md)); o desenho com ATP fica como referência de rede, nginx, JRI e integrações.
- **2026-11-06:** na VM de borda, o nginx substitui os apps Node (node4ords na
  entrada e suez na saída). Corrigido o padrão de chamada do Sicoob: hoje é
  `apisicoobauth.localhost:3000`, pelo suez, e o proxy escolhe o destino pelo
  nome. Detalhes em [proxy-reverso.md](proxy-reverso.md).
- **2026-10-06:** comparado ATP × APEX Service (§9). Mantido o ATP porque o APEX
  Service não aceita SQL*Net e quebra o JRI. Adicionada a previsão de custos
  (§10) e os itens de custo no checklist (§7).
