# Dolomiti — instruções para o agente

> Ler inteiro antes de qualquer operação. As lições em `licoes/_indice.md` são carregadas no fim deste arquivo e valem como regra.

## O que é este repositório

Base de conhecimento da **Dolomiti** (DolomiTI), empresa dos sócios **Tiago** e **Chico**. O produto é um ERP em **Oracle + APEX**, multiempresa: schema `TF`, app APEX 130, relatórios no JRI (JasperReportsIntegration) e integrações bancárias (Sicoob com mTLS, Sicredi). Aqui ficam as convenções de código, os módulos, as análises, as decisões, os runbooks e as lições.

- **Produção (2026-11):** uma VM na Locaweb (CentOS) com Oracle XE 11g e APEX 20.1, node4ords na entrada e suez na saída ([proxy-reverso.md](proxy-reverso.md)).
- **Foco atual:** levar DEV e PROD para VMs na OCI com Oracle Free 26ai em Docker ([análise](analise-producao-oci-vm-docker.md)). O estado de cada frente fica no [README.md](README.md) e nos documentos do assunto, não aqui.
- **Fora da KB:** fontes PL/SQL, patches, relatórios, exports e cópias do proxy e do site ficam na pasta `DolomiTI/` do Google Drive (`app/`, `site/`, `Infra/`). No Mac do Tiago: `~/Library/CloudStorage/GoogleDrive-<conta>/My Drive/DolomiTI/`. Busca recursiva na pasta inteira passa de 3 min: restringir a `app/` ou `Infra/`.

## Regras de operação

1. **Segredo nunca em arquivo versionado.** Senha, PFX, wallet, token, chave e string de conexão com senha ficam fora do repositório; nos arquivos, só placeholder (`${VARIAVEL}`, `<senha>`, `&senha` no SQL*Plus). `app/proxy/` e `Infra/`, no Drive, têm PFX e senhas em texto: ler se for útil, mas nunca copiar trecho com segredo para a KB nem repeti-lo na resposta. Um hook bloqueia a gravação e o pre-commit bloqueia o commit; se dispararem, não contornar: mover o valor.
2. **Produção só com alvo confirmado.** Antes de qualquer comando contra servidor, banco ou console da OCI, dizer qual host, banco ou compartimento e o que será feito, e esperar confirmação.
3. **Banco pelo SQLcl MCP com o destino conferido.** No SQLcl do Tiago, `Dolomiti TF - PROD` e `Dolomiti - TF - Desenv` usam a mesma string (`localhost:3521/xe`): o nome não garante o banco de destino. A leitura em PROD pelo agente é bloqueada pela política de permissões; não contornar pela conexão Desenv, e sim pedir ao usuário para rodar a consulta ou liberar o acesso. `Dev OCI - tiago.steil` apontava para o ADB `DEVDOLOMITI`, encerrado em 2026-11-10: não usar. Conexões com outros nomes não são da Dolomiti.
4. **Mudança destrutiva só com volta planejada.** DDL ou patch na produção, import, restore, recriar o contêiner do banco ou apagar volume: confirmar backup recente e escrever o plano de reversão *antes*.
5. **Execução um passo por vez.** Em roteiros práticos (console da OCI, servidor, banco), mandar só o passo atual, com o que conferir no fim, e esperar o retorno (print ou resultado) antes do próximo. O passo seguinte pode ser citado em uma linha. Análises e decisões continuam podendo ser completas.
6. **Nada de dado de cliente em docs.** Sem nome, CPF/CNPJ, e-mail ou telefone de cliente, dados de boleto ou conteúdo de PDF. Exemplos de consulta usam IDs ou dados inventados.
7. **Documentar na mesma sessão.** Mudou servidor, banco, rede ou decisão? Atualizar o documento do assunto (tabela de andamento, changelog) antes de encerrar.

## Fontes de verdade

| Assunto | Onde confiar | Não usar |
|---|---|---|
| Código atual do banco | `dba_source` na produção, em consulta rodada pelo usuário | `app/prod/1.0` e `2.0` (2017–2018): divergem da produção (ex.: `TF_PCK_AUTENTICACAO`) |
| Fontes locais mais recentes | `app/patch/<versão>/` | — |
| Proxy reverso e mTLS do Sicoob | [proxy-reverso.md](proxy-reverso.md) | `DolomiTI/app/proxy/Proxy_reverso_dolomiti.md`, substituído |
| SQL, PL/SQL e APEX | [convencoes/](convencoes/): ler antes de escrever código | — |
| Plano da migração | [analise-producao-oci-vm-docker.md](analise-producao-oci-vm-docker.md) | [arquitetura-migracao-oci.md](arquitetura-migracao-oci.md) como plano: o desenho com ATP vale só como referência de rede, nginx, JRI e integrações |

## Ciclo de auto-aprendizado

A KB fica mais inteligente a cada sessão por um ciclo simples, e girá-lo é responsabilidade do agente:

| Quando | O que fazer |
|---|---|
| Algo quebrou, surpreendeu ou custou tempo | skill `registrar-licao` |
| Escolha de arquitetura, fornecedor, versão ou padrão | skill `registrar-decisao` (ADR) |
| Um procedimento foi executado pela 2ª vez | virar runbook em `runbooks/` |
| A mesma lição apareceu 2 vezes | propor promovê-la a regra neste arquivo: mostrar o diff e pedir aprovação, nunca editar calado |

Lição que não muda comportamento é diário, não lição. Registre a **regra**, não a história.

## Estrutura

| Caminho | Conteúdo |
|---|---|
| `README.md` | Índice: ponto de entrada e lista de documentos |
| `convencoes/` | Padrões de banco, multiempresa, APEX e glossário; os módulos referenciam, não repetem |
| `modulos/` | Um arquivo por módulo do ERP |
| `*.md` na raiz | Análises e arquitetura: migração para a OCI, importação do TF, proxy, NFS-e, site |
| `decisoes/` | ADRs numerados: o *porquê* de cada escolha |
| `runbooks/` | Procedimentos repetíveis |
| `licoes/` | Lições; `_indice.md` é carregado em toda sessão |
| `scripts/seguranca/` | Verificação de segredos, usada pelo hook do Claude Code e pelo pre-commit do git |
| `.claude/` | Hook e skills do projeto |

## Convenções

- Português brasileiro em tudo. Datas ISO `AAAA-MM-DD`, sempre absolutas.
- Arquivos em kebab-case. ADR: `NNNN-titulo.md`. Lição: `AAAA-MM-DD-titulo.md`.
- Um assunto por arquivo, uma casa por assunto: referenciar por link, nunca copiar. Títulos de seção estáveis, porque outros documentos apontam para eles. Changelog curto no fim de cada documento. Documento que crescer demais vira subarquivos listados no `README.md`.
- Imagens Docker sempre com versão fixa, nunca `latest`.
- Commit com prefixo — `docs:` para conteúdo, `kb:` para a estrutura da KB (skills, hooks, scripts) — seguido do que mudou. Conferir `git diff --cached --stat` antes. **Push logo depois de cada commit**, com `git pull --rebase` antes. Nunca force push.
- Cada clone ativa o pre-commit uma vez: `git config core.hooksPath scripts/git-hooks`.

## Lições ativas

@licoes/_indice.md
