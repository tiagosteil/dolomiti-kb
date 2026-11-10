# Análise: Integração NFS-e — API Nacional × Intermediário (Spedy) — Dolomiti

> **Status:** análise para decisão — nada implementado.
> **Última atualização:** 2026-10-13

Objetivo: permitir que os clientes da Dolomiti emitam NFS-e pelo ERP usando o
**padrão nacional** (Emissor Nacional / Sefin Nacional). Este documento compara
duas abordagens: integrar **direto** com as APIs do governo ou usar um
**intermediário** (Spedy como referência).

---

## 1. Resumo e recomendação

- As duas abordagens são viáveis.
- **Recomendação para o momento:** começar com **intermediário**, mas atrás de
  uma **camada de abstração própria** (package adaptador). A integração direta
  fica como evolução quando *volume × tarifa* superar o custo de manutenção.
- Modelar a NFS-e no Dolomiti pelos campos da **DPS** (layout nacional), não
  pelo payload do fornecedor. Assim, trocar de provedor (ou ir direto) vira
  trocar o adaptador, não reescrever o módulo.
- A proposta da Spedy (R$ 129–289/mês, §9) equivale a poucas horas de
  manutenção por mês, o que reforça a recomendação.

---

## 2. Contexto regulatório (o que pesa na decisão)

| Data | Marco |
|---|---|
| 2026-01-01 | LC 214/2025, art. 62: municípios devem adotar o padrão nacional e compartilhar no ADN |
| 2026-09-01 | Resolução CGSN 189/2026: ME/EPP do **Simples Nacional** emitem obrigatoriamente no padrão nacional |
| Ao longo de 2026 | Lucro Presumido/Real: conforme a migração de cada município |

- **Adesão incompleta:** São Paulo, Barueri e Salvador mantiveram layouts
  próprios. São Paulo, porém, passou a exigir o Emissor Nacional para
  autônomos (ago/2026) e para o Simples (set/2026).
- **Implicação:** se a base de clientes é majoritariamente Simples, a API
  nacional cobre todos. O diferencial entre as opções é **quem absorve a
  manutenção**.

### O padrão muda rápido (amostra de 2026, produção)

| Data | Mudança |
|---|---|
| 2026-03-13 | Desligamento/ajuste de regras de validação; ajustes na API de consulta (UTF-8) |
| 2026-04-24 | Renomeação de códigos de erro (ex.: E6151→E1634, E6157→E1225) e nova regra E1000 (Calculadora RTC) |
| 2026-07-01 | Ajuste de validação IBS/CBS: `pAliqEfetUF/Mun/CBS` obrigatórios e iguais às alíquotas quando não há redutor |
| 2026-08-03 | DANFSe conforme NT 008; **desativação da API de DANFSe do ADN (v1.0)** |
| 2026-08-10 | CNPJ alfanumérico; destaque de IBS/CBS no Emissor Web (NT 004) |
| NT 009/2026 | Parte adiada sem data (novos fatos geradores, subitens 99.02–99.04) |

---

## 3. Opção A — Integração direta (Sefin Nacional)

### Como funciona
- A **DPS** é montada em XML, **assinada (XMLDSig)**, compactada em **GZip** e
  codificada em **Base64** dentro de um JSON.
- Transporte por **mTLS** com certificado **ICP-Brasil A1** do prestador.
- `POST /nfse` é **síncrono**: devolve a NFS-e autorizada na mesma chamada.
- `GET /dps/{id}` e `HEAD /dps/{id}` recuperam timeouts (a DPS já virou nota?).
- `GET /nfse/{chaveAcesso}` consulta a nota.
- Eventos assinados: cancelamento (`e101101`), substituição (`e105102`).
- APIs separadas — Sefin Nacional, ADN, CNC, Parâmetros Municipais, DANFSe —
  cada uma com **Produção Restrita** e **Produção** (URLs no §8).

### Encaixe na arquitetura OCI
- O ADB não injeta certificado de cliente com chave privada em chamadas de
  saída (ver [arquitetura-migracao-oci.md](arquitetura-migracao-oci.md) §5).
  Assinatura e mTLS teriam de rodar num **serviço na VM de borda**, carregando
  o PFX certo por empresa emissora.
- Diferente do Sicoob, aqui é **um certificado por tenant emissor**, e a chave
  privada também é usada para **assinar o XML**, não só no TLS.
- **DANFSe** passa a ser responsabilidade da Dolomiti (API do ADN desativada em
  2026-08-03) — gerar via **JRI**.

