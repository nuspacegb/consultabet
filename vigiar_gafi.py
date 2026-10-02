#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vigia as listas do GAFI -- sem tentar extrair nada.

Por que vigiar em vez de raspar
-------------------------------
A lista do GAFI tem 25 paises e muda tres vezes por ano. Um raspador para
isso seria codigo fragil defendendo um ganho pequeno: ele quebraria em
silencio entre uma plenaria e outra, justamente quando ninguem esta
olhando, e voce so descobriria no dia em que precisasse.

Este robo faz menos e erra menos. Ele responde uma pergunta so:

    "a pagina do COAF mudou desde a ultima vez?"

Se mudou, ele te avisa. Quem decide o que mudou e atualiza o gafi.json e
voce -- em cinco minutos, tres vezes por ano.

Dois gatilhos independentes
---------------------------
1. A pagina do COAF mudou (comparacao de impressao digital)
2. A base esta velha para o calendario: ja passou da plenaria e o
   gafi.json continua apontando para a anterior

O segundo existe porque o primeiro pode falhar -- o COAF pode publicar
num endereco novo, ou a pagina pode mudar de forma que a impressao
digital nao pegue. O calendario do GAFI, esse nao falha: fevereiro,
junho e outubro, todo ano.

Saidas:
    0  nada a fazer, ou erro de rede (nao e alarme)
    0  mudou -- escreve 'mudou=sim' no GITHUB_OUTPUT
    1  erro de verdade (arquivo corrompido, etc.)
"""

import hashlib
import json
import os
import re
import socket
import sys
from datetime import date, datetime

import requests
import urllib3.util.connection

# Runners do GitHub sao so IPv4; varios sites do governo publicam IPv6.
urllib3.util.connection.allowed_gai_family = lambda: socket.AF_INET

PAGINA = ("https://www.gov.br/coaf/pt-br/assuntos/"
          "informacoes-as-pessoas-obrigadas/avisos-e-alertas/"
          "comunicados-do-gafi")

ARQUIVO_VIGIA = "gafi_vigia.json"
ARQUIVO_BASE  = "gafi.json"

CABECALHOS = {
    "User-Agent": ("Mozilla/5.0 (compatible; NuConsulta/1.0; "
                   "+https://nuspacegb.github.io/consultabet/)"),
    "Accept-Language": "pt-BR,pt;q=0.9",
}

# Meses em que o GAFI faz plenaria.
MESES_PLENARIA = (2, 6, 10)


def anotar(chave, valor):
    """Escreve no GITHUB_OUTPUT, quando rodando dentro do Actions."""
    destino = os.getenv("GITHUB_OUTPUT")
    if destino:
        with open(destino, "a", encoding="utf-8") as f:
            f.write(f"{chave}={valor}\n")


def impressao_digital(html):
    """
    Reduz a pagina ao que interessa e devolve um hash.

    Tira script, style, comentario e atributo -- que mudam a cada visita
    por causa de token de sessao e afins, e disparariam alarme falso todo
    dia. Sobra o texto visivel, com espacos normalizados.
    """
    texto = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
    texto = re.sub(r"(?s)<!--.*?-->", " ", texto)
    texto = re.sub(r"(?s)<[^>]+>", " ", texto)
    texto = re.sub(r"&[a-zA-Z#0-9]+;", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip().lower()

    # Datas soltas no rodape ("atualizado em 02/10/2026") mudam sem que o
    # conteudo mude. Fora.
    texto = re.sub(r"\d{2}/\d{2}/\d{4}", "", texto)

    return hashlib.sha256(texto.encode("utf-8")).hexdigest(), len(texto)


def plenaria_esperada(hoje):
    """A plenaria mais recente que ja deveria estar refletida na base."""
    ano, mes = hoje.year, hoje.month
    for m in sorted(MESES_PLENARIA, reverse=True):
        # Damos um mes de folga: o COAF publica depois da plenaria.
        if mes >= m + 1:
            return (ano, m)
    return (ano - 1, MESES_PLENARIA[-1])


def base_esta_velha():
    """
    Compara a plenaria registrada no gafi.json com a que o calendario diz
    que ja deveria estar la.
    """
    try:
        with open(ARQUIVO_BASE, encoding="utf-8") as f:
            meta = json.load(f).get("meta", {})
        iso = meta.get("plenaria_iso")
        if not iso:
            return False, "o gafi.json nao registra de qual plenaria ele e"
        d = datetime.strptime(iso, "%Y-%m-%d").date()
    except Exception as erro:
        return False, f"nao consegui ler o {ARQUIVO_BASE}: {erro}"

    ano_esp, mes_esp = plenaria_esperada(date.today())
    if (d.year, d.month) < (ano_esp, mes_esp):
        nomes = {2: "fevereiro", 6: "junho", 10: "outubro"}
        return True, (f"a base e da plenaria de {d.strftime('%m/%Y')}, mas a de "
                      f"{nomes[mes_esp]} de {ano_esp} ja deveria estar publicada")
    return False, ""


def main():
    # ---------------------------------------------------- gatilho 2: calendario
    velha, motivo_calendario = base_esta_velha()

    # ---------------------------------------------------- gatilho 1: a pagina
    mudou_pagina = False
    motivo_pagina = ""

    try:
        resp = requests.get(PAGINA, headers=CABECALHOS, timeout=45)
        resp.raise_for_status()
        atual, tamanho = impressao_digital(resp.text)

        if tamanho < 500:
            print(f"A pagina voltou curta demais ({tamanho} caracteres). "
                  "Provavelmente e um bloqueio ou erro, nao conteudo. "
                  "Nao vou comparar.")
        else:
            anterior = {}
            if os.path.exists(ARQUIVO_VIGIA):
                with open(ARQUIVO_VIGIA, encoding="utf-8") as f:
                    anterior = json.load(f)

            if not anterior.get("impressao"):
                print("Primeira execucao: guardando a impressao digital.")
            elif anterior["impressao"] != atual:
                mudou_pagina = True
                motivo_pagina = (f"a pagina do COAF mudou desde "
                                 f"{anterior.get('conferido_em', '?')}")
                print(f"MUDOU. {motivo_pagina}")
            else:
                print("A pagina do COAF esta igual.")

            with open(ARQUIVO_VIGIA, "w", encoding="utf-8") as f:
                json.dump({
                    "pagina": PAGINA,
                    "impressao": atual,
                    "tamanho": tamanho,
                    "conferido_em": date.today().isoformat(),
                }, f, ensure_ascii=False, indent=1)

    except requests.exceptions.RequestException as erro:
        # Mesma regra dos outros robos: rede fora nao e alarme. O gatilho
        # do calendario continua valendo abaixo.
        print(f"Nao consegui acessar o COAF ({type(erro).__name__}). "
              "Isso e transitorio; nao vou tratar como falha.")

    # ----------------------------------------------------------- o veredito
    motivos = [m for m in (motivo_pagina, motivo_calendario if velha else "") if m]

    if motivos:
        anotar("mudou", "sim")
        anotar("motivo", " e ".join(motivos))
        print()
        print("=" * 60)
        print("VALE CONFERIR AS LISTAS DO GAFI")
        for m in motivos:
            print(f"  - {m}")
        print()
        print(f"  Pagina: {PAGINA}")
        print("  Se mudou de verdade: edite as listas no topo do")
        print("  gerar_gafi.py, rode 'python3 gerar_gafi.py' e suba o")
        print("  gafi.json novo.")
        print("=" * 60)
    else:
        anotar("mudou", "nao")
        print("Nada a fazer.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
