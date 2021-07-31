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
from pathlib import Path
import osgeo.ogr as ogr

# Caminho do ficheiro Carta Administrativa Oficial de Portugal (CAOP)
entrada = str(Path(__file__).parent / 'CAOP.shp')

def envelope(dico):
    driver = ogr.GetDriverByName('ESRI Shapefile')
    # abrir a Shapefile da CAOP com o SRC 4326
    inDataSet = driver.Open(entrada)
    inLayer = inDataSet.GetLayer()
    # Selecionar o Municipio pretendido da pesquisa atraves do código DICO
    str="SELECT * FROM %s WHERE DICO = '%s' " %(inLayer.GetName(),dico)
    inDataSet.ExecuteSQL(str)
    #  recursos de entrada
    inFeature = inLayer.GetNextFeature()
    while inFeature:
         # obter a geometria de entrada
         geom = inFeature.GetGeometryRef()
         # Obter as coordendas dos pontos do poligono do Municipio selecionado
         bb=geom.GetEnvelope()
         inFeature = inLayer.GetNextFeature()
    # Salvar e fechar os shapefiles
    inDataSet = None
    # Obter os pontos do poligono Xmim, Xmax, Ymin, Ymax
    ring = ogr.Geometry(ogr.wkbLinearRing)
    ring.AddPoint(bb[0], bb[2])
    ring.AddPoint(bb[1], bb[2])
    ring.AddPoint(bb[1], bb[3])
    ring.AddPoint(bb[0], bb[3])
    ring.AddPoint(bb[0], bb[2])
    poly = ogr.Geometry(ogr.wkbPolygon)
    poly.AddGeometry(ring)
    footprint=poly.ExportToWkt()
    return(footprint)




