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

# Importar as bibliotecas
import osgeo.gdal as gdal
import osgeo.ogr as ogr

import numpy as np
from scipy import ndimage
from PIL import Image
import re
import osr
import zipfile
from datetime import datetime

from pathlib import Path
import shutil


#Define o EPSG de Portugal continental
EPSG_PORTUGAL = 3763

#Define o caminho das pastas resultados e temporarios
caminhoimagoriginais = Path(__file__).parent.parent
pasta_resultados = caminhoimagoriginais / "resultados"
temporarios = caminhoimagoriginais / "temporarios"
pasta_resultados.mkdir(exist_ok=True)

#Função de reamostragem das imagens de satélite para pixel de 10 metros e EPSG 3763 e recorte pelos limites Municipio
def recorte(inptclip, outclip, shapefile):
    kw = {
        "dstAlpha": True,
        "cutlineDSName": str(shapefile),
        "cropToCutline": True,
        "srcSRS": "EPSG:32629",
        "dstSRS": "EPSG:3763",
        "xRes": 10,
        "yRes": 10,
    }
    if not isinstance(inptclip, list):
        inptclip = str(inptclip)
    else:
        inptclip = [str(caminho) for caminho in inptclip]
    gdal.Warp(str(outclip), inptclip, **kw)
    return outclip


#Procura dentro do ZIP das imagens do sentinel2, as imagens jp2 com melhor resulução para cada banda
def acha_melhor_imagem(banda, ficheiro_zip):
    imagens_na_banda = [
        nome
        for nome in ficheiro_zip.namelist()
        if re.search(fr"B{banda:02d}_\d\dm\.jp2$", nome)
    ]
    imagens_na_banda.sort(key=lambda nome: int(nome.split("_")[-1].split("m")[0]))
    return imagens_na_banda[0]


#Realiza o recorte pelo shapefile do munícipio das bandas pretendidas antes e depois do incêndio e colocas no ficheiro temporario
def realiza_recorte(zip_pre, zip_pos, shapefile, bandas_pre, bandas_pos, temporarios):
    # ficheiros antes do incendio -
    if not isinstance(zip_pre, list):
        zip_pre = [zip_pre]
        zip_pos = [zip_pos]

    ficheiros_recortados = {}

    ficheiros_recortados["pre"] = realiza_recorte_com_mosaico(
        extrai_bandas_do_zip_do_satelite(zip_pre, bandas_pre, temporarios),
        shapefile, bandas_pre, temporarios, "pre"
    )

    ficheiros_recortados["pos"] = realiza_recorte_com_mosaico(
        extrai_bandas_do_zip_do_satelite(zip_pos, bandas_pos, temporarios),
        shapefile, bandas_pos, temporarios, "pos"
    )

    return ficheiros_recortados


# De cada ficheiro do satelite2, extrai as bandas desejadas na melhor resolução .jp2 para a pasta temporarios
def extrai_bandas_do_zip_do_satelite(ficheiros_de_satelite, bandas, temporarios):
    imagens_de_bandas = {}
    for ficheiro_satelite in ficheiros_de_satelite:
        dados = zipfile.ZipFile(ficheiro_satelite)
        for banda in bandas:
            if banda not in imagens_de_bandas:
                imagens_de_bandas[banda] = []
            caminho_no_zip = acha_melhor_imagem(banda, dados)
            caminho_imagem = Path(dados.extract(caminho_no_zip, temporarios))
            imagens_de_bandas[banda].append(temporarios / caminho_no_zip)
    return imagens_de_bandas


# Realiza o recorte das bandas pela shapefile do municipio
def realiza_recorte_com_mosaico(imagens_de_bandas, shapefile, bandas, temporarios, prefixo):
    ficheiros_recortados = {}
    for banda in bandas:
        outclip = temporarios / f"{prefixo}_B{banda:02d}_10m_clip.tif"
        recorte(imagens_de_bandas[banda], outclip, shapefile)
        ficheiros_recortados[banda] = outclip
    return ficheiros_recortados


#Cria as composições coloridas RGB com as bandas (4 3 2), (8 4 3) e (12 8 4) com resolução de 10 metros 
def composicao_rgb(ficheiros, prefixo_saida, referencia):
    resultados = []
    for composicoes in [(4, 3, 2), (8, 4, 3), (12, 8, 4)]:
        canais = []
        for banda in composicoes:
            openb = gdal.Open(str(ficheiros[banda]))
            canais.append(openb.GetRasterBand(1).ReadAsArray().astype(np.float))
        caminho = pasta_resultados / (prefixo_saida + f"_RGB_{'_'.join(str(c) for c in composicoes)}.tif")
        guarda_imagem_geo(caminho, np.dstack(canais), referencia)
        resultados.append(caminho)
    return resultados

