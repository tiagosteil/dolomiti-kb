# Convenções — Multitenancy (filtro por empresa)

O sistema é multitenant. `ID_EMPRESA` é um **bitmask** e a seleção de empresas do usuário vive numa **variável de contexto** — o usuário pode ter **várias empresas selecionadas** ao mesmo tempo.

## Filtro padrão (em toda WHERE que precise filtrar empresa)
```sql
bitand(id_empresa, sys_context('CTX','BIT_EMPRESAS_SELECIONADAS')) = id_empresa
```
O predicado testa se a empresa da linha está **contida** na seleção atual. **Nunca** usar `ID_EMPRESA = :bind`.

### Tabelas sem `ID_EMPRESA`
Filtrar via **join** com a tabela-pai que tem `ID_EMPRESA`:
- `TF_ATENDIMENTO_ITEM` → via `TF_ATENDIMENTO`.
- `TF_PESSOA_REPRESENTANTE` → via `TF_PESSOA` (ou `TF_REPRESENTANTE`).

## Empresa única do usuário (para ler parâmetros)
Diferente do filtro acima (multi-seleção), quando se precisa de **uma** empresa (ex.: ler um parâmetro por empresa) usa-se o page item **`PRM_ID_EMPRESA`**, setado no login com a empresa do usuário. Ver leitura de parâmetros em [apex.md](apex.md).

## Views
Como `sys_context('CTX',...)` é contexto real do banco, o filtro `bitand` **pode** ir dentro de uma view. Por decisão de projeto, porém, as views do CRM ficam **sem** filtro de sessão (expõem `ID_EMPRESA`) e o filtro é aplicado **na região do APEX** — assim as views são validáveis em SQL puro e reutilizáveis. Ver [modulos/crm.md](../modulos/crm.md).
