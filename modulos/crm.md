# Módulo CRM

Extensão do ERP (Oracle + APEX) para registrar **atendimentos** dos representantes aos clientes e apoiar o acompanhamento comercial. Convenções gerais em [../convencoes/](../README.md).

## 1. Visão geral / objetivo
- Registrar interações (atendimentos) e os **produtos oferecidos** em cada uma.
- **Agendar o próximo contato** (data e hora) quando o cliente pede retorno, já durante o atendimento.
- Dar ao representante um **dashboard** (página principal) com o "meu dia": agenda, lembretes, aniversários, atendimentos e funil.
- Base para um **funil de vendas** a partir do status dos itens oferecidos.

## 2. Modelo de dados
Tabelas do módulo (schema `TF`; DDL em `app/desenv/tabelas_crm.sql`):

| Tabela | Papel | Observações |
|---|---|---|
| `TF_ATENDIMENTO` | atendimento | tem `ID_EMPRESA`; `RESULTADO` P/N/E |
| `TF_ATENDIMENTO_ITEM` | itens oferecidos | **sem** `ID_EMPRESA` (deriva do pai); `STATUS` O/A/R/N |
| `TF_CANAL_ATENDIMENTO` | canais | parametrizável por empresa; `ATIVO` S/N, `ORDEM` |
| `TF_AGENDAMENTO` | agendamento do próximo contato | tem `ID_EMPRESA`; `SITUACAO` P/R/C; DDL em `app/desenv/tabelas_agendamento_crm.sql`, log em `app/desenv/logs_agendamento_crm.sql` |
| `TF_PESSOA_REPRESENTANTE` | carteira | estendida com `DATA_INICIO/DATA_FIM/DATA_ALTERACAO/USUARIO_ALTERACAO`; log em `LTF_PESSOA_REPRESENTANTE` |

Tabelas pré-existentes referenciadas: `TF_PESSOA` (cliente), `TF_REPRESENTANTE`, `TF_EMPRESA`, `TF_ITEM` (produtos), `TF_PARAMETROS`.

`TF_AGENDAMENTO` tem duas FKs para `TF_ATENDIMENTO`: **`ID_ATENDIMENTO`** (opcional — atendimento em que o agendamento foi criado) e **`ID_ATENDIMENTO_REALIZADO`** (opcional — atendimento que deu a baixa). `ID_CANAL_ATENDIMENTO` é o canal *previsto* do retorno, também opcional.

### Domínios
- **`TF_ATENDIMENTO.RESULTADO`**: `P` Positivo · `N` Negativo · `E` Em aberto.
- **`TF_ATENDIMENTO_ITEM.STATUS`**: `O` Oferecido · `A` Aceito · `R` Recusado · `N` Em andamento.
  - > O antigo `B` (Em aberto) foi **unificado em `N`** (Em andamento) em 2026-07 — ver changelog.
  - **Pipeline vivo** = `O`, `N`. **Fechados** = `A` (ganho), `R` (perdido).
- **`TF_AGENDAMENTO.SITUACAO`**: `P` Pendente · `R` Realizado · `C` Cancelado.

