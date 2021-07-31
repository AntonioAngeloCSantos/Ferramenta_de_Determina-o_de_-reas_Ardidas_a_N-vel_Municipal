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
import tkinter
tk = tkinter
from sentinel import ler_envelope

#Variaveis para o tamanho da caixa a distancia à margem
tamanho = 200
margem = 15

# Obtém os pontos do polígono Xmim, Xmax, Ymin, Ymax do município através do código DICO
def obter_coords_municipio(codigo):
    bbox = ler_envelope.envelope(codigo)
    return bbox_to_coord(bbox)

#Converte o poligono do município para pares de coordenadas
def bbox_to_coord(bbox):
    raw_coords = bbox.split("(")[-1].split(")")[0].split(",")
    final_coords = []
    for coords in raw_coords:
        tmp = coords.split(" ")
        final_coords.append((float(tmp[0]), float(tmp[1])))
    return final_coords

# Calcula a coordenda do canto superior esquerdo
def calcula_translado_escala(coordenadas):
    # encontrar translado do canto superior esquerdo
    min_x = min_y = 180
    max_x = max_y = -180
    for coord in coordenadas:
        if coord[0] < min_x: min_x = coord[0]
        if coord[1] < min_y: min_y = coord[1]
        if coord[0] > max_x: max_x = coord[0]
        if coord[1] > max_y: max_y = coord[1]
    translado = min_x, min_y
    escala = (tamanho - margem * 2) / (max_x - min_x)
    return translado, escala

#Desenha os poligonos do municipio e das imagens sentinel2
def desenha_poligono(parent, coord_municipio, coord_imagem, canvas=None):
    geom_municipio = calcula_translado_escala(coord_municipio)
    geom_imagem = calcula_translado_escala(coord_imagem)
    if not canvas:
        canvas = tkinter.Canvas(parent, width=tamanho, height=tamanho)
        canvas.pack()
    else:
        canvas.delete(tkinter.ALL)
    escala = min(geom_municipio[1], geom_imagem[1])
    if geom_municipio[1] < geom_imagem[1]:
        translado = geom_municipio[0]
    else:
        translado = geom_imagem[0]
    # Define a cor do poligono das imagens do sentinel2 a vermelho e a do municipio a verde
    for coordenadas, cor in ((coord_imagem, "red"), (coord_municipio, "green")):
        elementos_linha = []
        for x, y in coordenadas:
            x -= translado[0]
            x *= escala
            x += margem
            y -= translado[1]
            y *= escala
            y += margem
            y = tamanho - y
            elementos_linha.extend([x, y])
        canvas.create_line(*elementos_linha, fill=cor)
    parent.update()
    return canvas
