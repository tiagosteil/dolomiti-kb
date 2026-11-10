# Convenções — APEX

As telas são feitas manualmente; do banco vêm views, funções e queries de apoio (LOVs, validações, regiões).

## Binds de sessão
| Bind | O que é | Uso |
|---|---|---|
| `PRM_ID_EMPRESA` | empresa do usuário, setada no login | ler parâmetros por empresa |
| `AI_ID_REPRESENTANTE` | representante logado (setado quando um usuário representante loga) | filtrar dashboards "do representante" |
| `CTX / BIT_EMPRESAS_SELECIONADAS` | contexto com o bitmask de empresas selecionadas | filtro multitenant (ver [multiempresa.md](multiempresa.md)) |

**Views não enxergam page/application items** (`:AI_...`). Por isso o filtro por representante vai **na região**; o filtro de empresa por `sys_context('CTX',...)` funciona dentro de view, mas por decisão de projeto também fica na região.

## Leitura de parâmetros (TF_PARAMETROS)
Reutilizar a função existente (não criar função nova):
```sql
tf_pck_parametro.fnc_parametro_numerico(pparametro, pid_empresa) return number
```
A chave do parâmetro é a coluna **`DESCRICAO_PARAMETROS`**. Padrão no dashboard: no *load* da página, popular page items com o valor, uma vez só, e referenciá-los nas regiões e nos labels:
```sql
:P213_DIAS_SEM_CONTATO_CRM  := tf_pck_parametro.fnc_parametro_numerico('DIAS_SEM_CONTATO_CRM',  :PRM_ID_EMPRESA);
:P213_DIAS_AVISO_ANIVERSARIO := tf_pck_parametro.fnc_parametro_numerico('DIAS_AVISO_ANIVERSARIO', :PRM_ID_EMPRESA);
```
Assim evita repetir a chamada da função por linha/região e permite **labels dinâmicos** (ex.: `Sem contato +&P213_DIAS_SEM_CONTATO_CRM.d`).

## Plugin de badge list
Formato da query: colunas **`label`**, **`value`**, **`percent`** (uma linha por badge, via `UNION ALL`). `value` costuma vir formatado com `to_char(n,'9G990')`; `percent` **pode ser nulo**. Suporta um valor secundário (ex.: um `VALOR_REAIS` junto com a quantidade).

## Performance de dashboard
- Consolidar os KPIs numa **única query** (uma linha, várias contagens) em vez de uma região por cartão.
- Contas repetidas na mesma página são baratas no *buffer cache* quando o recorte é por representante; não otimizar prematuramente.