## 3. Regras de negócio
- **Carteira excludente + vigência por intervalos** (ver [glossário](../convencoes/glossario.md)): cada vínculo tem `[DATA_INICIO, DATA_FIM]`, com `DATA_FIM` **opcional** (nula = corrente/sem fim previsto). Regra: **não pode haver sobreposição** entre vínculos ativos (`BLOQUEADO='N'`) do mesmo cliente. **Vigente hoje** = intervalo que contém `SYSDATE`. Modelo permite **agendar sucessor futuro** (fecha o atual + cria o novo). O cadastro de atendimento **já segue** a exclusão (só atende cliente da própria carteira ou sem vínculo). A mesma regra vale nas telas de **pedido** (págs. 33, 38 e 210) através da LOV `tf_pck_lov.fnc_lov_cliente_representante`, que lista a carteira vigente do rep + os clientes sem vínculo vigente (representante nulo = todos).
- **Aniversário** reutiliza `TF_PESSOA.DATA_NASCIMENTO` comparando **só dia/mês** (ignora ano); PF = aniversário, PJ = fundação (muda só o label).
- **Última data de contato** = `MAX(DATA_ATENDIMENTO)`; cliente sem atendimento = "nunca contatado" (mais crítico).
- **Canais** parametrizáveis por empresa (ativo/ordem).
- **Agendamento do próximo contato:**
  - Respeita a **carteira excludente** (mesma validação do atendimento): só se agenda cliente da própria carteira ou sem vínculo vigente.
  - **Atrasado = por dia**, não por hora (`trunc(DATA_AGENDAMENTO) < trunc(SYSDATE)` com `SITUACAO='P'`). Assim os KPIs "Agenda hoje" e "Agendamentos atrasados" ficam disjuntos e o compromisso das 09h não vira atrasado às 10h do mesmo dia.
  - **Baixa** pelo botão "Registrar atendimento": abre o form de atendimento com o cliente e, ao salvar, o agendamento vira `R` gravando `ID_ATENDIMENTO_REALIZADO`. Não há baixa automática por cliente.
  - **Vários pendentes por cliente são permitidos**; a lista e a coluna "Agendado para" usam sempre o mais próximo (`MIN(DATA_AGENDAMENTO)`).
  - Data/hora no passado é **bloqueada na criação** e liberada na edição (é o próprio reagendamento).

## 4. Parâmetros (`TF_PARAMETROS`, por empresa)
Chave = `DESCRICAO_PARAMETROS`. Leitura via `tf_pck_parametro.fnc_parametro_numerico` (ver [apex.md](../convencoes/apex.md)). Já existe tela genérica de parâmetros no ERP — só precisa de *seed*, sem página nova.

| Parâmetro | Tipo | Uso |
|---|---|---|
| `DIAS_SEM_CONTATO_CRM` | N | limiar do lembrete "sem contato" |
| `DIAS_AVISO_ANIVERSARIO` | N | janela (dias) do aviso de aniversário |
| `DIAS_PROXIMOS_AGENDAMENTOS` | N | janela (dias) da lista "Próximos agendamentos" |

Seed (exemplo, empresa 1):
```sql
Insert into TF_PARAMETROS (DESCRICAO_PARAMETROS,TIPO_DADOS,VALOR_NUMERO,VALOR_DATA,VALOR_CARACTER,DOLOMITI,ID_EMPRESA)
values ('DIAS_SEM_CONTATO_CRM','N',30,null,null,'N',1);
Insert into TF_PARAMETROS (DESCRICAO_PARAMETROS,TIPO_DADOS,VALOR_NUMERO,VALOR_DATA,VALOR_CARACTER,DOLOMITI,ID_EMPRESA)
values ('DIAS_AVISO_ANIVERSARIO','N',7,null,null,'N',1);
Insert into TF_PARAMETROS (DESCRICAO_PARAMETROS,TIPO_DADOS,VALOR_NUMERO,VALOR_DATA,VALOR_CARACTER,DOLOMITI,ID_EMPRESA)
values ('DIAS_PROXIMOS_AGENDAMENTOS','N',7,null,null,'N',1);
```

## 5. Objetos de banco (views)
Arquivos em `app/desenv/`. Sem filtro de sessão (expõem `ID_EMPRESA`); filtros aplicados na região. Ver [multiempresa.md](../convencoes/multiempresa.md).

