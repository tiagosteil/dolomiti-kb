# 0004 — nginx no lugar do node4ords e do suez

- **Status:** Aceita
- **Data:** 2026-11-06
- **Quem decidiu:** Tiago
- **Revisar em:** se a homologação na VM de desenvolvimento mostrar que login, POSTs ou modais do APEX, ou o mTLS do Sicoob, não funcionam atrás do nginx

## Contexto

Na produção, dois apps Node fazem o proxy reverso ([proxy-reverso.md](../proxy-reverso.md)). O **node4ords** recebe a internet e entrega ao ORDS, aos estáticos e ao site. O **suez** recebe as chamadas do banco (`http://<nome>.localhost:3000/...`), escolhe o destino pelo nome e, no Sicoob, apresenta o PFX do cliente (mTLS).

Os dois estão abandonados: o suez teve o último commit em 2018 e foi arquivado em 2024, e o node4ords teve o último commit em 2016. Ambos dependem do `http-proxy-middleware` 0.17, rodam como root e devolvem stack trace a quem chama. Em 2026-11-06, uma senha de PFX desatualizada numa das ocorrências do settings do suez derrubou a busca do token do Sicoob ([proxy-reverso.md, §5](../proxy-reverso.md#5-riscos)).

As imagens oficiais da Oracle não trazem proxy, então algum proxy tem de ser montado na VM de aplicação do [ADR 0001](0001-producao-em-oracle-free-em-duas-vms.md).

## Opções consideradas

- **Levar node4ords e suez como estão:** zero mudança de configuração, mas carrega projetos sem correção de segurança para a máquina exposta à internet.
- **Load balancer da OCI na entrada:** resolve só a entrada. A saída com mTLS continua exigindo uma VM, então o LB só entra quando alta disponibilidade for requisito ([arquitetura, §8](../arquitetura-migracao-oci.md#8-notas-de-decisão-racional)).
- **mTLS dentro do banco (`UTL_HTTP` com wallet):** a chave privada do cliente ficaria no banco sem patches. No ADB, nem era possível ([arquitetura, §5](../arquitetura-migracao-oci.md#5-integrações-de-saída-webservices-de-bancos)).
- **nginx nos dois papéis:** escolhida.

## Decisão

Na VM de aplicação, o **nginx** assume a entrada (TLS com certbot, redirecionamento HTTP → HTTPS, proxy para o ORDS em `127.0.0.1`, estáticos, site e `Permissions-Policy`) e a saída: um `server` por nome `*.localhost`, escutando no IP privado na porta 3000, com mTLS por `proxy_ssl_certificate`.

Os apps Node não migram. O banco continua chamando os mesmos nomes, que o `extra_hosts` do compose aponta para a VM de aplicação. Por isso o código PL/SQL não muda. O mapeamento completo está em [proxy-reverso.md, §6](../proxy-reverso.md#6-migração-para-a-oci-nginx-no-lugar-dos-apps-node).

## Consequências

### O que fica mais fácil

- Pacote da distribuição, atualizado normalmente.
- `nginx -t` valida a configuração antes de aplicar, e `systemctl reload nginx` aplica sem derrubar conexões.
- Os erros vão para o `error.log`, não para a tela do usuário do APEX.
- Cada senha de certificado fica num único arquivo, o que evita a falha de 2026-11-06.

### O que fica mais difícil

- O nginx não lê PFX: cada certificado do Sicoob vira PEM (certificado, cadeia e chave cifrada) a cada troca. No OpenSSL 3, um PFX antigo pode exigir `-legacy`.
- A configuração é montada do zero. Falta validar na homologação se o ORDS 26 ainda exige a troca do `Origin` que o node4ords faz.
- Cada cliente Sicoob novo continua exigindo um nome novo no proxy, como hoje.

## Como reverter

Instalar o suez e o node4ords na VM de aplicação com os settings atuais. O banco chama os mesmos nomes e portas, então nada muda do lado do banco.

## Fontes

- [proxy-reverso.md](../proxy-reverso.md), §5 e §6 (2026-11-06).
- [arquitetura-migracao-oci.md](../arquitetura-migracao-oci.md), §5 e §8.
- [nginx: `proxy_ssl_certificate` e diretivas relacionadas](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_ssl_certificate) e [guia de HTTPS do uc-local-apex-dev](https://www.united-codes.com/products/uc-local-apex-dev/docs/getting-started/expose-https-reverse-proxy/), consultados em 2026-11-06.
