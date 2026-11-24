# Compose do banco e da aplicação

Os mesmos arquivos servem ao dev e à produção ([ADR 0003](../decisoes/0003-dev-em-a1-com-o-compose-da-producao.md)). Só o `.env` muda.

| Pasta | Onde roda na produção | O que sobe |
|---|---|---|
| [banco/](banco/) | VM banco, sem IP público | Oracle AI Database Free 26ai, com dados em `/opt/oracle/oradata` |
| [aplicacao/](aplicacao/) | VM de aplicação | ORDS com as imagens do APEX, só em `127.0.0.1:8181` |

No dev, as duas pastas sobem na mesma VM, e todos os IPs do `.env` são o IP privado dela. O nginx ([ADR 0004](../decisoes/0004-nginx-no-lugar-de-node4ords-e-suez.md)) e o Tomcat do JRI rodam no host, fora do compose.

**Por que um compose próprio, e não o do uc-local-apex-dev:** as imagens são as mesmas, mas o compose e os scripts de lá foram feitos para o notebook do desenvolvedor: portas em todas as interfaces, senhas em texto relaxadas, archive log desligado e `restart: no`. As diferenças estão na [análise, §7](../analise-producao-oci-vm-docker.md#7-o-que-precisa-mudar-em-relação-à-imagem-dos-links). Do projeto, aproveitamos os tetos de datafile e a limpeza da auditoria, no `pos-instalacao.sql`.

## Primeira subida

A ordem resumida. O passo a passo com conferência vai para o runbook de subida da VM.

1. Na VM: criar `/opt/oracle/oradata` com dono `54321:54321`, o usuário `oracle` das imagens, e `/opt/dolomiti/ords/config` e `/opt/dolomiti/apex/images`.
2. Em cada pasta, copiar `.env.example` para `.env`, preencher e rodar `chmod 600 .env`.
3. Subir o banco (`docker compose up -d` em `banco/`) e esperar o *healthy*. A primeira criação leva alguns minutos.
4. Rodar o [`pos-instalacao.sql`](banco/pos-instalacao.sql) e conferir as saídas: `ARCHIVELOG`, hora de Brasília, `AL32UTF8` e tetos.
5. Instalar o APEX dentro do contêiner do banco, com `apexins.sql TBS_APEX TBS_APEX TEMP /i/`, e copiar a pasta `images/` do zip para `/opt/dolomiti/apex/images`.
6. Subir a aplicação (`docker compose up -d` em `aplicacao/`). Na primeira vez, a imagem instala o ORDS no banco.
7. Configurar o ORDS e reiniciar o contêiner:
   ```bash
   docker exec dolomiti-ords ords --config /etc/ords/config config --db-pool default set plsql.gateway.mode proxied
   docker exec dolomiti-ords ords --config /etc/ords/config config set database.api.enabled false
   docker exec dolomiti-ords ords --config /etc/ords/config config --db-pool default set feature.sdw false
   docker restart dolomiti-ords
   ```
8. Tirar o `ORACLE_PWD` do `.env` da aplicação. Ele só volta para atualizar o ORDS.

## Pendências

- **Imagens `arm64`:** não confirmadas. O primeiro `docker pull` na VM A1 responde.
- **`ENABLE_ARCHIVELOG`:** conferir na documentação da imagem `database/free`. Se não funcionar, ligar o archive log por SQL, com o banco montado.
- **Versão do APEX:** baixar o zip uma vez, anotar a versão e guardar uma cópia no Object Storage, para reinstalar sempre a mesma.
- **Retenção da auditoria:** 7 dias serve ao dev; definir a da produção.
- **Fora deste compose, por ora:** backup (RMAN, Data Pump, Object Storage), configuração do nginx e o JRI.

## Changelog

- **2026-11-24:** criado. Imagens `database/free:23.26.3.0` e `database/ords:26.3.1`, as mesmas do uc-local-apex-dev (branch `26-4`, commit `22d7c7c`, de 2026-11-22).