- **`VW_CRM_CARTEIRA_VIGENTE`** — `ID_PESSOA_REPRESENTANTE, ID_PESSOA, ID_REPRESENTANTE, DATA_INICIO, DATA_FIM, ID_EMPRESA` (vigente hoje = `SYSDATE` entre `DATA_INICIO` e `DATA_FIM`; `DATA_FIM` nula = corrente; `BLOQUEADO='N'`). Empresa via `TF_PESSOA.ID_EMPRESA`.
- **`VW_CRM_ULTIMO_CONTATO`** — `ID_PESSOA, ID_EMPRESA, DATA_ULTIMO_CONTATO, DIAS_DESDE_ULTIMO_CONTATO, QTD_ATENDIMENTOS` (agrega `TF_ATENDIMENTO`).
- **`VW_CRM_ANIVERSARIO`** — `ID_PESSOA, ID_EMPRESA, DATA_NASCIMENTO, DIA_MES, PROX_ANIVERSARIO, DIAS_PARA_ANIVERSARIO, ANOS_A_COMPLETAR`. Próximo aniversário via `ADD_MONTHS` (29/02 cai em 28/02 nos anos não bissextos).
- **`VW_CRM_AGENDAMENTO`** — `ID_AGENDAMENTO, ID_EMPRESA, ID_PESSOA, ID_REPRESENTANTE, ID_ATENDIMENTO, ID_ATENDIMENTO_REALIZADO, ID_CANAL_ATENDIMENTO, DATA_AGENDAMENTO, ASSUNTO, OBSERVACAO, SITUACAO, SITUACAO_DESCRICAO, NOME_CLIENTE, CANAL, DIAS_ATE_AGENDAMENTO, ATRASADO, QUANDO`. `NOME_CLIENTE = nvl(apelido, nome)`; `ATRASADO` é por dia (ver seção 3); `QUANDO` = `Hoje`/`Amanhã`/`DD/MM` + `HH24:MI`. Canal via `LEFT JOIN` (é opcional).

## 6. Telas & queries de apoio — Dashboard "Meu Dia"
Página principal, painel do **representante logado** (`:AI_ID_REPRESENTANTE`). Duas lentes:
- **Minha carteira (proativo):** sem-contato e aniversários → base = carteira vigente do rep.
- **Meus atendimentos (realizado):** histórico e funil → base = `ID_REPRESENTANTE` do atendimento.

Page items lidos no *load*: `P213_DIAS_SEM_CONTATO_CRM`, `P213_DIAS_AVISO_ANIVERSARIO`, `P213_DIAS_PROXIMOS_AGENDAMENTOS`.

> As queries e os processos das telas de agendamento estão reunidos em `app/desenv/apex_crm_agendamento.sql`.

### 6.1 KPIs (query única — badge list)
```sql
WITH k AS (
    SELECT /*+ materialize */
           ( SELECT COUNT(*) FROM tf.tf_atendimento a
              WHERE a.id_representante = :AI_ID_REPRESENTANTE
                AND trunc(a.data_atendimento) = trunc(sysdate)
                AND bitand(a.id_empresa, sys_context('CTX','BIT_EMPRESAS_SELECIONADAS')) = a.id_empresa
           ) AS atendimentos_hoje,
           ( SELECT COUNT(*) FROM tf.vw_crm_carteira_vigente cv
               LEFT JOIN tf.vw_crm_ultimo_contato uc ON uc.id_pessoa = cv.id_pessoa
              WHERE cv.id_representante = :AI_ID_REPRESENTANTE
                AND bitand(cv.id_empresa, sys_context('CTX','BIT_EMPRESAS_SELECIONADAS')) = cv.id_empresa
                AND ( uc.data_ultimo_contato IS NULL
                      OR uc.dias_desde_ultimo_contato > :P213_DIAS_SEM_CONTATO_CRM )
           ) AS sem_contato,
           ( SELECT COUNT(*) FROM tf.vw_crm_carteira_vigente cv
               JOIN tf.vw_crm_aniversario av ON av.id_pessoa = cv.id_pessoa
              WHERE cv.id_representante = :AI_ID_REPRESENTANTE
                AND bitand(cv.id_empresa, sys_context('CTX','BIT_EMPRESAS_SELECIONADAS')) = cv.id_empresa
                AND av.dias_para_aniversario <= :P213_DIAS_AVISO_ANIVERSARIO
           ) AS aniversarios,
           ( SELECT COUNT(*) FROM tf.tf_atendimento_item ai
               JOIN tf.tf_atendimento a ON a.id_atendimento = ai.id_atendimento
              WHERE a.id_representante = :AI_ID_REPRESENTANTE
                AND ai.status IN ( 'O', 'N' )
                AND bitand(a.id_empresa, sys_context('CTX','BIT_EMPRESAS_SELECIONADAS')) = a.id_empresa
           ) AS em_aberto,
           ( SELECT COUNT(*) FROM tf.tf_agendamento ag
              WHERE ag.id_representante = :AI_ID_REPRESENTANTE
                AND ag.situacao = 'P'
                AND trunc(ag.data_agendamento) = trunc(sysdate)
                AND bitand(ag.id_empresa, sys_context('CTX','BIT_EMPRESAS_SELECIONADAS')) = ag.id_empresa
           ) AS agenda_hoje,
           ( SELECT COUNT(*) FROM tf.tf_agendamento ag
              WHERE ag.id_representante = :AI_ID_REPRESENTANTE
                AND ag.situacao = 'P'
                AND trunc(ag.data_agendamento) < trunc(sysdate)
                AND bitand(ag.id_empresa, sys_context('CTX','BIT_EMPRESAS_SELECIONADAS')) = ag.id_empresa
           ) AS agenda_atrasada
      FROM dual
)
SELECT 'Atendimentos hoje'                                                AS label, to_char(atendimentos_hoje,'9G990') AS value, cast(NULL AS NUMBER) AS percent FROM k
 UNION ALL SELECT 'Agenda hoje',                                            to_char(agenda_hoje,'9G990'),     NULL FROM k
 UNION ALL SELECT 'Agendamentos atrasados',                                 to_char(agenda_atrasada,'9G990'), NULL FROM k
 UNION ALL SELECT 'Sem contato +' || :P213_DIAS_SEM_CONTATO_CRM || 'd',      to_char(sem_contato,'9G990'),  NULL FROM k
 UNION ALL SELECT 'Aniversários (próx. ' || :P213_DIAS_AVISO_ANIVERSARIO || ' dias)', to_char(aniversarios,'9G990'), NULL FROM k
 UNION ALL SELECT 'Em aberto',                                              to_char(em_aberto,'9G990'),    NULL FROM k;
```

