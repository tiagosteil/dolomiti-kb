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

## Como manter esta KB
- **Um assunto por arquivo**; mantenha os **títulos estáveis** (não renomear seções).
- Decisões com **data absoluta** + um **changelog** curto no fim de cada módulo.
- Convenções *cross-cutting* ficam em `convencoes/` e os módulos apenas **referenciam** (não repetem).
- Quando um módulo crescer muito, quebre em subarquivos (ex.: `crm-dashboard.md`) e liste aqui.
