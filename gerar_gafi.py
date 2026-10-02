#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera o gafi.json: TODOS os paises com codigo ISO, marcando quais estao
nas listas do GAFI.

Por que todos os paises, e nao so os 25 listados?
-------------------------------------------------
O analista chega com um codigo de tres letras vindo do alerta ("BOL").
Se o site respondesse "nao encontrado", isso significaria duas coisas
opostas:

    "a Bolivia nao esta listada pelo GAFI"   (resposta util)
    "eu nao sei o que e BOL"                 (falha da ferramenta)

Com a lista completa, o site sabe a diferenca. E o mesmo principio das
outras duas bases: nunca deixar a ferramenta responder "nao achei"
quando o certo e "nao consta".

Atualizar 3x por ano, depois das plenarias do GAFI (fev, jun, out):
basta mexer nas duas listas abaixo e rodar de novo.

    python3 gerar_gafi.py
"""

import json
import sys
from datetime import date

# =============================================================================
#  AS LISTAS DO GAFI  --  editar aqui depois de cada plenaria
# =============================================================================

PLENARIA = "19/06/2026"          # data do comunicado que esta refletido aqui
PLENARIA_ISO = "2026-06-19"

FONTE_ACAO = ("https://www.gov.br/coaf/pt-br/assuntos/"
              "informacoes-as-pessoas-obrigadas/avisos-e-alertas/"
              "comunicados-do-gafi")
FONTE_MONIT = FONTE_ACAO

# Chamado para acao. O GAFI separa dois graus dentro desta lista:
#   contramedidas        -- o grau mais severo
#   diligencia reforcada -- severo, mas sem pedido de contramedidas
ACAO_CONTRAMEDIDAS = ["IRN", "PRK"]
ACAO_DILIGENCIA    = ["MMR"]

# Monitoramento reforcado (a "lista cinza")
MONITORAMENTO = [
    "AGO",  # Angola
    "BIH",  # Bosnia e Herzegovina
    "BOL",  # Bolivia
    "BGR",  # Bulgaria
    "CMR",  # Camaroes
    "CIV",  # Costa do Marfim
    "COD",  # Congo (Republica Democratica)
    "HTI",  # Haiti
    "IRQ",  # Iraque
    "KEN",  # Quenia
    "KWT",  # Kuwait
    "LAO",  # Laos
    "LBN",  # Libano
    "MCO",  # Monaco
    "NPL",  # Nepal
    "PNG",  # Papua-Nova Guine
    "SSD",  # Sudao do Sul
    "SYR",  # Siria
    "VEN",  # Venezuela
    "VNM",  # Vietna
    "VGB",  # Ilhas Virgens Britanicas
    "YEM",  # Iemen
]

# O CLDR escreve alguns nomes de um jeito que soa estranho num relatorio
# de analise ("Congo - Kinshasa"). Aqui a gente corrige esses poucos.
NOMES_PERSONALIZADOS = {
    "COD": "República Democrática do Congo",
    "COG": "República do Congo",
    "MMR": "Mianmar",
}

# Apelidos que o analista pode digitar e que nao sao o nome oficial.
# A busca ja ignora acento e caixa; isto aqui e para nome alternativo mesmo.
APELIDOS = {
    "PRK": ["coreia do norte", "correia do norte", "dprk", "north korea"],
    "KOR": ["coreia do sul", "south korea"],
    "IRN": ["ira", "iran"],
    "MMR": ["myanmar", "birmania", "burma"],
    "COD": ["congo democratico", "rd congo", "rdc", "zaire"],
    "COG": ["congo brazzaville", "republica do congo"],
    "CIV": ["costa do marfim", "ivory coast"],
    "VGB": ["ilhas virgens britanicas", "virgin islands"],
    "VIR": ["ilhas virgens americanas"],
    "LAO": ["laos"],
    "SYR": ["siria"],
    "YEM": ["iemen"],
    "KEN": ["quenia"],
    "CMR": ["camaroes"],
    "BIH": ["bosnia", "bosnia e herzegovina"],
    "NLD": ["holanda", "paises baixos"],
    "USA": ["estados unidos", "eua"],
    "GBR": ["reino unido", "inglaterra"],
    "CHE": ["suica"],
    "ARE": ["emirados arabes unidos"],
    "TUR": ["turquia"],
    "CZE": ["republica tcheca", "tchequia"],
    "CPV": ["cabo verde"],
    "TLS": ["timor leste"],
    "SWZ": ["suazilandia", "essuatini"],
    "MKD": ["macedonia"],
}

# =============================================================================


def nomes_em_portugues():
    """Nomes de pais em portugues, vindos do Babel (dados do CLDR)."""
    try:
        from babel import Locale
        return Locale("pt", "BR").territories
    except Exception as erro:
        print(f"Babel indisponivel ({erro}). Os nomes sairao so em ingles.",
              file=sys.stderr)
        return {}


def carregar_iso():
    """A base oficial ISO 3166-1 que acompanha o sistema."""
    caminho = "/usr/share/iso-codes/json/iso_3166-1.json"
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)["3166-1"]


def classificar(alpha3):
    if alpha3 in ACAO_CONTRAMEDIDAS:
        return "acao_contramedidas"
    if alpha3 in ACAO_DILIGENCIA:
        return "acao_diligencia"
    if alpha3 in MONITORAMENTO:
        return "monitoramento"
    return "nao_listado"


def main():
    pt = nomes_em_portugues()
    paises = []

    for item in carregar_iso():
        a2 = item.get("alpha_2", "")
        a3 = item.get("alpha_3", "")
        if not a3:
            continue

        nome_pt = (NOMES_PERSONALIZADOS.get(a3)
                   or pt.get(a2)
                   or item.get("common_name")
                   or item["name"])

        paises.append({
            "alpha3":    a3,
            "alpha2":    a2,
            "numerico":  item.get("numeric", ""),
            "nome":      nome_pt,
            "nome_en":   item["name"],
            "apelidos":  APELIDOS.get(a3, []),
            "situacao":  classificar(a3),
        })

    paises.sort(key=lambda p: p["nome"])

    # ---- conferencias que impedem um arquivo silenciosamente errado -------
    codigos = {p["alpha3"] for p in paises}
    esperados = ACAO_CONTRAMEDIDAS + ACAO_DILIGENCIA + MONITORAMENTO
    faltando = [c for c in esperados if c not in codigos]
    if faltando:
        print(f"ERRO: codigos do GAFI que nao existem na base ISO: {faltando}",
              file=sys.stderr)
        return 1

    contagem = {
        "acao_contramedidas": len(ACAO_CONTRAMEDIDAS),
        "acao_diligencia":    len(ACAO_DILIGENCIA),
        "monitoramento":      len(MONITORAMENTO),
    }
    for chave, esperado in contagem.items():
        real = sum(1 for p in paises if p["situacao"] == chave)
        if real != esperado:
            print(f"ERRO: {chave} deveria ter {esperado}, tem {real}",
                  file=sys.stderr)
            return 1

    saida = {
        "meta": {
            "fonte_nome":   "COAF / GAFI",
            "fonte_url":    FONTE_ACAO,
            "plenaria":     PLENARIA,
            "plenaria_iso": PLENARIA_ISO,
            "gerado_em":    date.today().isoformat(),
            "total_paises": len(paises),
            "total_acao":   len(ACAO_CONTRAMEDIDAS) + len(ACAO_DILIGENCIA),
            "total_monitoramento": len(MONITORAMENTO),
        },
        "paises": paises,
    }

    with open("gafi.json", "w", encoding="utf-8") as f:
        json.dump(saida, f, ensure_ascii=False, indent=1)

    print(f"gafi.json gerado: {len(paises)} paises")
    print(f"  chamado para acao .... {saida['meta']['total_acao']}")
    print(f"  monitoramento ........ {saida['meta']['total_monitoramento']}")
    print(f"  nao listados ......... "
          f"{len(paises) - saida['meta']['total_acao'] - saida['meta']['total_monitoramento']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
