# Base de Conhecimento — DolomiTI

Documentação viva do sistema (ERP **Oracle + APEX**, multitenant). Use este índice como ponto de entrada. Para tarefas com o Claude: aponte para o arquivo do **módulo** relevante e para as **convenções** correspondentes.

## Convenções (valem para todos os módulos)
- [convencoes/banco.md](convencoes/banco.md) — nomenclatura, tipos, PK por sequence+trigger, auditoria
- [convencoes/multiempresa.md](convencoes/multiempresa.md) — filtro multitenant por empresa (`bitand` + contexto)
- [convencoes/apex.md](convencoes/apex.md) — binds de sessão, LOVs, plugin *badge list*, leitura de parâmetros
- [convencoes/glossario.md](convencoes/glossario.md) — termos do negócio

## Módulos
- [modulos/crm.md](modulos/crm.md) — CRM: atendimentos, itens oferecidos, canais, carteira, dashboard

## Arquitetura e análises
- [arquitetura-migracao-oci.md](arquitetura-migracao-oci.md) — migração para OCI: ADB privado, VM de borda, VM do JRI, integrações bancárias, custos
- [analise-producao-oci-vm-docker.md](analise-producao-oci-vm-docker.md) — produção em VM na OCI com Oracle Free em Docker: licença, limites, custos, comparação com ATP/APEX Service/Base Database e critérios de decisão
- [migracao-oci-importacao-tf.md](migracao-oci-importacao-tf.md) — importação do owner TF no Oracle Free: inventário da produção, o que fica fora do schema, decisões (senhas, e-mail, owners), script de pré-import, ACLs, conferência e patch dos PDFs no log
- [analise-integracao-nfse.md](analise-integracao-nfse.md) — NFS-e: API nacional (Sefin) × intermediário (Spedy), custos e precificação, recomendação e itens em aberto

## Infraestrutura
- [proxy-reverso.md](proxy-reverso.md) — proxy reverso da produção: node4ords (entrada), suez (saída e mTLS do Sicoob), troca de certificado, diagnóstico e substituição pelo nginx na OCI

## Site
- [site-institucional.md](site-institucional.md) — site público: estrutura, formulário de WhatsApp, publicação e pendências

## Pastas fora desta KB
Desde 2026-11-10 esta KB é o repositório `dolomiti-kb` no GitHub. Os caminhos `app/`, `site/` e `Infra/` citados nos documentos continuam na pasta `DolomiTI/` do Google Drive: fontes PL/SQL, patches, relatórios, exports, cópias do proxy e do site.

`app/proxy/` e `Infra/` têm certificados e senhas em texto. Podem ser lidos, mas nenhum trecho com segredo entra neste repositório.

## Decisões
ADRs em [decisoes/](decisoes/): o porquê de cada escolha, o que foi recusado e como reverter.

| ADR | Título | Status |
|---|---|---|
| [0001](decisoes/0001-producao-em-oracle-free-em-duas-vms.md) | Produção em Oracle Free 26ai, em Docker, em duas VMs na OCI | Proposta até o teste de carga (Tiago, 2026-11-04) |
| [0002](decisoes/0002-risco-de-licenca-do-free-assumido.md) | Risco de licença do Oracle Free assumido, sem consulta à Oracle | Aceita 2026-11-04 (Tiago) |
| [0003](decisoes/0003-dev-em-a1-com-o-compose-da-producao.md) | Desenvolvimento em VM A1 Always Free, com o compose e as imagens da produção | Aceita 2026-11-05 (Tiago) |
| [0004](decisoes/0004-nginx-no-lugar-de-node4ords-e-suez.md) | nginx no lugar do node4ords e do suez | Aceita 2026-11-06 (Tiago) |
| [0005](decisoes/0005-importar-so-o-owner-tf.md) | Importar só o owner TF; `APEXREP` e `DOLOMITI` ficam para trás | Aceita 2026-11-10 (Tiago) |
| [0006](decisoes/0006-reset-de-senhas-com-hash-novo.md) | Reset geral de senhas, com hash novo, na virada | Aceita 2026-11-10 (Tiago) |
| [0007](decisoes/0007-email-por-smtp-fora-da-migracao.md) | E-mail por SMTP fica fora da migração | Aceita 2026-11-10 (Tiago) |
| [0008](decisoes/0008-arquivos-e-senhas-fora-dos-logs.md) | Os logs `LTF_` não guardam arquivo nem senha | Aceita e aplicada 2026-11-10 (Tiago) |
| [0009](decisoes/0009-jri-le-pelo-apexrep-vazio-e-so-de-leitura.md) | O JRI lê pelo `APEXREP`, vazio e só de leitura | Aceita 2026-11-10 (Tiago) |
| [0010](decisoes/0010-tf-sem-a-role-dba.md) | O TF nasce sem a role `DBA`; privilégios só diretos e conforme a necessidade | Aceita 2026-11-10 (Tiago) |

## Runbooks e lições
- [runbooks/](runbooks/) — procedimentos repetíveis. Nenhum ainda.
- [licoes/_indice.md](licoes/_indice.md) — regras aprendidas na operação, carregadas em toda sessão do Claude Code.

## Como manter esta KB
Regras de operação, convenções e o ciclo de decisões e lições ficam no [CLAUDE.md](CLAUDE.md). O Claude Code o lê em toda sessão, e ele vale também para quem edita à mão.

Depois de clonar, ativar uma vez o bloqueio de segredos no commit:

```
git config core.hooksPath scripts/git-hooks
```