# Guarda a composição colorida RGB de falsa cor em formato .tif mas sem ser georreferenciada
def guarda_imagem_pil(resultado, canais, referencia):
    caminho_temp = temporarios / "imagem_nao_georefenciada_843.tif"
    dados = np.ndarray(canais.shape, dtype="uint8")
    for canal in (0, 1, 2):
        max_val = canais[:, :, canal].max()
        print(max_val)
        if max_val == 0:
            max_val = 1
        dados[:, :, canal] = 255 * canais[:, :, canal] / max_val
    img = Image.fromarray(dados)
    img.save(caminho_temp)

# Abre a composição colorida RGB de falsa cor não georreferenciada e cria a mesma mas já georreferencia na pasta resultados
def guarda_imagem_geo(caminho_resultado, dados, referencia):
    dataset = gdal.Open(str(referencia), gdal.GA_ReadOnly)
    imgdriver = gdal.GetDriverByName("GTiff")
    imgdriver.Register()
    nCols, nRows = dataset.RasterXSize, dataset.RasterYSize
    reclassificada = imgdriver.Create(
        str(caminho_resultado), nCols, nRows, 3, gdal.GDT_Float32
    )
    geoTransf = dataset.GetGeoTransform()
    reclassificada.SetGeoTransform(geoTransf)
    proj = dataset.GetProjection()
    reclassificada.SetProjection(proj)
    #No final do processo apresenta 100 "*"
    print(dados.shape, "*" * 100)
    for i in range(3):
        banda = reclassificada.GetRasterBand(i + 1)
        banda.WriteArray(dados[:, :, i])
        banda.SetNoDataValue(-9999)
    reclassificada.FlushCache()
    reclassificada = None
    banda = None

# Função de calculo NDVI e DNBR (depende das bandas)
def calcula(ficheiros, banda1, banda2):
    openb = gdal.Open(str(ficheiros[banda1]))
    b_a = openb.GetRasterBand(1).ReadAsArray().astype(np.float)
    openb = gdal.Open(str(ficheiros[banda2]))
    b_b = openb.GetRasterBand(1).ReadAsArray().astype(np.float)
    # Calcular o pre NDVI/DNBR com a mascara e atribuir o valor -9999 aos valores de nulos
    d1 = b_a - b_b
    s1 = b_a + b_b
    pre_calculado = np.divide(d1, s1, out=np.full_like(d1, -9999), where=s1 != 0)
    return pre_calculado


