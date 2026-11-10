# Glossário — termos do negócio

- **Empresa** — tenant do sistema. Filtrada por bitmask (ver [multiempresa.md](multiempresa.md)).
- **Pessoa** (`TF_PESSOA`) — cliente (PF ou PJ). Nome de exibição = `nvl(apelido, nome)`. `DATA_NASCIMENTO` = aniversário (PF) ou fundação (PJ).
- **Representante** (`TF_REPRESENTANTE`) — vendedor. Quem loga como representante tem `AI_ID_REPRESENTANTE` setado.
- **Carteira** (`TF_PESSOA_REPRESENTANTE`) — vínculo cliente↔representante. É **excludente** e **com vigência**:
  - **Excludente:** cliente COM vínculo vigente só é atendido pelo seu representante; SEM vínculo, qualquer representante atende. Regra vale para pedidos e para o CRM.
  - **Vigência (intervalos):** `[DATA_INICIO, DATA_FIM]`, `DATA_FIM` **opcional** (nula = corrente/sem fim previsto). **Sem sobreposição** entre vínculos ativos (`BLOQUEADO='N'`) do mesmo cliente. **Vigente hoje** = intervalo que contém `SYSDATE`. No máximo 1 vigente por cliente hoje.
- **Atendimento** (`TF_ATENDIMENTO`) — interação registrada (cliente, representante, canal, data, assunto, resultado).
- **Item oferecido** (`TF_ATENDIMENTO_ITEM`) — produto oferecido num atendimento, com status.
- **Agendamento** (`TF_AGENDAMENTO`) — compromisso **futuro** com o cliente (data e hora do próximo contato), normalmente criado durante um atendimento. Situação: `P` pendente · `R` realizado · `C` cancelado. **Atrasado** = pendente cujo **dia** já passou (`trunc(DATA_AGENDAMENTO) < trunc(SYSDATE)`) — a hora não conta. Segue a carteira excludente, como o atendimento.
- **Canal** (`TF_CANAL_ATENDIMENTO`) — meio do atendimento (Presencial, Telefone, etc.), parametrizável por empresa.
- **Pipeline vivo** — itens ainda em aberto (status `O`/`N`).
- **Funil de conversão** — visão do caminho até a venda (Oferecido → Em andamento → Aceito), com Recusado à parte.
- **Última data de contato** — `MAX(DATA_ATENDIMENTO)` do cliente.