### 6.2 Lembretes — sem contato
Traz também **"Agendado para"** (próximo agendamento pendente do cliente): quem já tem retorno marcado continua na lista, mas vai para o fim — evita cobrar duas vezes sem esconder informação.
```sql
SELECT p.id_pessoa,
       nvl(p.apelido, p.nome)                    AS nome_cliente,
       uc.data_ultimo_contato,
       uc.dias_desde_ultimo_contato,
       CASE WHEN uc.data_ultimo_contato IS NULL THEN 'Nunca contatado'
            ELSE 'Último contato há ' || uc.dias_desde_ultimo_contato || ' dias' END AS info_contato,
       pa.prox_agendamento,
       to_char(pa.prox_agendamento,'DD/MM HH24:MI') AS agendado_para
  FROM tf.vw_crm_carteira_vigente cv
  JOIN tf.tf_pessoa               p  ON p.id_pessoa  = cv.id_pessoa
  LEFT JOIN tf.vw_crm_ultimo_contato uc ON uc.id_pessoa = cv.id_pessoa
  LEFT JOIN ( SELECT id_pessoa, MIN(data_agendamento) AS prox_agendamento
                FROM tf.tf_agendamento WHERE situacao = 'P'
               GROUP BY id_pessoa ) pa ON pa.id_pessoa = cv.id_pessoa
 WHERE cv.id_representante = :AI_ID_REPRESENTANTE
   AND bitand(cv.id_empresa, sys_context('CTX','BIT_EMPRESAS_SELECIONADAS')) = cv.id_empresa
   AND ( uc.data_ultimo_contato IS NULL
         OR uc.dias_desde_ultimo_contato > :P213_DIAS_SEM_CONTATO_CRM )
 ORDER BY nvl2(pa.prox_agendamento, 1, 0),                -- sem agendamento primeiro
          nvl(uc.dias_desde_ultimo_contato, 99999) DESC;
```

