import os
import re
import json
import requests
from bs4 import BeautifulSoup
import pdfplumber

URL_GOV = "https://www.gov.br/fazenda/pt-br/composicao/orgaos/secretaria-de-premios-e-apostas/lista-de-empresas"

def buscar_link_pdf():
    print("Acessando o site do Ministério da Fazenda...")
    response = requests.get(URL_GOV, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Varre os elementos da página para isolar os blocos de texto
    for elemento in soup.find_all(['p', 'div', 'li']):
        texto_bloco = elemento.get_text().lower()
        
        # Garante que encontrou o PRIMEIRO bloco e ignora o de liminares judiciais
        if "autorizadas a ofertar apostas" in texto_bloco and "determinação judicial" not in texto_bloco:
            # Busca o link "Visualizar PDF" especificamente dentro deste bloco isolado
            for link in elemento.find_all('a', href=True):
                if "visualizar pdf" in link.get_text().lower():
                    print(f"Link oficial localizado: {link['href']}")
                    return link['href']
                    
    print("Aviso: Link do PDF oficial não foi localizado.")
    return None

def extrair_dados_pdf(url_pdf):
    print(f"Baixando e processando o PDF: {url_pdf}")
    response = requests.get(url_pdf)
    pdf_path = "lista_atualizada.pdf"
    
    with open(pdf_path, "wb") as f:
        f.write(response.content)
        
    nova_base = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for pagina in pdf.pages:
            tabela = pagina.extract_table()
            if not tabela:
                continue
                
            for linha in tabela:
                if not linha or "CNPJ" in str(linha) or "PORTARIA" in str(linha):
                    continue
                
                # Limpa espaços em branco extras das células
                texto_linha = [str(celula).strip() for celula in linha if celula]
                
                # Procura o CNPJ usando Expressão Regular
                cnpj_match = None
                for item in texto_linha:
                    match = re.search(r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}', item)
                    if match:
                        cnpj_match = match.group(0)
                        break
                
                if cnpj_match:
                    # Mapeia as colunas baseado na estrutura padrão da SPA/MF
                    portaria = texto_linha[0].split("\n")[0] if len(texto_linha) > 0 else ""
                    razao_social = texto_linha[1].replace("\n", " ") if len(texto_linha) > 1 else ""
                    marcas = texto_linha[3].replace("\n", ", ") if len(texto_linha) > 3 else ""
                    requerimento = texto_linha[-1].split("\n")[0] if len(texto_linha) > 4 else ""
                    
                    # Evita duplicados na leitura de quebras de página do PDF
                    if not any(item['cnpj'] == cnpj_match for item in nova_base):
                        nova_base.append({
                            "cnpj": cnpj_match,
                            "razao_social": razao_social.upper(),
                            "marcas": marcas.upper(),
                            "portaria": portaria,
                            "requerimento": requerimento
                        })
                        
    if os.path.exists(pdf_path):
        os.remove(pdf_path)
    return nova_base

def atualizar_arquivos():
    url_pdf = buscar_link_pdf()
    if not url_pdf:
        return False
        
    novos_dados = extrair_dados_pdf(url_pdf)
    if not novos_dados:
        print("Nenhum dado pôde ser extraído do arquivo.")
        return False
        
    # Compara com a base atual antes de sobrescrever
    if os.path.exists('dados.json'):
        with open('dados.json', 'r', encoding='utf-8') as f:
            try:
                dados_antigos = json.load(f)
                if len(dados_antigos) == len(novos_dados):
                    print("A base do site já possui o mesmo número de empresas. Pulando gravação.")
                    return False
            except json.JSONDecodeError:
                pass

    # Grava o novo arquivo JSON limpo
    with open('dados.json', 'w', encoding='utf-8') as f:
        json.dump(novos_dados, f, ensure_ascii=False, indent=2)
    print(f"Sucesso! dados.json atualizado com {len(novos_dados)} empresas.")
    return True

if __name__ == "__main__":
    atualizar_arquivos()