### Prós
- Custo zero por nota e nenhuma dependência comercial.
- Emissão síncrona: o APEX recebe a nota autorizada na mesma chamada, sem
  webhook.
- Controle total de dados, rejeições e eventos, inclusive substituição.
- Aproveita a VM de borda (já faz mTLS de saída) e o JRI.

### Contras
- **Infra:** serviço de assinatura + mTLS na VM de borda, por empresa.
- **Certificados:** a Dolomiti vira custodiante de todos os A1 e senhas —
  exige cofre de segredos, troca anual e alerta de vencimento.
- **Manutenção contínua:** cada nota técnica vira trabalho próprio, no prazo
  do governo (ver ritmo de 2026 no §2).
- **Regra fiscal:** o HTTP é a parte fácil. O difícil são retenções, local de
  incidência, códigos de rejeição e IBS/CBS.
- **Cobertura:** só municípios no padrão nacional.
- **Testes:** mesmo a Produção Restrita exige certificado real.
- **Pessoas:** conhecimento concentrado em uma pessoa.

---

## 4. Opção B — Spedy (intermediário)

### Como funciona
- REST/JSON, autenticado pelo header `X-Api-Key`. Ambientes **sandbox**
  (`sandbox-api.spedy.com.br`) e **produção** (`api.spedy.com.br`).
- Emissão **assíncrona**: `POST /v1/service-invoices` → `2xx` só confirma que a
  nota foi aceita. Resultado por **webhook** ou `GET /v1/service-invoices/{id}`.
- **Multiempresa:** a conta titular cria empresas via `POST /v1/companies`;
  cada empresa recebe sua própria `X-Api-Key`. Mapeia 1:1 com a empresa
  emissora do Dolomiti.
  > ⚠️ `ID_EMPRESA` é bitmask com multisseleção (ver
  > [convencoes/multiempresa.md](convencoes/multiempresa.md)). A chave deve ser
  > resolvida pela **empresa emissora da nota**, nunca pela seleção da sessão.
- Certificado A1 enviado via `POST /v1/companies/{id}/certificates` (um ativo
  por empresa; o último enviado substitui o anterior).
- `issueType` da empresa: `annfs` (Ambiente Nacional) | `website` | `alt`
  (provedor municipal).
- **IBS/CBS:** bloco `ibsCbs` no nível da nota (não por item).
- **Webhooks** por conta (não por empresa), assinados no padrão Standard
  Webhooks; o payload traz `company` para identificar o emissor.
- Extras prontos: PDF/XML, e-mail ao tomador, `check-status` (reconciliação),
  NFS-e **recebidas** do ADN com manifestação.

### Encaixe na arquitetura OCI
- HTTPS comum com API key → `APEX_WEB_SERVICE` direto do ADB pela **NAT
  Gateway**, mesmo padrão do Sicredi (§5 da arquitetura OCI). Sem mTLS nem PFX
  na infra da Dolomiti no dia a dia.
- Retorno assíncrono: endpoint **ORDS** exposto pela VM de borda para o webhook
  (validar a assinatura HMAC com `DBMS_CRYPTO`) **ou** job de polling via
  `DBMS_SCHEDULER`.

### Prós
- Prazo para colocar no ar bem menor; as notas técnicas viram problema do
  fornecedor.
- Arquitetura simples (HTTPS + API key).
- Cobre municípios fora do padrão nacional.
- PDF/XML, e-mail, reconciliação e NFS-e tomadas já vêm prontos.

### Contras
- **Custo recorrente:** a API é produto à parte. Proposta de 2026-10-13:
  R$ 129/mês (1.000 notas, 30 CNPJs) ou R$ 289/mês (3.000 notas, 50 CNPJs),
  com excedente de R$ 0,161 ou R$ 0,120 por nota (§9). Referências (out/2026):
  planos self-service da Spedy cobram R$ 0,35–0,62 por nota excedente (o plano
  de entrada não tem API); Focus NFe cobra R$ 0,10 por nota adicional e
  R$ 37,90 por CNPJ adicional.
- **Assíncrono:** exige webhook ou polling.
- **Isolamento multitenant:** clientes e produtos ficam no nível da **conta**,
  compartilhados por todas as empresas — validar com vários tenants numa conta.
- **Substituição:** não há endpoint de substituição de NFS-e na doc; o caminho
  documentado para corrigir é cancelar e reemitir.