### 6.3 Aniversários da empresa
```sql
SELECT p.id_pessoa,
       nvl(p.apelido, p.nome)          AS nome_cliente,
       av.prox_aniversario,
       av.dias_para_aniversario,
       av.anos_a_completar,
       CASE av.dias_para_aniversario WHEN 0 THEN 'Hoje' WHEN 1 THEN 'Amanhã'
            ELSE to_char(av.prox_aniversario,'DD/MM') END AS quando
  FROM tf.vw_crm_carteira_vigente cv
  JOIN tf.vw_crm_aniversario      av ON av.id_pessoa = cv.id_pessoa
  JOIN tf.tf_pessoa               p  ON p.id_pessoa  = cv.id_pessoa
 WHERE cv.id_representante = :AI_ID_REPRESENTANTE
   AND bitand(cv.id_empresa, sys_context('CTX','BIT_EMPRESAS_SELECIONADAS')) = cv.id_empresa
   AND av.dias_para_aniversario <= :P213_DIAS_AVISO_ANIVERSARIO
 ORDER BY av.dias_para_aniversario, av.prox_aniversario;
```

### 6.4 Atendimentos de hoje
```sql
SELECT a.id_atendimento,
       nvl(p.apelido, p.nome)          AS nome_cliente,
       ca.descricao                    AS canal,
       a.assunto,
       CASE a.resultado WHEN 'P' THEN 'Positivo' WHEN 'N' THEN 'Negativo' WHEN 'E' THEN 'Em aberto' END AS resultado_descricao,
       a.data_atendimento
  FROM tf.tf_atendimento         a
  JOIN tf.tf_pessoa              p  ON p.id_pessoa             = a.id_pessoa
  JOIN tf.tf_canal_atendimento   ca ON ca.id_canal_atendimento = a.id_canal_atendimento
 WHERE a.id_representante = :AI_ID_REPRESENTANTE
   AND trunc(a.data_atendimento) = trunc(sysdate)
   AND bitand(a.id_empresa, sys_context('CTX','BIT_EMPRESAS_SELECIONADAS')) = a.id_empresa
 ORDER BY a.data_atendimento DESC;
```

### 6.5 (A) Distribuição do pipeline vivo — badge list
Itens em aberto (`O`/`N`), do rep, sem limite de data. `value` = quantidade, `valor_reais` = `SUM(valor_oferecido)`, `percent` = participação.
```sql
WITH status_dom AS (
        SELECT 'O' AS status, 'Oferecido' AS label, 1 AS ordem FROM dual
        UNION ALL SELECT 'N','Em andamento',2 FROM dual
), itens AS (
        SELECT ai.status, ai.valor_oferecido
          FROM tf.tf_atendimento_item ai
          JOIN tf.tf_atendimento a ON a.id_atendimento = ai.id_atendimento
         WHERE a.id_representante = :AI_ID_REPRESENTANTE
           AND ai.status IN ('O','N')
           AND bitand(a.id_empresa, sys_context('CTX','BIT_EMPRESAS_SELECIONADAS')) = a.id_empresa
), agg AS (
        SELECT sd.ordem, sd.label, COUNT(i.status) AS qtd, nvl(SUM(i.valor_oferecido),0) AS valor
          FROM status_dom sd LEFT JOIN itens i ON i.status = sd.status
         GROUP BY sd.ordem, sd.label
)
SELECT label,
       to_char(qtd,'9G990')                        AS value,
       to_char(valor,'FML999G999G990D00')          AS valor_reais,
       round(100*qtd/nullif(SUM(qtd) OVER (),0))   AS percent
  FROM agg ORDER BY ordem;
```

