#!/usr/bin/env python3
"""Hook Stop da KB: cobra commit e push antes de encerrar, num único JSON de bloqueio.

1. Arquivo alterado nesta sessão e sem commit, ou commit local sem push: pede o commit
   e o push. Se o usuário ainda vai revisar a mudança, o agente só lembra, sem commitar.
   "Desta sessão" = o caminho aparece num Edit/Write da transcrição, ou num comando de
   shell que grava nele. Outra sessão (do Tiago ou do Chico) pode estar na mesma pasta.
2. Arquivo sem commit há mais de 30 min que não é desta sessão: só avisa o usuário,
   sem bloquear.

Adaptado de .claude/hooks/exige-registro.py da KB da ExpertBase, sem a cobrança de
registro em docs/ quando stacks/ ou fluxos/ mudam: a KB da Dolomiti só tem documentos.
"""
import json
import os
import subprocess
import sys
import time

PARADO_SEGUNDOS = 30 * 60
GRAVA = (" > ", " >> ", "write_text", "sed -i", "tee ", "mv ", "cp ", "rm ", "git add ", "git checkout ")


def git(raiz, *args):
    r = subprocess.run(["git", "-C", raiz, *args], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


def caminhos_pendentes(raiz):
    caminhos = []
    for linha in git(raiz, "status", "--porcelain", "--untracked-files=all").splitlines():
        caminho = linha[3:]
        if " -> " in caminho:
            caminho = caminho.split(" -> ", 1)[1]
        caminhos.append(caminho.strip('"'))
    return caminhos


def entradas_da_sessao(transcricao):
    """Textos de Edit/Write (file_path) e comandos de shell que gravam, desta sessão."""
    textos = []
    if not transcricao or not os.path.isfile(transcricao):
        return textos
    with open(transcricao, encoding="utf-8", errors="replace") as f:
        for linha in f:
            if '"tool_use"' not in linha:
                continue
            try:
                conteudo = json.loads(linha).get("message", {}).get("content", [])
            except (ValueError, AttributeError):
                continue
            for item in conteudo if isinstance(conteudo, list) else []:
                if not isinstance(item, dict) or item.get("type") != "tool_use":
                    continue
                entrada = item.get("input") or {}
                if item.get("name") in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
                    textos.append(str(entrada.get("file_path", "")))
                elif item.get("name") == "Bash":
                    comando = str(entrada.get("command", ""))
                    if any(g in comando for g in GRAVA):
                        textos.append(comando)
    return textos


def da_sessao(caminho, raiz_abs, textos):
    absoluto = os.path.join(raiz_abs, caminho)
    for t in textos:
        if absoluto in t or t.startswith(caminho):
            return True
        if any(b + caminho in t for b in (" ", '"', "'", "(", "=", "\n")):
            return True
    return False


def parado(caminho, raiz_abs):
    absoluto = os.path.join(raiz_abs, caminho)
    if not os.path.exists(absoluto):
        return True
    return time.time() - os.path.getmtime(absoluto) > PARADO_SEGUNDOS


def lista(caminhos, limite=8):
    texto = ", ".join(caminhos[:limite])
    return texto + (f" e mais {len(caminhos) - limite}" if len(caminhos) > limite else "")


def main():
    try:
        entrada = json.load(sys.stdin)
    except ValueError:
        entrada = {}
    # Evita laço: se o agente já está continuando por causa deste hook, deixa encerrar.
    if entrada.get("stop_hook_active"):
        return

    raiz = os.environ.get("CLAUDE_PROJECT_DIR", ".")
    if git(raiz, "rev-parse", "--is-inside-work-tree").strip() != "true":
        return
    raiz_abs = git(raiz, "rev-parse", "--show-toplevel").strip()

    caminhos = caminhos_pendentes(raiz)
    textos = entradas_da_sessao(entrada.get("transcript_path", ""))
    meus = [c for c in caminhos if da_sessao(c, raiz_abs, textos)]
    parados = [c for c in caminhos if c not in meus and parado(c, raiz_abs)]
    motivos = []

    if meus:
        motivos.append(
            f"Arquivos alterados nesta sessão e não commitados: {lista(meus)}. "
            "Se o usuário ainda vai revisar a mudança (por exemplo, algo no CLAUDE.md), não commite: "
            "termine a resposta lembrando quais arquivos estão sem commit. Senão, antes de encerrar: "
            "git pull --rebase; git add só esses arquivos; git diff --cached --stat; commit com o prefixo "
            "(docs: para conteúdo, kb: para a estrutura da KB); git push logo depois (Convenções do "
            "CLAUDE.md). Se algum não for desta sessão, deixe-o de fora e diga ao usuário qual é."
        )

    if git(raiz, "rev-parse", "--abbrev-ref", "@{u}").strip():
        nao_enviados = git(raiz, "log", "--oneline", "@{u}..HEAD").splitlines()
        if nao_enviados:
            motivos.append(
                f"Há {len(nao_enviados)} commit(s) local(is) não enviado(s): git pull --rebase e git push logo."
            )

    if motivos:
        if parados:
            motivos.append(
                f"Além disso, há arquivos sem commit há mais de 30 min que não são desta sessão: {lista(parados)}. "
                "Avise o usuário e pergunte se commita."
            )
        print(json.dumps({"decision": "block", "reason": " ".join(motivos)}, ensure_ascii=False))
    elif parados:
        print(json.dumps({
            "systemMessage": f"KB: {len(parados)} arquivo(s) sem commit há mais de 30 min, de outra sessão: "
                             f"{lista(parados)}. Commitar na sessão que os criou, ou pedir aqui."
        }, ensure_ascii=False))


if __name__ == "__main__":
    main()