- **Dependência:** custódia dos certificados e dos dados fiscais dos clientes
  passa a um terceiro (contrato + LGPD). Foco comercial deles é infoprodutor e
  e-commerce; a API é vendida à parte.

---

## 5. Comparativo

| | Direta (Sefin Nacional) | Spedy |
|---|---|---|
| Custo recorrente | Zero na fatura; vira horas internas | R$ 129–289/mês + excedente (§9) |
| Prazo do MVP | Maior | Menor |
| Notas técnicas | Por conta da Dolomiti | Por conta do fornecedor |
| Cobertura | Só padrão nacional | Nacional + municipais |
| Modelo de chamada | Síncrono | Assíncrono (webhook/polling) |
| Infra | Serviço de assinatura + mTLS na VM de borda | `APEX_WEB_SERVICE` + webhook |
| Certificados A1 | Custódia da Dolomiti | Custódia da Spedy |
| DANFSe | Gerado pela Dolomiti (JRI) | Pronto (PDF da API) |
| Controle e debug | Total | Limitado à API do fornecedor |

---

## 6. Diretrizes de desenho (valem para qualquer provedor)

- **Modelo de dados pela DPS nacional:** nota, eventos (cancelamento,
  substituição) e status próprios do Dolomiti, com `ID_EMPRESA` e as convenções
  de [convencoes/banco.md](convencoes/banco.md).
- **Adaptador por provedor:** um package de fachada (emitir, consultar,
  cancelar, substituir) que delega para um package específico do provedor.
- **Segredos fora de tabela em texto puro:** API keys e/ou PFX + senha em cofre
  (ex.: OCI Vault) ou cifrados; nunca em `TF_PARAMETROS` em claro.
- **Idempotência:** usar o `integrationId` (Spedy) ou o Id da DPS (direto) para
  reenvio seguro após timeout.

> Esboço — nomes de tabelas e packages a definir quando o módulo for aberto.

---

## 7. Itens em aberto / próximos passos

- [ ] Levantar **regime tributário, município e volume mensal de NFS-e** de
      cada CNPJ que vai emitir; checar adesão do município (API do CNC ou
      `GET /v1/service-invoices/cities`).
- [x] Pedir **cotação da API Spedy** — recebida em 2026-10-13 (§9).
- [ ] Comparar com 1–2 alternativas (Focus NFe, NFE.io) na mesma base: por
      CNPJ e por nota.
- [ ] Perguntar à Spedy: suporte a **substituição** de NFS-e; se a chave de uma
      empresa enxerga clientes de outra; **SLA**; valores de **rate limit**.
- [ ] Perguntar à Spedy (comercial): planos acima de **3k notas / 50 CNPJs**;
      **CNPJ adicional** avulso; o que **conta como nota** (canceladas,
      rejeitadas, NFS-e recebidas do ADN); **fidelidade**, reajuste e desconto
      anual.
- [x] Fechar o preço (§9) — definido em 2026-10-13: 2 clientes, `m` = 40%,
      arredondado para cima; implantação de R$ 1.000 (`t` = 0 enquanto for MEI).
- [ ] (Opcional) **Spike de 1–2 dias** na Produção Restrita com o A1 da própria
      Dolomiti, assinando e transmitindo pela VM de borda — transforma "a
      integração direta é trabalhosa" num número real.
- [ ] Definir política de **custódia de certificados A1** (quem guarda,
      renovação, alerta de vencimento) — necessária em qualquer opção.

---

## 8. Referências

### APIs oficiais (Produção Restrita → Produção)
- Índice: https://www.gov.br/nfse/pt-br/biblioteca/documentacao-tecnica/apis-prod-restrita-e-producao
- Sefin Nacional: https://sefin.producaorestrita.nfse.gov.br/API/SefinNacional/docs/index → https://sefin.nfse.gov.br/SefinNacional/docs/index
- ADN: https://adn.producaorestrita.nfse.gov.br/docs/index.html → https://adn.nfse.gov.br/docs/index.html
- ADN Contribuintes: https://adn.producaorestrita.nfse.gov.br/contribuintes/docs/index.html → https://adn.nfse.gov.br/contribuintes/docs/index.html
- CNC (consulta): https://adn.producaorestrita.nfse.gov.br/cnc/consulta/docs/index.html → https://adn.nfse.gov.br/cnc/consulta/docs/index.html
- Parâmetros Municipais: https://adn.producaorestrita.nfse.gov.br/parametrizacao/docs/index.html → https://adn.nfse.gov.br/parametrizacao/docs/index.html
- Atualizações e implantações: https://www.gov.br/nfse/pt-br/biblioteca/documentacao-tecnica/atualizacoes-e-implantacoes

