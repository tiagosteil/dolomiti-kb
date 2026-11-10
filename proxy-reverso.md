# Proxy reverso — Dolomiti

> **Status:** em produção na VM da Locaweb (CentOS). Na migração para a OCI, o nginx assume os dois papéis (§6).
> **Última atualização:** 2026-11-10
> **Substitui:** as anotações em `DolomiTI/app/proxy/Proxy_reverso_dolomiti.md`, que não devem mais ser usadas para consulta.

A produção usa dois apps Node como proxy reverso. O **node4ords** recebe o tráfego da internet e o entrega ao APEX/ORDS e aos arquivos estáticos. O **suez** recebe as chamadas que o banco faz para APIs externas e as repassa por HTTPS. No caso do Sicoob, ele também apresenta o certificado do cliente (mTLS).

Senhas, PFX e dados de acesso ao servidor **não devem ser copiados para a KB**.

---

## 1. Visão geral

| | node4ords | suez |
|---|---|---|
| Sentido | Entrada: internet → servidor | Saída: banco → APIs externas |
| Portas | 80 e 443 | 3000, só em `127.0.0.1` |
| Pasta no servidor | A registrar (§7) | `/opt/suez` |
| Configuração | `config.js` (não está na cópia local) | `/opt/suez/config/settings.json` |
| Processo | pm2, nome a registrar | pm2 `proxy-suez`, com `pm2 save` para subir no boot |
| Usuário | root | root |
| Projeto de origem | [OraOpenSource/node4ords](https://github.com/OraOpenSource/node4ords) | [fuzziebrain/suez](https://github.com/fuzziebrain/suez) |

```
Internet ──80/443──► node4ords ──► ORDS / APEX
                        ├────────► /i/ e estáticos
                        └────────► site

Banco (UTL_HTTP / APEX_WEB_SERVICE)
   │  http://apisicoobauth.localhost:3000/auth/...
   ▼
suez (127.0.0.1:3000) ──HTTPS──► https://auth.sicoob.com.br/auth/...
   escolhe o destino pelo          apresenta o PFX do cliente (mTLS)
   nome antes do primeiro ponto
```

### Cópias locais

Ficam em `DolomiTI/app/proxy/` e podem estar atrás do servidor (§3).

| Arquivo | O que é |
|---|---|
| `implantacao_PROD_24032026/` | `app.js` e `settings.json` do suez implantados na produção em 2026-03-24, com os backups anteriores e o PFX |
| `app_suez_DEV*.js`, `settings_DEV*.json` | suez do DEV. O `app.js` é idêntico ao da produção |
| `app_node4ords_DEV_1.js`, `app_node4ords_DEV_2.js` | node4ords do DEV. A versão 2 acrescenta o header `Permissions-Policy` (§2) |
| `bkp/` | Versões do suez anteriores ao mTLS |

---

## 2. node4ords (entrada)

Comportamento lido em `app_node4ords_DEV_2.js` (2026-09-02):

| Função | Como faz |
|---|---|
| HTTPS | Lê chave e certificado de `config.web.https` e sobe o servidor na 443 |
| Forçar HTTPS | `express-force-ssl` redireciona HTTP para HTTPS com 301 |
| APEX/ORDS | `config.ords.path` vai para `config.ords.webContainerUrl`. Em HTTPS, troca `https:` por `http:` no header `Origin` da requisição, porque sem isso o ORDS recusa POSTs por CORS. Nos redirects, troca `http:` por `https:` no `Location` |
| Chrome 146+ | Acrescenta `Permissions-Policy: unload=(self)` às respostas do ORDS, para o APEX conseguir fechar modais e popups de LOV |
| Caminhos antigos | `config.ords.redirectPaths` redireciona para o caminho do ORDS |
| Estáticos | `config.static.path`, imagens do APEX em `config.apex.images.path` e o site em `config.static.site` ([site-institucional.md](site-institucional.md)) |
| Raiz | `/` redireciona para o site |

---

## 3. suez (saída)

### Como escolhe o destino

O banco chama `http://<nome>.localhost:3000/<caminho>`, e o `/etc/hosts` resolve `<nome>.localhost` para `127.0.0.1`. O suez pega o nome antes do primeiro ponto, procura esse nome em `apiTargets` e repassa a chamada para `proxyTarget` + `<caminho>`, trocando o `Host` pelo do destino.

Exemplo: `http://apisicoobauth.localhost:3000/auth/realms/cooperado/protocol/openid-connect/token` vai para `https://auth.sicoob.com.br/auth/realms/cooperado/protocol/openid-connect/token`.

Um nome que não está no settings cai em `http://localhost/`, que é o node4ords. A resposta volta como redirect ou HTML, não como um erro claro.

O suez escuta só em `127.0.0.1`. Se a variável de ambiente `DOCKER` existir, ele passa a escutar em todas as interfaces, na porta 3000.

### Destinos

Lidos do settings da produção de 2026-03-24:

| Nome | Destino | mTLS | Uso |
|---|---|---|---|
| `apisicredi` | `https://api-parceiro.sicredi.com.br/` | Não | Boletos Sicredi |
| `apisicoobauth` | `https://auth.sicoob.com.br/` | Sim, PFX do Jornal Repercussão | Token OAuth do Sicoob |
| `apisicoob` | `https://api.sicoob.com.br/` | Não, nesta cópia (ver nota) | API de cobrança do Sicoob |
| `apisicoobsb` | `https://sandbox.sicoob.com.br/` | Não | Sandbox do Sicoob |
| `viacep` | `https://viacep.com.br/` | Não | A confirmar. O banco também tem ACL direta para `viacep.com.br` |
| `soers`, `secwebhml`, `secwebprd` | Sistemas do governo do RS | Não | A confirmar |
| `contosoapi`, `acmeapi`, `typicode` | Domínios de exemplo | Não | Vieram com o suez. Sem uso |

> **Cópia desatualizada:** em 2026-11-06, o settings do servidor tinha a senha do PFX em **dois** lugares, mas a cópia de 2026-03-24 só tem um bloco `mTLS`. Conferir no servidor quais destinos usam mTLS e atualizar esta tabela (§7).

No banco, a ACL `apex_rest_acl` libera `apisicredi.localhost`, `apisicoob.localhost` e `apisicoobauth.localhost` para o TF e o schema do APEX ([migracao-oci-importacao-tf.md](migracao-oci-importacao-tf.md)). As URLs ficam em `TF_PARAMETROS`, por empresa: `URL_TOKEN_SICOOB`, `URL_CRIA_BOLETO_SICOOB` e `URL_CONSULTA_BOLETO_SICOOB`, lidas pelo `TF_PCK_BOLETO_SICOOB`.

### Como o mTLS funciona

- **Leitura na subida:** para cada destino com `mTLS.enabled`, o suez lê o PFX (`mTLS.pfxPath`) uma vez, quando o processo sobe, e cria um agente HTTPS com o arquivo e a senha (`mTLS.passphrase`). Trocar o arquivo ou a senha exige `pm2 restart proxy-suez`.
- **Senha testada só na primeira chamada:** o restart passa sem erro mesmo com a senha errada.
- **PFX ausente:** se o arquivo não existir na subida, o log do pm2 mostra `Error loading certificate for <nome>` e as chamadas desse nome caem em `http://localhost/`.
- **Um PFX por nome:** hoje há um único beneficiário Sicoob, o Jornal Repercussão (`id_empresa` 16, `id_param_integracao_banco` 3). Um segundo cliente precisa de quatro coisas:
  - outro nome no settings (ex.: `apisicoobauth2`);
  - a linha correspondente no `/etc/hosts`;
  - a ACL no banco;
  - os parâmetros de URL da empresa apontando para o novo nome.

---

## 4. Operação

### Reiniciar e ver logs

```bash
pm2 list
pm2 restart proxy-suez
pm2 logs proxy-suez --lines 100
```

### Adicionar um destino no suez

1. Incluir `{ "name": "<nome>", "proxyTarget": "https://<host>/" }` em `apiTargets`, no `/opt/suez/config/settings.json`.
2. Incluir `127.0.0.1 <nome>.localhost` no `/etc/hosts` e conferir com `ping <nome>.localhost`.
3. Liberar `<nome>.localhost` na ACL de rede do banco para o TF e o schema do APEX.
4. Rodar `pm2 restart proxy-suez`.
5. Testar no servidor com `curl -i http://<nome>.localhost:3000/<caminho>`.

### Trocar o certificado do Sicoob

1. Fazer backup do PFX e do `settings.json` atuais.
2. Copiar o PFX novo para `/opt/suez/config/cert/`.
3. Conferir se a senha abre o arquivo e anotar a validade:
   ```bash
   openssl pkcs12 -in novo.pfx -noout -info     # pede a senha
   openssl pkcs12 -in novo.pfx -nokeys -clcerts | openssl x509 -noout -subject -enddate
   ```
4. Atualizar `pfxPath` e `passphrase` em **todas** as ocorrências. No JSON, `"` e `\` na senha precisam de escape.
   ```bash
   grep -n -e pfxPath -e passphrase /opt/suez/config/settings.json
   ```
5. Rodar `pm2 restart proxy-suez`.
6. Buscar um token pelo banco (bloco abaixo). O esperado é `HTTP 200` com `access_token`, e só esse teste valida a senha.
7. Registrar a nova validade no changelog.

**Incidente de 2026-11-06.** O certificado do Jornal Repercussão foi trocado em 2026-11-05, e a senha nova foi colocada em só um dos dois lugares do settings. A busca do token passou a falhar com `ORA-20001 ... Erro HTTP ao buscar token Sicoob. Status: 500`, com `Error: mac verify failure` no corpo, e o erro apareceu para o cliente na tela de boletos. O problema foi resolvido trocando a senha nos dois lugares ([lição](licoes/2026-11-06-senha-do-pfx-em-todas-as-ocorrencias.md)).

### Simular a busca do token

Reproduz o `prc_busca_token` do `TF_PCK_BOLETO_SICOOB`, mas mostra o status, os headers e a resposta inteira. A package corta a resposta em 500 caracteres.

```sql
set serveroutput on size unlimited

declare
  c_id_empresa constant number := 16;  -- Jornal Repercussão
  c_id_prm     constant number := 3;   -- tf_parametro_integracao_banco.id

  v_url       varchar2(200);
  v_client_id varchar2(200);
  v_body      varchar2(4000);
  v_req       utl_http.req;
  v_resp      utl_http.resp;
  v_chunk     varchar2(8000);
  v_name      varchar2(256);
  v_value     varchar2(1024);
begin
  utl_http.set_detailed_excp_support(true);
  utl_http.set_transfer_timeout(30);

  v_url := tf_pck_parametro.fnc_parametro_caracter('URL_TOKEN_SICOOB', c_id_empresa);
  select x_api_key into v_client_id
  from tf_parametro_integracao_banco
  where id = c_id_prm;

  -- Mesmo corpo da package
  v_body := 'grant_type=client_credentials'
         || '&client_id=' || v_client_id
         || '&scope=boletos_inclusao boletos_consulta boletos_alteracao';

  dbms_output.put_line('URL ......: ' || v_url);
  dbms_output.put_line('client_id : ' || substr(v_client_id, 1, 8) || '... (' || length(v_client_id) || ' chars)');

  v_req := utl_http.begin_request(v_url, 'POST', 'HTTP/1.1');
  utl_http.set_header(v_req, 'Content-Type', 'application/x-www-form-urlencoded');
  utl_http.set_header(v_req, 'Content-Length', length(v_body));
  utl_http.write_text(v_req, v_body);

  v_resp := utl_http.get_response(v_req);
  dbms_output.put_line('HTTP .....: ' || v_resp.status_code || ' ' || v_resp.reason_phrase);

  for i in 1 .. utl_http.get_header_count(v_resp) loop
    utl_http.get_header(v_resp, i, v_name, v_value);
    dbms_output.put_line('  ' || v_name || ': ' || v_value);
  end loop;

  dbms_output.put_line('--- corpo completo ---');
  begin
    loop
      utl_http.read_text(v_resp, v_chunk, 8000);
      dbms_output.put_line(v_chunk);
    end loop;
  exception
    when utl_http.end_of_body then null;
  end;
  utl_http.end_response(v_resp);

exception
  when others then
    dbms_output.put_line('ERRO .....: ' || sqlerrm);
    dbms_output.put_line('DETALHE ..: ' || utl_http.get_detailed_sqlerrm);
    begin utl_http.end_response(v_resp); exception when others then null; end;
end;
/
```

### Diagnóstico

| Sintoma no banco | Causa provável |
|---|---|
| `Status: 500` com `mac verify failure` | O PFX não abre com a senha. Pode ser senha errada, uma ocorrência não trocada no settings ou arquivo corrompido |
| `Status: 502` com JSON `Bad Gateway` | O suez não conseguiu falar com o destino: DNS, rede ou TLS do lado de lá. O motivo vem no campo `message` |
| `Status: 400` ou `401` com JSON do Sicoob | A chamada chegou ao Sicoob. Conferir o `client_id` (`x_api_key`) e o cadastro do certificado no portal do desenvolvedor do Sicoob |
| HTML do site ou redirect no lugar do JSON | Nome fora do settings, ou PFX que não carregou na subida (ver o log do pm2) |
| `ORA-29273` com `ORA-12541` | suez parado |
| `ORA-29273` com `ORA-12545` | Nome ausente do `/etc/hosts` |
| `ORA-24247` | Falta ACL de rede no banco para o nome |

---

## 5. Riscos

- **Projetos abandonados:**
  - o suez teve o último commit em 2018-08-22, e o repositório foi arquivado em 2024-10-29;
  - o node4ords teve o último commit em 2016-09-13;
  - os dois dependem do `http-proxy-middleware` 0.17, muito defasado;
  - nenhum dos dois recebe correção de segurança.
- **Execução como root:** os dois apps rodam como root.
- **Segredos em texto puro:** a senha do PFX fica em texto puro no `settings.json`. Além disso, há cópias com PFX e senha no Google Drive, em `app/proxy/implantacao_PROD_24032026/` e nos `settings_DEV*.json`.
- **Stack trace exposto:** sem `NODE_ENV=production`, o Express devolve o stack trace com caminhos internos. O `TF_PCK_BOLETO_SICOOB` põe os primeiros 500 caracteres da resposta na mensagem de erro, e ela chega à tela do usuário do APEX, como aconteceu no incidente.
- **Validade do certificado:** o certificado A1 vence em um ano e hoje não há alerta de vencimento.
- **Um PFX por nome:** cada cliente Sicoob novo exige um nome novo no proxy (§3).

---

## 6. Migração para a OCI: nginx no lugar dos apps Node

**Decisão (2026-11-06, [ADR 0004](decisoes/0004-nginx-no-lugar-de-node4ords-e-suez.md)):** na VM de aplicação da OCI, o nginx assume os papéis do node4ords e do suez. Os dois apps Node não migram.

As imagens oficiais da Oracle (`database/free` e `database/ords`) não trazem nginx. O compose do projeto de referência, o [uc-local-apex-dev](https://www.united-codes.com/products/uc-local-apex-dev/docs/), sobe só o banco e o ORDS. O nginx aparece no [guia de HTTPS do projeto](https://www.united-codes.com/products/uc-local-apex-dev/docs/getting-started/expose-https-reverse-proxy/), instalado no host: ele termina o TLS com Let's Encrypt e repassa para o ORDS em `127.0.0.1:8181`. A instalação e a configuração do nginx ficam por nossa conta.

O que se ganha:
- **Manutenção:** pacote da distribuição, atualizado normalmente.
- **Configuração validada:** `nginx -t` confere a configuração antes de aplicar.
- **Reload sem queda:** `systemctl reload nginx` aplica mudanças sem derrubar conexões.
- **Erros no log:** vão para o `error.log`, não para quem chamou.
- **Senha num lugar só:** cada senha de certificado fica num único arquivo, o que evita a falha do incidente de 2026-11-06.

| Hoje | No nginx |
|---|---|
| node4ords: HTTP → HTTPS | `server` na 80 com `return 301 https://$host$request_uri;` |
| node4ords: TLS de entrada | `ssl_certificate` e `ssl_certificate_key`, renovados pelo certbot |
| node4ords: proxy do ORDS | `location /ords/` com `proxy_pass http://127.0.0.1:8181;`, `Host` e `X-Forwarded-Proto`. Validar na homologação se o ORDS 26 ainda exige a troca do `Origin` que o node4ords faz |
| node4ords: `Permissions-Policy` | `add_header Permissions-Policy "unload=(self)" always;` |
| node4ords: estáticos, site e redirects da raiz | `location` com `alias` e `return 302`. O `/i/` pode ficar com o nginx ou com o ORDS, conforme o compose |
| suez: destino pelo nome | Um `server` por nome (`server_name apisicredi.localhost;`) com `proxy_pass` para o destino |
| suez: mTLS com PFX | O nginx não lê PFX: converter para PEM e usar `proxy_ssl_certificate`, `proxy_ssl_certificate_key` e `proxy_ssl_password_file` |

O código PL/SQL não muda se o nginx mantiver os nomes `*.localhost` e a porta 3000. No compose do banco, `extra_hosts` aponta esses nomes para o IP privado da VM de aplicação ([migracao-oci-importacao-tf.md](migracao-oci-importacao-tf.md)). Como o destino é escolhido pelo nome, chamar o proxy direto pelo IP não funciona.

### Esboço: saída para o Sicoob com mTLS

```nginx
# O banco continua chamando http://apisicoobauth.localhost:3000/...
server {
    listen 10.0.1.10:3000;              # IP privado da VM de aplicação; o NSG libera só a VM banco
    server_name apisicoobauth.localhost;

    location / {
        proxy_pass https://auth.sicoob.com.br;
        proxy_ssl_server_name on;
        proxy_ssl_verify on;
        proxy_ssl_verify_depth 3;
        proxy_ssl_trusted_certificate /etc/pki/tls/certs/ca-bundle.crt;   # Oracle Linux

        proxy_ssl_certificate     /etc/nginx/mtls/repercussao.crt;
        proxy_ssl_certificate_key /etc/nginx/mtls/repercussao.key;
        proxy_ssl_password_file   /etc/nginx/mtls/repercussao.pass;
    }
}
```

Conversão do PFX:

```bash
openssl pkcs12 -in cliente.pfx -clcerts -nokeys  > repercussao.crt   # certificado do cliente primeiro
openssl pkcs12 -in cliente.pfx -cacerts -nokeys >> repercussao.crt   # depois a cadeia
openssl pkcs12 -in cliente.pfx -nocerts -out repercussao.key         # chave cifrada com nova senha, que vai no .pass
chmod 600 repercussao.key repercussao.pass
```

O processo mestre do nginx lê esses arquivos como root, então `600` com dono root basta. No OpenSSL 3, um PFX antigo pode exigir `-legacy`.

---

## 7. Pendências

- [ ] Registrar pasta, nome no pm2 e configuração do node4ords. O `config.js` não está na cópia local.
- [ ] Registrar a versão do Node no servidor (`node -v`).
- [ ] Atualizar a cópia local do settings da produção e a tabela de destinos (§3): quais destinos têm mTLS hoje.
- [ ] Confirmar se o `Permissions-Policy` (§2) já está na produção.
- [ ] Confirmar o uso de `viacep`, `soers`, `secwebhml` e `secwebprd`, e tirar os exemplos do settings.
- [ ] Registrar a validade do certificado do Jornal Repercussão e criar um alerta de vencimento.
- [ ] Tirar PFX e senhas da pasta `app/proxy` do Drive, ou restringir o acesso a ela.
- [ ] Migração: montar a configuração do nginx, com a entrada e um `server` por destino em uso, e testar na VM de desenvolvimento.
- [ ] Migração: validar login, POSTs e modais do APEX atrás do nginx.
- [ ] Migração: converter os PFX e buscar o token do Sicoob pelo nginx.

---

## Referências

Consultadas em 2026-11-06.

- [suez: commits](https://github.com/fuzziebrain/suez/commits/master/) (repositório arquivado) · [node4ords: commits](https://github.com/OraOpenSource/node4ords/commits/master/)
- [uc-local-apex-dev: compose da branch 26-4](https://github.com/United-Codes/uc-local-apex-dev/blob/26-4/docker-compose.yml) · [guia de HTTPS com nginx](https://www.united-codes.com/products/uc-local-apex-dev/docs/getting-started/expose-https-reverse-proxy/)
- [nginx: `proxy_ssl_certificate` e diretivas relacionadas](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_ssl_certificate)

---

## Changelog

- **2026-11-10 (2):** o incidente de 2026-11-06 virou [lição](licoes/2026-11-06-senha-do-pfx-em-todas-as-ocorrencias.md).
- **2026-11-10:** a direção do §6 virou o [ADR 0004](decisoes/0004-nginx-no-lugar-de-node4ords-e-suez.md).
- **2026-11-06:** documento criado a partir de `app/proxy/Proxy_reverso_dolomiti.md` e dos arquivos da mesma pasta. Registrados o incidente da troca de certificado do Jornal Repercussão, o procedimento de troca e a direção de substituir node4ords e suez pelo nginx na OCI.
