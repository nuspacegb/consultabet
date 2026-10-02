# Nu · Consulta

Consulta rápida a listas oficiais brasileiras, para apoio a análises de
prevenção à lavagem de dinheiro.

**→ [nuspacegb.github.io/consultabet](https://nuspacegb.github.io/consultabet/)**

Site estático, sem servidor e sem banco de dados. Três robôs mantêm as
bases em dia; o navegador faz o resto.

---

## O que dá para consultar

| Base | Fonte | O que responde |
|---|---|---|
| **Casas de apostas** | SPA/MF (gov.br) | se a empresa consta na lista oficial de autorizadas |
| **Instituições de Pagamento** | Banco Central | a situação da instituição: autorizada, sem atividade, cancelada |
| **Países · GAFI** | COAF | se o país consta nas listas do GAFI, pela sigla do alerta (ex.: `BOL`) |

Busca por marca, razão social, CNPJ (inclusive a raiz, de uma filial) ou
sigla de país.

---

## O princípio

**Uma resposta errada é pior do que nenhuma resposta.**

A versão anterior desta ferramenta tinha uma falha silenciosa: quando a
raspagem da fonte oficial falhava, ela publicava uma base vazia. O site
continuava no ar, bonito, respondendo "não consta" para todas as
empresas — a pior resposta possível, porque parecia um resultado.

Tudo aqui é construído em volta disso:

- **O robô morre alto.** Se a fonte não responde como esperado, ele falha
  e avisa, em vez de publicar o que conseguiu.
- **Mudança na lista vira Pull Request**, não commit direto. Uma pessoa
  lê o que mudou antes de ir para o ar.
- **A tela mostra quando a fonte foi conferida.** Se a base envelhece, o
  próprio site avisa.
- **"Não encontrei" e "não consta" são respostas diferentes**, e aparecem
  diferentes. Na consulta do GAFI, a base carrega os 249 países com
  código ISO justamente para saber distinguir *"este país não tem
  restrição"* de *"não reconheço esse código"*.
- **Constar na base não é estar regular.** Instituições com autorização
  cancelada aparecem em vermelho, com aviso explícito — uma consulta que
  respondesse apenas "achei / não achei" as mostraria como regulares.

---

## Como as bases se atualizam

| Robô | Quando | O que faz |
|---|---|---|
| `atualizar.yml` | dias úteis, 09:00 | lê a lista da SPA/MF; abre PR se mudou |
| `atualizar-ips.yml` | dias úteis, 08:47 | lê a API de dados abertos do Banco Central |
| `vigiar-gafi.yml` | segundas, 09:20 | avisa se a página do COAF mudou |
| `avisar-slack.yml` | segundas, 10:00 | resumo semanal |
| `testar-api-bcb.yml` | manual | diagnóstico da API do Banco Central |

Quando nada muda, o robô grava só o horário da verificação — direto na
`main`, sem PR. Não faz sentido pedir aprovação para um relógio.

### O GAFI é manual, de propósito

São 25 países mudando três vezes por ano, nas plenárias do GAFI
(fevereiro, junho e outubro). Raspar isso seria código frágil defendendo
um ganho pequeno, e que quebraria em silêncio entre plenárias — quando
ninguém está olhando.

Em vez disso, o `vigiar-gafi.yml` só avisa, e a atualização leva cinco
minutos:

1. editar as listas no topo de **`gerar_gafi.py`**
2. `python3 gerar_gafi.py`
3. subir o `gafi.json` gerado

O script se recusa a gerar se um código de país não existir na base ISO ou
se a contagem não bater com o declarado — um erro de digitação não vira
base errada publicada.

---

## Os arquivos

```
index.html            o site inteiro, num arquivo só
dados.json            casas de apostas          ← robô
ips.json              instituições de pagamento ← robô
gafi.json             países + listas do GAFI   ← manual, 3x/ano
historico*.json       o que mudou na última alteração
gafi_vigia.json       impressão digital da página do COAF ← robô

scraper.py            lê a SPA/MF
scraper_ips.py        lê a API do Banco Central
gerar_gafi.py         monta o gafi.json a partir da base ISO
vigiar_gafi.py        confere se a página do COAF mudou
avisar_slack.py       monta as mensagens de aviso
```

---

## Ressalva

Ferramenta informativa, sem valor de certidão. As fontes definitivas são
a **Secretaria de Prêmios e Apostas do Ministério da Fazenda**, o **Banco
Central do Brasil** e o **COAF**. Em caso de divergência, vale sempre a
publicação oficial.

Estar fora das listas do GAFI não significa ausência de risco — significa
apenas que o país não consta nos comunicados daquela data.

> **Nota, outubro de 2026.** A Medida Provisória de 25/09/2026 proibiu a
> atuação de casas de apostas no país. A base de apostas mantém o registro
> do que constava na lista oficial, o que segue sendo necessário para
> análise retrospectiva.