### Spedy
- Documentação: https://docs.spedy.com.br (índice completo em https://docs.spedy.com.br/llms.txt)
- Emissão de NFS-e: https://docs.spedy.com.br/guides/emissao-nfse
- Modelo de dados (conta × empresa): https://docs.spedy.com.br/guides/conceitos-modelo-de-dados
- Reforma Tributária: https://docs.spedy.com.br/guides/reforma-tributaria
- Preços: https://spedy.com.br/precos

### Contexto e bibliotecas de referência
- EY — Layouts da NFS-e (jul/2026): https://www.ey.com/content/dam/ey-unified-site/ey-com/pt-br/campaigns/reforma-tributaria/documents/ey-serie-reforma-tributaria-layouts-da-nfs-e-2026.pdf
- Obrigatoriedade por perfil: https://triviumcontabil.com.br/?p=17554
- Requisitos técnicos da API nacional: https://notagateway.com.br/?p=6164
- Exemplo de implementação (Laravel): https://packagist.org/packages/rumbleh/laravel-nfse
- Focus NFe — preços: https://focusnfe.com.br/preco

---

## 9. Custos e precificação

> Base para definir quanto cobrar pelo módulo NFS-e. Os valores da Spedy vêm
> da proposta recebida em 2026-10-13. Os demais custos são premissas a
> confirmar.

### Proposta Spedy (API)

| | API 1k | API 3k |
|---|---:|---:|
| Mensalidade | R$ 129,00 | R$ 289,00 |
| Notas inclusas/mês | 1.000 | 3.000 |
| CNPJs emissores | até 30 | até 50 |
| Nota adicional | R$ 0,161 | R$ 0,120 |
| Custo médio/nota (franquia cheia) | R$ 0,129 | R$ 0,096 |

- Inclusos nos dois: API REST, cálculo automático de impostos, contingência
  automática, dashboard, armazenamento por 5 anos, onboarding assistido e
  atendimento prioritário.
- O plano é da **conta** Dolomiti: notas e CNPJs formam um **pool** dividido
  por todos os clientes emissores (modelo conta × empresa, §4).
- **Troca de plano:** o 3k fica mais barato a partir de **~1.994 notas/mês**
  na conta (129 + 0,161 × (N − 1.000) = 289) ou ao passar de **30 CNPJs**.
- Acima de 50 CNPJs não há preço na proposta (ver §7).

### Fatura Spedy por volume da conta

| Notas/mês | API 1k | API 3k | Custo médio/nota |
|---:|---:|---:|---:|
| 500 | **R$ 129,00** | R$ 289,00 | R$ 0,258 |
| 1.000 | **R$ 129,00** | R$ 289,00 | R$ 0,129 |
| 1.500 | **R$ 209,50** | R$ 289,00 | R$ 0,140 |
| 2.000 | R$ 290,00 | **R$ 289,00** | R$ 0,145 |
| 3.000 | R$ 451,00 | **R$ 289,00** | R$ 0,096 |
| 5.000 | R$ 773,00 | **R$ 529,00** | R$ 0,106 |
| 10.000 | R$ 1.578,00 | **R$ 1.129,00** | R$ 0,113 |

Em negrito, o plano mais barato (sem considerar o limite de CNPJs).

- Até 1.000 notas a fatura é **fixa**. O risco está no início, com poucos
  clientes dividindo os R$ 129.
- Acima da franquia, cada nota custa **R$ 0,161** (1k) ou **R$ 0,120** (3k).
  Para precificar, usar **R$ 0,161** como custo por nota (pior caso).

### Custo Spedy por CNPJ

Fatura do melhor plano ÷ CNPJs ativos, conforme o volume médio por CNPJ:

| CNPJs ativos | 30 notas/CNPJ | 100 notas/CNPJ | 200 notas/CNPJ |
|---:|---:|---:|---:|
| 5 | R$ 25,80 | R$ 25,80 | R$ 25,80 |
| 10 | R$ 12,90 | R$ 12,90 | R$ 28,90 |
| 20 | R$ 6,45 | R$ 14,45 | R$ 20,45 |
| 30 | R$ 4,30 | R$ 9,63 | R$ 21,63 |
| 50 | R$ 5,78 | R$ 10,58 | R$ 22,58 |

- Nesses cenários a Spedy custa **até ~R$ 29 por CNPJ/mês**. O preço final
  depende mais do **suporte** e do valor percebido do que da fatura Spedy.

