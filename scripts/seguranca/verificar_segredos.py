#!/usr/bin/env python3
"""Impede que segredos entrem no repositório.

Modos:
  --hook    Hook PreToolUse do Claude Code (Write|Edit|MultiEdit). Lê o JSON da ferramenta
            no stdin e nega a gravação se o conteúdo novo tiver segredo em arquivo versionado.
  --staged  Pre-commit do git. Varre as linhas adicionadas no stage.
  --teste   Roda os casos de exemplo do fim deste arquivo.

Nunca imprime o valor encontrado: só o tipo e a linha.

Adaptado de scripts/seguranca/verificar_segredos.py da KB da ExpertBase, com os padrões
do Oracle (IDENTIFIED BY, usuario/senha@banco, JDBC), do PFX do suez e do ORACLE_PWD.
"""
import json
import os
import re
import subprocess
import sys

PADROES = [
    ("chave privada", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("token do GitHub", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,})")),
    ("chave de acesso AWS", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("chave de API (sk-)", re.compile(r"\bsk-[A-Za-z0-9_-]{32,}")),
]

# URL com credencial embutida: esquema://usuario:senha@host
URL_COM_SENHA = re.compile(r"\b[a-z][a-z0-9+.-]*://[^\s:/@]+:([^\s@/]+)@")

# Atribuição de variável sensível com valor literal (YAML, JSON, .env, compose, settings do suez).
# A aspa opcional depois do nome pega a chave JSON ("passphrase": "...").
ATRIBUICAO = re.compile(
    r"\b([A-Za-z0-9_]*(?:PASSWORD|PASSWD|PASSPHRASE|PWD|SENHA|SECRET|TOKEN|API_?KEY|ACCESS_KEY|"
    r"PRIVATE_KEY|CLIENT_SECRET)[A-Za-z0-9_]*)"
    r"[\"']?[ \t]*[:=][ \t]*[\"']?([^\s\"'#,}]+)",
    re.IGNORECASE,
)

# Padrões do Oracle. O contexto já diz que é senha, então o mínimo de tamanho é menor.
ORACLE = [
    # CREATE/ALTER USER ... IDENTIFIED BY senha  (e IDENTIFIED BY VALUES 'hash')
    ("senha em IDENTIFIED BY",
     re.compile(r"\bIDENTIFIED\s+BY\s+(?:VALUES\s+)?[\"']?([^\s\"';]+)", re.IGNORECASE)),
    # sqlplus/expdp/impdp/rman/connect usuario/senha[@banco]
    ("senha em linha de conexão",
     re.compile(r"\b(?:sqlplus|conn|connect|expdp|impdp|rman|sqlldr)\s+(?:-\S+\s+)*"
                r"[\"']?[A-Za-z][A-Za-z0-9_$#]*/([^\s@/\"']+)", re.IGNORECASE)),
    # sql (SQLcl), exp e imp só com @ depois da senha: sem ele, "SQL Developer/SQLcl" vira senha
    ("senha em linha de conexão",
     re.compile(r"\b(?:sql|exp|imp)\s+(?:-\S+\s+)*"
                r"[\"']?[A-Za-z][A-Za-z0-9_$#]*/([^\s@/\"']+)@", re.IGNORECASE)),
    # jdbc:oracle:thin:usuario/senha@...
    ("senha em URL JDBC",
     re.compile(r"jdbc:oracle:[a-z]+:[A-Za-z][A-Za-z0-9_$#]*/([^\s@]+)@", re.IGNORECASE)),
    # openssl ... -passin pass:senha / -passout pass:senha (PFX do Sicoob)
    ("senha em pass: do openssl", re.compile(r"\bpass:([^\s\"']+)")),
    # mkstore -createCredential <alias> <usuario> <senha>
    ("senha em mkstore",
     re.compile(r"-createCredential\s+\S+\s+\S+\s+([^\s\"']+)", re.IGNORECASE)),
]

PLACEHOLDER = re.compile(
    r"^(?:\$\{?[A-Za-z0-9_]+\}?|\{\{.*\}\}|<[^>]+>|&{1,2}[A-Za-z0-9_]+\.?|:[A-Za-z0-9_]+|"
    r"/run/secrets/\S*|x{3,}|\*{3,}|\.{3,}|…|"
    r"changeme|change_me|troque\S*|trocar\S*|exemplo\S*|example\S*|placeholder|"
    r"sua_\S*|seu_\S*|your_\S*|"
    r"senha|password|null|none|true|false|required|optional|obrigatorio|opcional|"
    r"externally|globally)$",
    re.IGNORECASE,
)

MIN_VALOR = 8
MIN_VALOR_ORACLE = 4

# Este arquivo traz senhas inventadas nos casos de teste (CASOS, no fim).
ISENTOS = {"scripts/seguranca/verificar_segredos.py"}

# Expressão de código, não valor literal: chamada, índice ou acesso por ponto
# (ex.: re.compile(...), os.environ["X"], config.api_key, :new.senha)
EXPRESSAO_DE_CODIGO = re.compile(r"[()\[\]]|^:?[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+$")


def valor_parece_segredo(valor: str, minimo: int = MIN_VALOR) -> bool:
    valor = valor.strip().rstrip(";")
    if len(valor) < minimo:
        return False
    if valor.startswith(("$", "{", "<", "&", "/run/secrets/")):
        return False
    if EXPRESSAO_DE_CODIGO.search(valor):
        return False
    return not PLACEHOLDER.match(valor)


def varrer_linha(linha: str):
    achados = []
    for nome, padrao in PADROES:
        if padrao.search(linha):
            achados.append(nome)
    m = URL_COM_SENHA.search(linha)
    if m and valor_parece_segredo(m.group(1)):
        achados.append("URL com senha embutida")
    for m in ATRIBUICAO.finditer(linha):
        if valor_parece_segredo(m.group(2)):
            achados.append(f"valor literal em {m.group(1)}")
    for nome, padrao in ORACLE:
        for m in padrao.finditer(linha):
            if valor_parece_segredo(m.group(1), MIN_VALOR_ORACLE):
                achados.append(nome)
                break
    return achados


def varrer_texto(texto: str, deslocamento: int = 1):
    resultado = []
    for i, linha in enumerate(texto.splitlines(), start=deslocamento):
        for achado in varrer_linha(linha):
            resultado.append((i, achado))
    return resultado


def arquivo_ignorado(caminho: str, raiz: str) -> bool:
    r = subprocess.run(["git", "-C", raiz, "check-ignore", "-q", caminho],
                       capture_output=True)
    return r.returncode == 0


def texto_da_ferramenta(entrada: dict) -> str:
    partes = [entrada.get("content") or "", entrada.get("new_string") or ""]
    for edicao in entrada.get("edits") or []:  # MultiEdit
        partes.append(edicao.get("new_string") or "")
    return "\n".join(p for p in partes if p)


def modo_hook() -> int:
    try:
        dados = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    entrada = dados.get("tool_input") or {}
    caminho = entrada.get("file_path") or ""
    texto = texto_da_ferramenta(entrada)
    raiz = os.environ.get("CLAUDE_PROJECT_DIR") or dados.get("cwd") or os.getcwd()
    if not caminho or not texto:
        return 0
    caminho_abs = os.path.abspath(caminho)
    if not caminho_abs.startswith(os.path.abspath(raiz) + os.sep):
        return 0  # fora do repositório: não é assunto deste hook
    if arquivo_ignorado(caminho_abs, raiz):
        return 0  # .env e afins podem guardar segredo localmente
    rel = os.path.relpath(caminho_abs, raiz)
    if rel in ISENTOS:
        return 0
    achados = varrer_texto(texto)
    if not achados:
        return 0
    lista = "; ".join(f"linha {n}: {tipo}" for n, tipo in achados[:10])
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                f"Segredo aparente em arquivo versionado ({rel}) — {lista}. "
                "Troque o valor por um placeholder (${VARIAVEL}, <senha>, &senha no SQL*Plus) "
                "e deixe o valor real fora do repositório: .env ignorado, cofre ou a pasta "
                "DolomiTI/ do Drive. Se for falso positivo, use um placeholder evidente e "
                "avise o usuário."
            ),
        }
    }, ensure_ascii=False))
    return 0


