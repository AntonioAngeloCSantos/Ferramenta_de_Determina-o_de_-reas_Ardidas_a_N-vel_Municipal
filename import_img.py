# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Nome da Ferramenta: Determinação de Áreas Ardidas a Nível Municipal           
#                                           
# Proposito: Ferramenta que utiliza imagens Sentinel2 com resolução 10 metros
#            para criar um shapefile das áreas ardidas
#
# Autor: Antonio Ângelo Candeias dos Santos
#
# Versão: 01/2020
# Copyright:(c) Antonio A C Santos 2020
#-------------------------------------------------------------------------------

#Importar bibliotecas
from pathlib import Path

from sentinelsat import SentinelAPI

# Definição dos caminhos das pastas imagens na raiz e se não existir cria a pasta
caminhoimagoriginais= Path(__file__).parent.parent
pasta_imagens_satelite = caminhoimagoriginais / "imagens"
pasta_imagens_satelite.mkdir(exist_ok=True)

# Ligação API do sentinelsat, em que sentinel_2 é o username e a password
api = SentinelAPI('sentinel_2', 'sentinel_2', 'https://scihub.copernicus.eu/dhus',show_progressbars=True)
def lerimagens(bbox,dtin,dtfim, cobertura_maxima=10):
     # Pesquisa de imagens do Sentinel 2 comprocessamento do Nivel 2A, pelos limites do Municipio (DICO), no intervalo de tempo e com uma cobertura de nuvem inferior ao defenido que por defeito é 5%
    products = api.query(bbox, date =(dtin,dtfim), platformname = 'Sentinel-2', cloudcoverpercentage = f'[0 TO {cobertura_maxima}]', processinglevel='Level-2A')
    # Visualizar as imagens disponiveis
    img=api.to_geojson(products)
    return(img)


# Retorna o caminho para o ficheiro de imagem do satélite, se já está disponível a imagem na pasta "imagens", ou se tem que ser descarregada
def imagem_ja_descarregada(uuid):
    fich_descarregados = (pasta_imagens_satelite/ "ficheiros_descarregados.txt")
    if not fich_descarregados.exists():
        fich_descarregados.write_text("")

    descarregados = fich_descarregados.read_text().split("\n")
    for linha in descarregados:
        if not "=" in linha:
            continue
        uuid_imagem, nome_ficheiro = linha.split("=")
        ficheiro_imagem = pasta_imagens_satelite/nome_ficheiro
        if uuid_imagem == uuid and ficheiro_imagem.exists():
            return ficheiro_imagem
    return None


# Descarregar as imagens e adicionar ao ficheiro descarregados.txt o nome da imagem para em seguida visualizar no tkinter
def download(uuid, title, update):

    if imagem_ja_descarregada(uuid):
        print("Imagem com uuid f{uuid} já existe - não é necessario efetuar o Download ")
        return False

    fich_descarregados = (pasta_imagens_satelite/ "ficheiros_descarregados.txt")
    ficheiros_antes = set(pasta_imagens_satelite.iterdir())
    api.download(uuid, str(pasta_imagens_satelite))
    ficheiros_depois = set(pasta_imagens_satelite.iterdir())
    ficheiro_descarregado = (ficheiros_depois - ficheiros_antes)
    if ficheiro_descarregado:
        descarregados = fich_descarregados.read_text().split("\n")
        ficheiro_descarregado = ficheiro_descarregado.pop()
        descarregados.append(f"{uuid}={ficheiro_descarregado.name}")
        fich_descarregados.write_text("\n".join(descarregados))
    return True