### Outros custos da Dolomiti

| Item | Tipo | Valor |
|---|---|---|
| Desenvolvimento do módulo (adaptador, telas, webhook) | Único | _a estimar_ (h × custo-hora) |
| Onboarding do CNPJ (empresa na Spedy, A1, códigos de serviço, nota de teste) | Único, por CNPJ | Trabalho próprio, cobrado na implantação (R$ 1.000) |
| Suporte (rejeições, cadastro de serviço, dúvidas fiscais) | Mensal, por CNPJ | Trabalho próprio, pago pela margem `m` |
| Troca anual do certificado A1 | Anual, por CNPJ | Trabalho próprio, pago pela margem `m` |
| Infra (webhook na VM de borda, jobs) | Mensal | ~R$ 0 marginal ([arquitetura OCI](arquitetura-migracao-oci.md) §10) |
| Impostos sobre o faturamento da Dolomiti | % da receita (`t`) | MEI: DAS fixo por mês, `t` = 0 |

### Modelo de cobrança

Cobrar por **CNPJ emissor**: é a unidade que a Spedy limita e a que gera
trabalho de onboarding e suporte. Cliente com filiais emitindo conta como mais
de um CNPJ.

1. **Implantação** (única): **R$ 1.000,00**, cobre as horas de onboarding.
2. **Mensalidade** com **franquia**: planos de **100, 200 e 300 NFS-e/mês**, à
   escolha do cliente — **R$ 135, R$ 162 e R$ 188**.
3. **Excedente** por nota acima da franquia: **R$ 1,35, R$ 0,81 e R$ 0,63**,
   conforme o plano.

> **Decisão (2026-10-13):** precificar para **2 clientes**, com `m` = 40% e
> valores arredondados para cima. O primeiro cliente fechado já paga a
> mensalidade da Spedy (R$ 135 ≥ R$ 129).

### Fórmulas

```
Preço = Custo ÷ (1 − t − m)
  t = impostos sobre o faturamento (MEI: 0)
  m = margem desejada, como fração do preço
```

- **Por que dividir:** com custo de R$ 60 e `m` = 40%, o preço é
  60 ÷ 0,6 = R$ 100 e sobram R$ 40, que são 40% do preço. Multiplicar
  (60 × 1,4 = R$ 84) deixa só R$ 24, ou 29% do preço.
- **MEI:** o DAS é fixo por mês, então não há imposto por venda (`t` = 0).
  Suporte e onboarding são trabalho próprio: a margem `m` paga esse tempo,
  além do lucro.
- ⚠️ **Teto do MEI:** R$ 81 mil/ano de faturamento total (confirmar o valor
  vigente). Acima dele a Dolomiti muda de regime e `t` volta a contar.

```
Mensalidade(F) = Base + F × Preço da nota                          arredondada para cima, ao real
  Base          = (mensalidade Spedy ÷ nº de clientes) ÷ (1 − m)   igual em todos os planos
  Preço da nota = R$ 0,161 ÷ (1 − m)                               R$ 0,27 com m = 40%
  F             = franquia do plano (100, 200 ou 300)

Excedente(F) = Mensalidade(F) ÷ F                                  arredondado para cima, ao centavo
Implantação  = R$ 1.000 (valor único)
```

- A **Base** divide a mensalidade fixa da Spedy (R$ 129 no 1k, R$ 289 no 3k)
  entre os clientes.
- Cada nota da franquia é precificada pelo custo de uma nota excedente na
  Spedy (R$ 0,161). Até a conta passar de 1.000 notas/mês, essas notas já
  estão pagas nos R$ 129 e viram margem extra — uma reserva para quando o pool
  encher.
- O excedente é o **preço médio por nota do próprio plano**: a nota além da
  franquia custa o mesmo que uma nota dentro dela.

### Planos com 2 clientes (`m` = 40%)

| Plano | Base | Notas da franquia | Calculado | Mensalidade | Excedente |
|---|---:|---:|---:|---:|---:|
| 100 NFS-e | R$ 107,50 | R$ 26,83 | R$ 134,33 | **R$ 135,00** | **R$ 1,35** |
| 200 NFS-e | R$ 107,50 | R$ 53,67 | R$ 161,17 | **R$ 162,00** | **R$ 0,81** |
| 300 NFS-e | R$ 107,50 | R$ 80,50 | R$ 188,00 | **R$ 188,00** | **R$ 0,63** |