def processa(
    zip_pre,
    zip_pos,
    prefixo_saida,
    valor_filtro_reclass,
    bandas,
    shape_recorte,
    update=None,
):
    if not update:
        update = lambda msg, v: None
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    temporarios = caminhoimagoriginais / f"temporarios{timestamp}"
    temporarios.mkdir(exist_ok=True)
    #Mensagem de indicação do que está a realizar na barra de progressos
    update(5, "A realizar os recortes das bandas do sentinel 2 pelos limites do munícipio ")

    bandas_pre = bandas
    bandas_pos = list(bandas)
    for b in (12, 8, 4, 3, 2):
        if b not in bandas_pos:
            bandas_pos.append(b)
    
    fich_recortados = realiza_recorte(
        zip_pre, zip_pos, shape_recorte, bandas_pre, bandas_pos, temporarios
    )
    #Mensagem de indicação do que está a realizar na barra de progressos
    update(20, "A guardar as composições RGB das bandas [4 3 2], [8 4 3] e [12 8 4]")
    caminho_anterior = fich_recortados["pre"][bandas[0]]
    imagens_compostas = composicao_rgb(
        fich_recortados["pos"], prefixo_saida, referencia=caminho_anterior
    )
    pre = calcula(fich_recortados["pre"], bandas[0], bandas[1])
    pos = calcula(fich_recortados["pos"], bandas[0], bandas[1])

    # Calcular a diferenca entre NDVI/NDBR
    diferenca = pre - pos

    #Mensagem de indicação do que está a realizar na barra de progressos
    update(25, "A aplicar o filtro mediana 5x5")
    # Aplicar o filtro mediana de  5x5
    filtro = ndimage.median_filter(diferenca, 5)

    # Reclassificar o filtro em que:
    # As celulas com valor igual ou superior ao valor do filtro passam a ter valor 1
    reclass = (filtro > valor_filtro_reclass) * 1

    #Mensagem de indicação do que está a realizar na barra de progressos
    update(25, "A criar a imagem reclassificada")
    # Criar o tif da reclassificacao
    caminho_tif = temporarios / "diferenca_reclassificada.tif"

    georefencia_imagem(caminho_anterior, caminho_tif, reclass)

    caminho_nao_filtrado = temporarios / "diferenca_sem_filtros.tif"
    georefencia_imagem(caminho_anterior, caminho_nao_filtrado, diferenca)

    #Mensagem de indicação do que está a realizar na barra de progressos
    update(70, "A transformar a imagem reclassificada em vetorial")
    # Criar a Shapefile a partir do raster reclassificado só com os valores de 1
    # abrir o raster a converter em vetor
    band = gdal.Open(str(caminho_tif))
    srsband = band.GetRasterBand(1)
    # criar a camada vetorial
    drv = ogr.GetDriverByName("ESRI Shapefile")
    ficheiro_destino = pasta_resultados / (prefixo_saida + ".shp")
    ficheiro_destino.write_bytes(shape_recorte.read_bytes())
    dst_ds = drv.CreateDataSource(str(ficheiro_destino))
    dst_layer = dst_ds.CreateLayer(str(ficheiro_destino), srs=None)
    fd = ogr.FieldDefn("DN", ogr.OFTInteger)
    dst_layer.CreateField(fd)
    # Criar a shapefile com os valores de 1 no campo DN
    gdal.Polygonize(srsband, srsband, dst_layer, -0, [], callback=None)
    # Criar o ficheiro do sistema de referencia PRJ
    spatialRef = osr.SpatialReference()
    spatialRef.ImportFromEPSG(EPSG_PORTUGAL)
    spatialRef.MorphToESRI()

    #Mensagem de indicação do que está a realizar na barra de progressos
    update(95, "A criar o arquivo de projeto")
    with open(str(pasta_resultados / (prefixo_saida + ".prj")), "w") as prj_file:
        prj_file.write(spatialRef.ExportToWkt())
    #Mensagem de indicação do que está a realizar na barra de progressos
    update(99, "A remover os ficheiros temporários")
    #Apaga a pasta dos ficherios temporários
    shutil.rmtree(temporarios)
    #Mensagem de indicação do que está a realizar na barra de progressos
    update(100, "Processo Completo: A Shapefile e a composição de falsa cor está na pasta 'resultados'")
    return str(pasta_resultados / (prefixo_saida + ".shp"))


def georefencia_imagem(caminho_anterior, caminho_tif, dados):
    # Criar o tif da reclassificacao
    dataset = gdal.Open(str(caminho_anterior), gdal.GA_ReadOnly)
    imgdriver = gdal.GetDriverByName("GTiff")
    imgdriver.Register()
    nCols = dataset.RasterXSize
    nRows = dataset.RasterYSize
    reclndvi = imgdriver.Create(str(caminho_tif), nCols, nRows, 1, gdal.GDT_Float32)
    geoTransf = dataset.GetGeoTransform()
    reclndvi.SetGeoTransform(geoTransf)
    proj = dataset.GetProjection()
    reclndvi.SetProjection(proj)
    banda = reclndvi.GetRasterBand(1)
    banda.WriteArray(dados)
    banda.SetNoDataValue(-9999)
    reclndvi.FlushCache()
    reclndvi = None
    banda = None

#Função que define o processo do dndvi com a escolha das bandas e do valor para áreas ardidas da reclassificação
def processa_dndvi(zip_pre, zip_pos, prefixo, shape_recorte, update=None):
    return processa(
        zip_pre,
        zip_pos,
        prefixo,
        0.17767,
        bandas=(8, 4),
        shape_recorte=shape_recorte,
        update=update,
    )

#Função que define o processo do dnbr com a escolha das bandas e do valor para áreas ardidas da reclassificação
def processa_dnbr(zip_pre, zip_pos, prefixo, shape_recorte, update=None):
    return processa(
        zip_pre,
        zip_pos,
        prefixo,
        0.100,
        bandas=(8, 12),
        shape_recorte=shape_recorte,
        update=update,
    )