### 6.6 (B) Funil de conversão (histórico) — gráfico
Todos os itens do rep, sem limite de data. Estágios **cumulativos** (só temos o status atual do item): `Oferecido(todos) ⊇ Em andamento(N/A) ⊇ Aceito(A)`; `Recusado(R)` à parte (`FUNIL='N'`). Conversão = `percent` da linha Aceito.
```sql
WITH itens AS (
        SELECT ai.status, ai.valor_oferecido
          FROM tf.tf_atendimento_item ai
          JOIN tf.tf_atendimento a ON a.id_atendimento = ai.id_atendimento
         WHERE a.id_representante = :AI_ID_REPRESENTANTE
           AND bitand(a.id_empresa, sys_context('CTX','BIT_EMPRESAS_SELECIONADAS')) = a.id_empresa
), tot AS (
        SELECT /*+ materialize */
               COUNT(*)                                       AS q_ofer,
               COUNT(CASE WHEN status IN ('N','A') THEN 1 END) AS q_and,
               COUNT(CASE WHEN status = 'A' THEN 1 END)        AS q_ace,
               COUNT(CASE WHEN status = 'R' THEN 1 END)        AS q_rec,
               nvl(SUM(valor_oferecido),0)                     AS v_ofer,
               nvl(SUM(CASE WHEN status IN ('N','A') THEN valor_oferecido END),0) AS v_and,
               nvl(SUM(CASE WHEN status = 'A' THEN valor_oferecido END),0)        AS v_ace,
               nvl(SUM(CASE WHEN status = 'R' THEN valor_oferecido END),0)        AS v_rec
          FROM itens
)
SELECT 1 AS ordem,'Oferecido'    AS label, q_ofer AS qtd, v_ofer AS valor, 100 AS percent, 'S' AS funil FROM tot
 UNION ALL SELECT 2,'Em andamento', q_and, v_and, round(100*q_and/nullif(q_ofer,0)), 'S' FROM tot
 UNION ALL SELECT 3,'Aceito',       q_ace, v_ace, round(100*q_ace/nullif(q_ofer,0)), 'S' FROM tot
 UNION ALL SELECT 4,'Recusado',     q_rec, v_rec, round(100*q_rec/nullif(q_ofer,0)), 'N' FROM tot
 ORDER BY ordem;
```

### 6.7 Próximos agendamentos — região do dashboard
Pendentes do rep, **incluindo os atrasados** (sem limite inferior), até a janela de `DIAS_PROXIMOS_AGENDAMENTOS`. Cada linha tem os botões **"Registrar atendimento"** (baixa — ver 6.9) e **"Reagendar"** (abre a modal); `ATRASADO='S'` em destaque.
```sql
SELECT ag.id_agendamento, ag.id_pessoa, ag.nome_cliente, ag.data_agendamento,
       ag.quando, ag.canal, ag.assunto, ag.atrasado, ag.dias_ate_agendamento
  FROM tf.vw_crm_agendamento ag
 WHERE ag.id_representante = :AI_ID_REPRESENTANTE
   AND ag.situacao         = 'P'
   AND bitand(ag.id_empresa, sys_context('CTX','BIT_EMPRESAS_SELECIONADAS')) = ag.id_empresa
   AND trunc(ag.data_agendamento) <= trunc(sysdate) + :P213_DIAS_PROXIMOS_AGENDAMENTOS
 ORDER BY ag.data_agendamento;
```

### 6.8 Minha agenda (IR)
Interactive Report sobre `VW_CRM_AGENDAMENTO` com os mesmos filtros de região, mais itens de período (`DATA_DE`/`DATA_ATE`, default hoje → +30d) e `SITUACAO` (default `P`; nulo = todas). Query em `app/desenv/apex_crm_agendamento.sql` (item 5).

### 6.9 Criar e dar baixa no agendamento
Duas portas de entrada, ambas gravando em `TF_AGENDAMENTO`:
- **Inline no form de atendimento** — região colapsável "Agendar próximo contato" (switch `AGENDAR`, `DATA_PROX_CONTATO`, `HORA_PROX_CONTATO`, `CANAL_PROX_CONTATO`, `ASSUNTO_PROX`, `OBS_PROX`). Data e hora em itens **separados** (melhor no celular), combinados com `to_date(data||' '||nvl(hora,'09:00'),'DD/MM/YYYY HH24:MI')` num processo *After Insert*, que grava `ID_ATENDIMENTO` = atendimento recém-criado.
- **Página modal** — form sobre `TF_AGENDAMENTO` para agendar avulso, reagendar e cancelar. Chamada do atendimento, do dashboard e da Minha agenda.

**Baixa:** o botão "Registrar atendimento" abre o form de atendimento passando `ID_PESSOA` e `ID_AGENDAMENTO`; um segundo processo *After Insert* marca `SITUACAO='R'` e grava `ID_ATENDIMENTO_REALIZADO`.