Base = (129 ÷ 2) ÷ 0,6. Notas da franquia = F × 0,161 ÷ 0,6. Excedente =
Mensalidade ÷ F.

**Excedente:**

- Subir de plano compensa cedo: do 100 para o 200 acima de **120 notas/mês**
  (135 + 20 × 1,35 = R$ 162), e do 200 para o 300 a partir de **233**
  (162 + 33 × 0,81 = R$ 188,73).
- Margem do excedente quando a conta passa de 1.000 notas: 88% (plano 100),
  80% (200) e 74% (300). Antes disso, 100%.
- ⚠️ R$ 1,35 fica acima da referência de mercado (R$ 0,35–0,62 por nota
  excedente nos planos self-service da Spedy, §4). Empurra o cliente para o
  plano 200, mas pode pesar na negociação.

**Resultado mensal** (até 2 × 300 = 600 notas a conta fica abaixo das 1.000,
e a fatura Spedy fica em R$ 129; sem excedente e sem implantação):

| Cenário | Receita/mês | Fatura Spedy | Sobra/mês | Margem |
|---|---:|---:|---:|---:|
| 1 cliente no 100 | R$ 135,00 | R$ 129,00 | R$ 6,00 | 4% |
| 1 cliente no 300 | R$ 188,00 | R$ 129,00 | R$ 59,00 | 31% |
| 2 clientes no 100 | R$ 270,00 | R$ 129,00 | R$ 141,00 | 52% |
| 2 clientes no 200 | R$ 324,00 | R$ 129,00 | R$ 195,00 | 60% |
| 2 clientes no 300 | R$ 376,00 | R$ 129,00 | R$ 247,00 | 66% |

- Com 2 clientes a margem passa dos 40% porque as notas da franquia ainda não
  custam nada a mais.
- **Implantação:** cada R$ 1.000 paga 7,75 meses da fatura Spedy. Primeiro ano
  com 1 cliente no plano 100: R$ 2.620 de receita (1.000 + 12 × 135) −
  R$ 1.548 de Spedy (12 × 129) = **R$ 1.072**.

### Preço conforme a base de clientes

Análise que levou à decisão de precificar para 2 clientes (valores calculados,
sem arredondamento). A Base cai à medida que entram clientes. A última coluna
mostra o resultado com os 2 clientes atuais no plano 100 (pior caso):

| Precificar para | Base | Plano 100 | Plano 200 | Plano 300 | Resultado com 2 clientes |
|---:|---:|---:|---:|---:|---:|
| 2 clientes | R$ 107,50 | R$ 134,33 | R$ 161,17 | R$ 188,00 | +R$ 139,67/mês |
| 5 clientes | R$ 43,00 | R$ 69,83 | R$ 96,67 | R$ 123,50 | +R$ 10,67/mês |
| 10 clientes | R$ 21,50 | R$ 48,33 | R$ 75,17 | R$ 102,00 | −R$ 32,33/mês |

- Precificar para 2 clientes cobre tudo desde o início, mas põe o plano 100
  a R$ 134.
- Mirando 5 clientes, os 2 atuais já pagam a fatura Spedy, com pouca sobra.
- Mirando 10, faltam ~R$ 32/mês até a base crescer.
- Baixar o preço depois é fácil; subir é difícil.

### Spedy × integração direta (custo)

- A integração direta zera a fatura, mas troca por horas internas (notas
  técnicas, custódia de A1, DANFSe — §3). Só compensa quando a fatura
  Spedy/mês supera as horas de manutenção/mês × custo-hora.
- A cada R$ 100/h de custo interno, a fatura de R$ 289 (3k) equivale a
  **~2,9 h/mês** e a de R$ 1.129 (10 mil notas) a **~11 h/mês**. Com o ritmo
  de mudanças de 2026 (§2), é difícil manter a direta com menos que isso — o
  que reforça a recomendação do §1.

---

## Changelog

- **2026-10-09:** versão inicial da análise (direta × Spedy), com recomendação
  de começar por intermediário atrás de um adaptador próprio.
- **2026-10-13:** adicionada a seção de custos e precificação (§9) com a
  proposta da API Spedy (planos 1k e 3k). Atualizados §1, §4, §5 e §7.
  Na mesma data, §9 ajustada para MEI (`t` = 0), 2 clientes iniciais e planos
  de 100/200/300 NFS-e. Definida a tabela de preços: implantação de R$ 1.000,
  mensalidades de R$ 135/162/188 e excedente de R$ 1,35/0,81/0,63.
