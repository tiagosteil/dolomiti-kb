---
name: registrar-decisao
description: Registra uma decisão técnica da Dolomiti como ADR numerado em decisoes/ — infraestrutura na OCI, banco Oracle, APEX/ORDS, Docker, nginx, integrações bancárias, JRI, NFS-e, padrão de código — ou a revisão de uma decisão anterior. Usar quando uma escolha técnica for feita ou revista, ou quando o usuário disser "vamos com", "decidimos", "decidi", "registra a decisão", "por que escolhemos isso".
---

# Skill: registrar-decisao

Um ADR guarda o **porquê**. O código e as análises mostram o que foi feito; só o ADR mostra o que foi recusado e o que se aceitou perder.

## Fluxo

1. **Verificar se já existe decisão sobre o tema:** `grep -ril "<tema>" decisoes/`. Se existir e continuar válida, não criar outra. Se a nova contradiz a antiga, a antiga passa a `Substituída por NNNN`, com link.
2. **Numerar:** próximo número sequencial de 4 dígitos. Arquivo `decisoes/NNNN-titulo-em-kebab-case.md`, a partir de `_template.md`.
3. **Preencher com honestidade:**
   - *Opções consideradas* com pelo menos 2 alternativas reais e o motivo de cada uma ter perdido.
   - *O que fica mais difícil* nunca vazio: toda decisão tem custo; se não achou nenhum, não pensou o bastante.
   - *Como reverter* e *Revisar em* (data ou gatilho observável, como "se o teste de carga falhar").
   - *Fontes*: a análise da KB de onde a decisão saiu (com a seção) e a documentação oficial, com data.
4. **Status:** `Proposta` enquanto depender de teste, de validação ou do outro sócio; `Aceita` só com confirmação explícita do usuário. *Quem decidiu* diz quem confirmou.
5. **Ligar à análise:** no documento de análise de onde a decisão saiu, trocar a explicação longa por uma linha com o link do ADR. Um assunto, uma casa.
6. **Atualizar** a lista de decisões no `README.md`.
7. Se a decisão cria algo que o agente deve seguir sempre, **propor** o acréscimo em "Regras de operação" no `CLAUDE.md`: mostrar o trecho e pedir aprovação.

## Regras

- Uma decisão por ADR.
- Número e preço sempre com data e fonte: eles envelhecem (preço da OCI em reais, limites do Oracle Free, versões).
- Nada de senha, PFX, wallet, IP público de produção ou dado de cliente.
- Proposta comercial e preço para cliente não são ADR: ficam na pasta do cliente no Drive.