Validações, LOVs (canal e hora) e o PL/SQL de cada processo estão em `app/desenv/apex_crm_agendamento.sql`.

## 7. Decisões & histórico
- Dashboard = painel do rep logado (`AI_ID_REPRESENTANTE`); empresa por `bitand`; nome do cliente = `nvl(apelido, nome)`.
- Parâmetros lidos por `tf_pck_parametro.fnc_parametro_numerico` com `PRM_ID_EMPRESA`; hoisted para page items `P213_*`.
- Widgets "realizado"/funil: referência de **30 dias** onde há recorte temporal; funil B é **histórico** (sem limite).
- Arquitetura: **views empresa-agnósticas + filtros na região**.

### Changelog
- **2026-08-19** — **LOV de cliente por representante** (`TF_PCK_LOV.fnc_lov_cliente_representante`, usada nas págs. 33, 38 e 210) passou a respeitar a **vigência** da carteira. Antes o `UNION` olhava `TF_PESSOA_REPRESENTANTE` cru (sem `DATA_INICIO`/`DATA_FIM`/`BLOQUEADO`), então: cliente transferido continuava na lista do rep de origem e **não** aparecia para o de destino; cliente com vínculo encerrado ficava invisível para todos; vínculo futuro já reservava o cliente. Reescrita como `SELECT` único sobre `TF_PESSOA` + `EXISTS` (minha carteira vigente) / `NOT EXISTS` (sem dono hoje) contra `VW_CRM_CARTEIRA_VIGENTE`. **Pré-requisito de deploy:** a view precisa existir no ambiente — a query é dinâmica, então a package compila mesmo sem ela e o erro só apareceria em runtime nas telas de pedido.
- **2026-08** — **Agendamento do próximo contato** (pedido do cliente em reunião): nova tabela `TF_AGENDAMENTO` (+ `LTF_AGENDAMENTO`, sequence e triggers), view `VW_CRM_AGENDAMENTO`, parâmetro `DIAS_PROXIMOS_AGENDAMENTOS` e as peças de tela em `app/desenv/apex_crm_agendamento.sql`. Criação pelo form de atendimento **e** por página modal; baixa pelo botão "Registrar atendimento" (amarra `ID_ATENDIMENTO_REALIZADO`); listagem no dashboard (região + 2 KPIs) e na página "Minha agenda". Sem notificação ativa e sem recorrência nesta etapa.
- **2026-07** — Definidos a **validação de sobreposição** do cadastro da carteira (pág. 329) e o processo de **trocar representante** (pág. 445): `DATA_TROCA`, transferência em lote (cliente opcional = todos), encerramento do origem na véspera, sem sobreposição. Ver seção 9.
- **2026-07** — Carteira passou ao modelo de **intervalos com `DATA_FIM` opcional** (nula = corrente) + **não-sobreposição** por cliente (permite agendar sucessor futuro). `VW_CRM_CARTEIRA_VIGENTE` passou a usar `SYSDATE BETWEEN DATA_INICIO e DATA_FIM`. Nova **validação de sobreposição** na tela de cadastro (substitui a checagem antiga de `DATA_FIM IS NULL`).
- **2026-07** — Status do item **`B` (Em aberto) unificado em `N` (Em andamento)**. Domínio passou a `O/A/R/N`. Ajustes: `CHECK`/comentário de `TF_ATENDIMENTO_ITEM`, LOV de status na tela de atendimento, e queries do dashboard (KPI "Em aberto", badge A, funil B). Sem migração de dados (feature ainda não estava em produção).
- **2026-07** — Criadas as views `VW_CRM_CARTEIRA_VIGENTE`, `VW_CRM_ULTIMO_CONTATO`, `VW_CRM_ANIVERSARIO` e as queries do dashboard.