def modo_staged() -> int:
    diff = subprocess.run(["git", "diff", "--cached", "-U0", "--no-color"],
                          capture_output=True, text=True).stdout
    arquivo, linha_atual, achados = None, 0, []
    for linha in diff.splitlines():
        if linha.startswith("+++ "):
            arquivo = linha[6:] if linha.startswith("+++ b/") else None
            if arquivo in ISENTOS:
                arquivo = None
        elif linha.startswith("@@"):
            m = re.search(r"\+(\d+)", linha)
            linha_atual = int(m.group(1)) if m else 0
        elif linha.startswith("+") and arquivo:
            for tipo in varrer_linha(linha[1:]):
                achados.append((arquivo, linha_atual, tipo))
            linha_atual += 1
    if not achados:
        return 0
    print("\n✋ Commit bloqueado: segredo aparente nas linhas adicionadas.\n", file=sys.stderr)
    for arq, n, tipo in achados[:20]:
        print(f"   {arq}:{n}  {tipo}", file=sys.stderr)
    print("\nTroque o valor por um placeholder e deixe o valor real fora do repositório.",
          file=sys.stderr)
    return 1


# (linha, deve_acusar). Os valores são inventados.
CASOS = [
    ('create user tf identified by "&senha_tf"', False),
    ("create user apexrep identified by \"&senha_apexrep\";", False),
    ("alter user tf identified by Abc12345;", True),
    ("alter user tf identified by values 'S:1A2B3C4D5E6F';", True),
    ("create user x identified externally;", False),
    ("sqlplus tf/oracle1@//10.0.2.10:1521/FREEPDB1", True),
    ("sqlplus / as sysdba", False),
    ("sqlplus sys/<senha>@//host:1521/FREEPDB1 as sysdba", False),
    ("expdp tf@XE schemas=TF directory=DATA_PUMP_DIR", False),
    ("expdp system/Manager123@XE schemas=TF", True),
    ("jdbc:oracle:thin:@//10.0.2.10:1521/FREEPDB1", False),
    ("jdbc:oracle:thin:jri/S3nhaJri@//10.0.2.10:1521/FREEPDB1", True),
    ("ORACLE_PWD=MinhaSenha2026", True),
    ("ORACLE_PWD=${ORACLE_PWD}", False),
    ('    "passphrase": "pfx-Sicoob-2026",', True),
    ('    "passphrase": "<senha do PFX>",', False),
    ('    "pfxPath": "/opt/suez/certs/cliente.pfx",', False),
    ("openssl pkcs12 -in c.pfx -passin pass:Segredo99 -nokeys", True),
    ("openssl pkcs12 -in c.pfx -passin pass:$SENHA_PFX -nokeys", False),
    ("--   :new.senha := null;", False),
    ("-- update tf.ltf_usuario set senha = null where senha is not null;", False),
    ("4. Atualizar `pfxPath` e `passphrase` em **todas** as ocorrências.", False),
    ("grep -n -e pfxPath -e passphrase /opt/suez/config/settings.json", False),
    ("mkstore -wrl /w -createCredential FREEPDB1 jri Jri2026x", True),
    ("password=SUA_SENHA", False),
    ("o acesso admin por SQL Developer/SQLcl e o Data Pump", False),
    ("sql tf/Senha123@//10.0.2.10:1521/FREEPDB1", True),
    ("sql tf@//10.0.2.10:1521/FREEPDB1", False),
]


def modo_teste() -> int:
    falhas = 0
    for linha, esperado in CASOS:
        obtido = bool(varrer_linha(linha))
        if obtido != esperado:
            falhas += 1
            print(f"FALHOU (esperado {'acusar' if esperado else 'passar'}): {linha}")
    print(f"{len(CASOS) - falhas}/{len(CASOS)} casos ok")
    return 1 if falhas else 0


if __name__ == "__main__":
    if "--hook" in sys.argv:
        sys.exit(modo_hook())
    if "--staged" in sys.argv:
        sys.exit(modo_staged())
    if "--teste" in sys.argv:
        sys.exit(modo_teste())
    print("uso: verificar_segredos.py --hook | --staged | --teste", file=sys.stderr)
    sys.exit(2)
