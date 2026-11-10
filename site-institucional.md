# Site institucional — Dolomiti

Site público da Dolomiti Software Solutions: uma única página estática, sem backend e sem banco de dados. É independente do ERP.

> **Última atualização:** 2026-11-03

## 1. Visão geral

| Item | Valor |
|---|---|
| URL pública | https://dolomiti.inf.br/site/ (a raiz `/` redireciona para `/site`) |
| Cópia de trabalho | Google Drive → `DolomiTI/site/` |
| Pasta no servidor | `/var/www/site`, em DESENV e PROD |
| Servidor web | Node/Express (`X-Powered-By: Express`) no servidor de produção CentOS |
| Versionamento | Sem git. Backups manuais `index_bkp_DDMMAAAA.html` na própria pasta, mais o histórico de versões do Drive |

Dados de acesso ao servidor ficam em `Infra/` e **não devem ser copiados para a KB**.

## 2. Estrutura

HTML, CSS e JS sem etapa de build, sobre o template **Transcend** (Colorlib) com jQuery 3.2.1. A licença é CC BY 3.0: o link da Colorlib no rodapé não pode ser removido.

| Arquivo | Conteúdo |
|---|---|
| `index.html` | Todo o conteúdo do site |
| `css/main.css` | Estilos das seções, incluindo os media queries |
| `css/base.css` | Reset, grid e tipografia; importa o Font Awesome |
| `js/main.js` | Comportamento; funções `cl*` chamadas em `clInit` |
| `images/portfolio/` | Miniaturas dos projetos (`g-imgN.png` e `g-imgN@2x.png`) |
| `images/portfolio/gallery/` | Imagens ampliadas dos projetos |
| `images/avatars/` | Logos dos clientes nos depoimentos |

### Seções da página

| Âncora | Conteúdo |
|---|---|
| `#home` | Capa |
| `#about` | Quem somos |
| `#services` | O que fazemos |
| `#works` | 12 projetos em destaque e depoimentos de clientes |
| `#stats` | Números da empresa |
| `#contact` | Formulário de WhatsApp, telefones e rodapé |

### Imagens
Reduzir o tamanho com GIMP (redimensionar) e TinyPNG (comprimir). Cada projeto declara as dimensões da imagem ampliada em `data-size`, que precisa corresponder ao arquivo real.

## 3. Formulário de contato (WhatsApp)

O formulário da seção `#contact` monta uma mensagem e abre uma conversa com o WhatsApp do **Francisco, (51) 99884-4942**.

- **Campos:** Nome (obrigatório), Empresa (opcional) e "Como podemos ajudar?" (obrigatório, até 1.000 caracteres). Não há campo de telefone porque o WhatsApp já identifica o remetente.
- **Envio:** `clContactForm`, em `js/main.js`, abre `https://wa.me/5551998844942?text=...` em nova aba. Se a aba for bloqueada, como pode ocorrer em navegadores embutidos, redireciona a própria página.
- **Sem JavaScript:** o formulário ainda abre o WhatsApp, mas leva só o texto da mensagem.
- **Trocar o número:** alterar apenas o `action` de `#contact-form` em `index.html`, no formato `55` + DDD + número.

Mensagem gerada:

```text
Olá! Vim pelo site da Dolomiti.

*Nome:* João da Silva
*Empresa:* Empresa Exemplo
*Mensagem:* Gostaria de um orçamento.
```

### Decisões (2026-11-03)
- **Link `wa.me` em vez da API do WhatsApp Business.** O site é estático e o link não exige backend, token nem custo por mensagem.
- **O visitante precisa confirmar o envio no WhatsApp.** Essa é uma limitação do `wa.me`, e o texto abaixo do botão avisa sobre isso. Para envio automático, seria preciso adotar a API oficial e criar um backend.
- **Nenhum dado fica no site.** O texto vai direto do navegador do visitante para o WhatsApp, então não há histórico de contatos fora da conversa do Francisco.

## 4. Publicação

1. Copiar `index.html` para `index_bkp_DDMMAAAA.html`.
2. Editar os arquivos em `DolomiTI/site/`.
3. Conferir localmente, abrindo `index.html` no navegador.
4. Copiar para o servidor somente os arquivos alterados.
5. Testar em https://dolomiti.inf.br/site/ e registrar a alteração no changelog abaixo.

O servidor responde com `Cache-Control: max-age=0`, então os navegadores revalidam os arquivos e não é preciso versionar os nomes de CSS e JS.

## 5. Pendências conhecidas

- **Links "Ver Projeto":** os 12 projetos apontam para `https://www.behance.net/`, um endereço genérico do template.
- **Metadados:** "Dolomti" está com erro de digitação em `description` e `keywords`, e `<html lang="en">` deveria ser `pt-BR`.
- **Telefones no contato:** `.contact-number` tem baixo contraste sobre o fundo escuro.
- **Conteúdo desativado:** endereço e redes sociais estão comentados no HTML da seção de contato.

## Changelog

- **2026-11-03** — Documento criado. E-mail fixo `dolomitisoftwaresolutions@gmail.com` (com link quebrado, `mailto:#0`) substituído pelo formulário de WhatsApp em `index.html`, `css/main.css` e `js/main.js`. Segundo telefone corrigido para `+55 (51) 98138-5757`. Backup em `index_bkp_03112026.html`. Envio real testado pelo Tiago: o WhatsApp abriu e a mensagem foi enviada. Publicado em produção no mesmo dia; `index.html`, `css/main.css` e `js/main.js` conferidos, idênticos à cópia local. Envio também testado pelo Tiago no site publicado.