## 8. Pendências / próximos passos
- **Página da Carteira** (Gestão da Carteira — IR + form de manutenção): **pendente**. A validação de sobreposição (pág. 329) e o processo de **trocar representante** (pág. 445) já estão **definidos** — ver seção 9.
- **Ajuste opcional no banco** do domínio de status (remover `B` do `CHECK`/comentário) — feature não está em produção.
- **Widget "Clientes sem representante"** (pool aberto para prospecção) — após finalizar o CRM.
- **Funil visual** (gráfico) como região separada abaixo do dashboard, se desejado além do badge list.
- **Agendamento — telas APEX**: banco pronto (seções 2/5); falta montar a região no form de atendimento, a página modal, a região do dashboard e a "Minha agenda" (seções 6.7–6.9).
- **Agendamento — não entrou nesta etapa**: notificação ativa (e-mail/push/badge no login), calendário nativo do APEX (a view já suporta) e recorrência.

## 9. Carteira — validações e processos (telas APEX)
Modelo de intervalos sem sobreposição (ver seção 3). As validações e o processo vivem nas telas.

**Cadastro do vínculo (pág. 329) — validação de sobreposição** (*PL/SQL returning error text*): impede período que se sobreponha a outro vínculo ativo (`BLOQUEADO='N'`) do mesmo cliente — interseção `ini1 <= fim2 AND ini2 <= fim1`, tratando `DATA_FIM` nula como infinito (`nvl(..., date '9999-12-31')`); exclui o próprio registro na edição (`ID_PESSOA_REPRESENTANTE`).

**Trocar representante (pág. 445):** itens origem, destino e cliente (opcional; nulo = todos). Efetiva em `P445_DATA_TROCA` (default hoje; pode ser futura): destino a partir da data da troca, origem encerra na **véspera** (`troca - 1`), sem sobreposição. Afeta só vínculos **vigentes na data da troca** (`BLOQUEADO='N'`); histórico e agendamentos futuros do origem ficam intactos. Cria um vínculo do destino **por cliente** (`INSERT ... SELECT`). Uma validação de data acompanha o processo (bloqueia se não houver cliente vigente na data, ou se a data não for posterior ao início do vínculo atual).

```sql
declare
  v_troca date := trunc(nvl(:P445_DATA_TROCA, sysdate));
  v_qtd   pls_integer;
begin
  if :P445_ID_REPRESENTANTE_ORIGEM = :P445_ID_REPRESENTANTE_DESTINO then
    raise_application_error(-20001, 'Representante origem e destino não podem ser o mesmo.');
  end if;

  insert into tf_pessoa_representante (id_pessoa, id_representante, bloqueado,
                                       data_inicio, data_fim, usuario_alteracao)
  select pr.id_pessoa, :P445_ID_REPRESENTANTE_DESTINO, 'N', v_troca, null, :PRM_ID_USUARIO
    from tf_pessoa_representante pr
   where pr.id_representante = :P445_ID_REPRESENTANTE_ORIGEM
     and pr.bloqueado        = 'N'
     and (pr.data_inicio is null or trunc(pr.data_inicio) <= v_troca)
     and (pr.data_fim    is null or trunc(pr.data_fim)    >= v_troca)
     and (:P445_ID_PESSOA is null or pr.id_pessoa = :P445_ID_PESSOA);

  v_qtd := sql%rowcount;

  update tf_pessoa_representante
     set data_fim          = greatest(v_troca - 1, trunc(nvl(data_inicio, v_troca - 1))),
         data_alteracao    = sysdate,
         usuario_alteracao = :PRM_ID_USUARIO
   where id_representante   = :P445_ID_REPRESENTANTE_ORIGEM
     and bloqueado          = 'N'
     and (data_inicio is null or trunc(data_inicio) <= v_troca)
     and (data_fim    is null or trunc(data_fim)    >= v_troca)
     and (:P445_ID_PESSOA is null or id_pessoa = :P445_ID_PESSOA);

  if v_qtd = 0 then
    raise_application_error(-20002, 'Nenhum cliente vigente encontrado para o representante de origem na data informada.');
  end if;

  apex_application.g_print_success_message := v_qtd || ' cliente(s) transferido(s) a partir de ' || to_char(v_troca,'dd/mm/yyyy') || '.';
end;
```
