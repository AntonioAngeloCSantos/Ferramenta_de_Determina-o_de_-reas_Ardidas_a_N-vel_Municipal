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

#Importar as bibliotecas do Python
import subprocess
import platform
import os
import tkinter as tk
from datetime import date, datetime, timedelta
from tkinter.filedialog import askopenfilename
from tkinter import ttk
from pathlib import Path

import osgeo.ogr as ogr
from sentinel import ler_envelope, import_img, processa, geometry

#Variável do número de imagens que mostra antes e depois da data do incêndio
NUMERO_DE_IMAGENS = 10

#Definir a pasta raiz da ferramenta
pasta_raiz = Path(__file__).parent.parent
pasta_downloads = pasta_raiz / "downloads"

#Definir o espaçamento e o afastamento entre quadros (frames)
pack_style = {"padx": 6, "pady": 6}


class DatePicker:
    #Cria um frame e funções para ler uma data na janela tkinter#

    def __init__(self, parent, title, arrange=tk.TOP):
        fr = tk.Frame(parent)
        self.titulo = tk.Label(fr, text=title)
        self.titulo.pack(side=arrange, **pack_style)
        fr2 = tk.Frame(fr)
        fr2.pack(side=arrange)
        frame_day = tk.Frame(fr2)
        frame_month = tk.Frame(fr2)
        frame_year = tk.Frame(fr2)
        for f in (frame_day, frame_month, frame_year):
            f.pack(side=tk.LEFT, **pack_style)
        # Define que o dia e o mês possuem 2 dígitos e o ano 4 dígitos
        l_day = tk.Label(frame_day, text="dia")
        l_month = tk.Label(frame_month, text="mês")
        l_year = tk.Label(frame_year, text="ano")
        self.day = tk.Entry(frame_day, width=2)
        self.month = tk.Entry(frame_month, width=2)
        self.year = tk.Entry(frame_year, width=4)

        for wid in (l_day, self.day, l_month, self.month, l_year, self.year):
            wid.pack()
        self.frame = fr

    # Se digitar a data errada a mesma fica a vermelho e a correta a verde
    def get(self):
        try:
            day = int(self.day.get())
            month = int(self.month.get())
            year = int(self.year.get())
            final_date = date(year, month, day)
        except (ValueError, TypeError) as error:
            self.titulo["background"] = "red"
        else:
            self.titulo["background"] = "green"
            return final_date
        return None

    def get_as_datetime(self):
        date = self.get()
        return datetime(year=date.year, month=date.month, day=date.day)

#Define os metodos intermedios para ligação entre o tkinter e os restantes códigos
class SentinelMixin:
    #Cria a função que define as mensagens de erro no título da janela
    def erro(self, mensagem):
        self.top.title(mensagem)

    @staticmethod
    def obtem_data_imagem_satelite(imagem):
        return datetime.strptime(imagem["properties"]["ingestiondate"][:10],"%Y-%m-%d")

    #Utilidade para criar uma variavel junto com um rotulo de tkinter
    def add_entry(self, parent, text, default="", **kwargs):
        frame = tk.Frame(parent)
        frame.pack(**pack_style)
        label_codigo = tk.Label(frame, text=text)
        label_codigo.pack(side="left")
        variavel = tk.Variable(frame, value=default)
        codigo_entrada = tk.Entry(frame, textvariable=variavel, **kwargs)
        codigo_entrada.pack(side="left")
        return variavel

    # Cria a barra de progresso
    def create_progress_bar(self):
        frame = tk.Frame(self.top)
        frame.pack(fill="x", expand=True)
        self.progress_label = tk.Label(frame, text="")
        self.progress_label.pack()
        self.progressbar = ttk.Progressbar(frame)
        self.progressbar.pack(fill="x", expand=True)

    #Atualiza a barra de progresso que é chamada diretamente das funções em "processa.py"
    #para atualizar a barra de acordo com o passo que a ferramenta está a realizar
    def update_progress(self, valor, mensagem):
        self.progress_label["text"] = mensagem
        self.progressbar["value"] = valor
        self.top.update()

    #Cria uma barra de rolagem para ajudar na ListBox do tkinter e ao selecionar uma data da imagem esta fica a azul
    def list_with_scrollbar(self, fr, **pack_options):
        fr2= tk.Frame(fr)
        fr2.pack(**pack_options)
        scrollbar = tk.Scrollbar(fr2, orient=tk.VERTICAL)
        lista = tk.Listbox(fr2, selectbackground="blue",selectforeground="white", selectmode=tk.MULTIPLE, yscrollcommand=scrollbar.set, height=8)
        lista.pack(side=tk.LEFT)
        scrollbar.config(command=lista.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        return lista

#Métodos para validar parametros de entrada, titulos, ajuda etc..
class SentinelParametrosMixin:
    
    def exibe_titulo(self):
        self.top.title("Determinação de Áreas Ardidas a Nível Municipal")

    #Mostra a ajuda ao clicar no botão de ajuda
    def mostra_ajuda(self):
        filepath = str(Path(__file__).parent.parent / "ajuda.pdf")
        subprocess.call(('xdg-open', filepath))

    #Lê a geometria do município, de acordo com o código DICO e se essa geometria alterar,
    #mostra a posição do município em relação às imagens disponíveis para download na janela
    def codigo_dico_mudou(self):
        codigo = self.codigo.get()
        if len(codigo) != 4:
            self.erro("Código DICO precisa ter 4 dígitos")
            return
        self.exibe_titulo()
        self.coords_municipio = geometry.obter_coords_municipio(codigo)

 #Define a cobertura máxima de nuvens para pesquisa das imagens Sentinel2 que por defeito é de 5%
    @property
    def cobertura_maxima(self):
        try:
            valor = int(self._cobertura_nuvens.get())
        except (ValueError, TypeError):
            valor =  5
        return valor


    #Permite escolher a shapefile de recorte com a geometria do município
    def seleciona_ficheiro_recorte(self):
        ficheiro = askopenfilename(parent=self.top, defaultextension=".shp", title="Ficheiro de recorte", filetypes=[("shapefile", "*shp"), ("All files", "*")])
        ficheiro = Path(ficheiro)
        self.ficheiro_recorte = ficheiro
        self.nome_ficheiro_recorte["text"] = ficheiro.name
        self.verifica_imagens_selecionadas()

    #Habilita o botão para processar as imagens, mas somente se já foi escolhida a
    #shapefile de recorte e se estarem selecionadas duas imagens, já descarregadas
    def verifica_imagens_selecionadas(self, evento=None):
        if evento is not None:
            # quando é chamado por evento do tkinter, a imagem
            # ainda não está selecionada. Passamos o controle
            # para o tkinter, e corremos essa função de volta em
            # 20 mili-segundos - evento vem como 'None',
            # e temos a seleção já feita na lista.
            self.top.after(20, self.verifica_imagens_selecionadas, None)
            return
        imagens_pre, imagens_pos, imagens_a_descarregar = self.verifica_selecao()
        if not imagens_a_descarregar and imagens_pre and imagens_pos and hasattr(self, "ficheiro_recorte"):
            state = "normal"
        else:
            state = "disabled"
        self.botao_dndvi["state"] = state
        self.botao_dnbr["state"] = state
        self.botao_descarregar["state"] = "normal" if imagens_a_descarregar else "disabled"

    #Cria a lista das imagens para que possa ser realizado o download
    def cria_lista(self):
        fr_pai = tk.Frame(self.descarrega)
        fr_pai.pack(**pack_style)
        fr = tk.Frame(fr_pai)
        fr.pack(side=tk.LEFT)
        self.lista = self.list_with_scrollbar(fr, **pack_style)
        self.lista.bind("<Button-1>", lambda ev=None: (self.desenha_contorno_imagem(ev), self.verifica_imagens_selecionadas(ev)))
        #cria o botão para efetuar o download das imagens selecionadas
        self.botao_descarregar = tk.Button(fr, text="Download das imagens selecionadas", command=self.descarrega_novas_imagens, state="disabled")
        self.botao_descarregar.pack(**pack_style)
        fr_preview = tk.Frame(fr_pai, width=200, height=200)
        fr_preview.pack(side=tk.RIGHT)
        self.fr_preview = fr_preview

    #Mostra os contornos da imagem de satélite em relação ao contorno do município, de acordo com o código DICO
    def desenha_contorno_imagem(self, evento=None, selecionadas_anteriores=None):
        selecionadas = self.lista.curselection()
        if evento is not None:
            # volta ao tkinter em 20ms com a seleção já feita e mostra na janela.
            tmp = lambda: self.desenha_contorno_imagem(selecionadas_anteriores=selecionadas)
            self.top.after(20, tmp)
            return
        # descobre qual das imagens novas do sentinel2 está selecionada
        imagem_clicada = list(set(selecionadas) - set(selecionadas_anteriores))
        # se uma imagem da lista foi des-selecionada, apaga o contorno do município
        if not imagem_clicada and self.canvas_contorno:
            self.canvas_contorno.delete(tk.ALL)
            return
        # chama função para desenhar os contornos do munícipio e da imagem sentinel2
        try:
            imagem = self.indice_de_imagens[imagem_clicada[0]][0]
        except KeyError:
            # utilizador clicou no separador "Data do incendio":
            self.lista.selection_clear(imagem_clicada[0])
            return
        coords_imagem = imagem["geometry"]["coordinates"][0][0]
        self.canvas_contorno = geometry.desenha_poligono(self.fr_preview, self.coords_municipio, coords_imagem, canvas=getattr(self, "canvas_contorno", None))


class MainApp(SentinelMixin, SentinelParametrosMixin):
    def __init__(self):
        #cria a janela da interface grafica com 700 x 700
        self.top = top = tk.Tk()
        self.top.geometry("700x700")
        #Atribuir o titulo da interface gráfica como "Determinação de Áreas Ardidas a Nível Municipal"
        self.exibe_titulo()

        #Cria o botão de "Ajuda" da ferramenta
        self.botao_ajuda = tk.Button(self.top, text="Ajuda", command=self.mostra_ajuda)
        self.botao_ajuda.pack()

        #Pesquisa as imagens disponíveis no Sentinel2 pelo código de identificação único do concelho DICO que por definição é "0803" Aljezur
        self.codigo = self.add_entry(self.top, "Introduzir o código DICO do Concelho", default="0803")

        
        # Cria quadro para data de incendio e cobertura de nuvens
        fr = tk.Frame(top)
        fr.pack(side=tk.TOP)

        #Cria o quadro para indicar a data que ocorreu o incêndio
        fr_data = tk.Frame(fr)
        fr_data.pack(side=tk.TOP)
        self.data_inicio = DatePicker(fr_data, "Indique a data do incêndio", arrange=tk.LEFT)
        self.data_inicio.frame.pack(side=tk.LEFT, expand=True, **pack_style)


        #Cria o quadro para indicar a cobertura maxima de nuvens, que por defeito é 5% e com uma largura de 3 digitos
        fr_cobertura = tk.Frame(fr)
        fr_cobertura.pack(side=tk.TOP)
        self._cobertura_nuvens = self.add_entry(fr_cobertura, "Cobertura de nuvens até (%)", default="5", width=3)

        #Cria o botão para "Ver as imagens disponiveis antes e depois do incêndio"
        obter_imagens = tk.Button(top, text="Ver as imagens disponiveis antes e depois do incêndio", command=self.selecionar_imagens)
        obter_imagens.pack(side=tk.TOP, **pack_style)
        self.descarrega = tk.Frame(self.top)
        self.descarrega.pack()
        self.cria_lista()

        #Criar quadro para selecionar a Shapefile de recorte pelo município
        fr_recorte = tk.Frame(self.top, **pack_style)
        fr_recorte.pack()
        lb = tk.Label(fr_recorte, text="Selecione a Shapefile de recorte do município:")
        lb.pack()
        fr2 = tk.Frame(fr_recorte)
        fr2.pack()

        #Cria o botão para procurar a "Shapefile de recorte pelo município
        file_button = tk.Button(fr2, text="Procurar a shp", command=self.seleciona_ficheiro_recorte )
        file_button.pack(side="left")
        self.nome_ficheiro_recorte = tk.Label(fr2, text="")
        self.nome_ficheiro_recorte.pack(side="left")

        #Cria o caixa de diálogo com o nome da Shapefile das áreas ardidas que por defeito aparece "aap" iniciais de "áreas ardidas prováveis"
        self.codigo.trace("w", lambda name, index, mode: self.codigo_dico_mudou())  # "lambda" recebe qualquer numero do código DICO
        self.codigo_dico_mudou()
        self.prefixo_de_destino = self.add_entry(self.top, "Escolha o nome a atribuir à Shapefile das áreas ardidas prováveis", default="aap")

        #Cria os botões de "Criar o dNDVI" e o "Criar o dNBR"
        frame_botoes = tk.Frame(self.top)
        frame_botoes.pack(**pack_style)
        self.botao_dndvi = tk.Button(frame_botoes, text="Criar o dNDVI", command=self.processa_imagens, state="disabled")
        self.botao_dnbr = tk.Button(frame_botoes, text="Criar o dNBR", command=(lambda: self.processa_imagens(alvo="dnbr")), state="disabled")
        self.botao_dndvi.pack()
        self.botao_dnbr.pack()
        self.create_progress_bar()

    #Inicia o processo principal que extrair as imagens pelas bandas corretas de dentro do ficheiro ZIP e criar os ficheiros finais na pasta "resultados"
    def processa_imagens(self, alvo="dndvi"):
        imagens_pre, imagens_pos, imagens_nao_baixadas = self.verifica_selecao()

        if imagens_nao_baixadas or not imagens_pre or not imagens_pos:
            print("Imagens ainda não estão prontas para processamento")
            return

        funcao = processa.processa_dndvi if alvo == "dndvi" else processa.processa_dnbr
        destino = f"{self.prefixo_de_destino.get()}_{self.data_inicio.get().strftime('%Y%m%d') }_{alvo}"
        ficheiro_qgis = funcao(imagens_pre, imagens_pos, destino, self.ficheiro_recorte, self.update_progress)

    #Função para descarregar as imagens do Sentinel2 e atualiza a barra de progresso
    def descarrega_novas_imagens(self):
        imagens = self.verifica_selecao()[2]

        passos = 100 // len(imagens)
        self.update_progress(0, f"A realizar o download das {len(imagens)} imagens")
        baixou_imagem_nova = False
        for indice, imagem in enumerate(imagens):
            uuid=imagem['properties']['uuid']
            title=imagem['properties']['title']
            print(f"\nA descarregar: {title} com identificador {uuid}")
            baixou_imagem_nova |= import_img.download(uuid,title, self.update_progress)
            self.update_progress(passos * indice, f"A realizar o download das imagens ")
        self.update_progress(100, f"Imagens já descarregadas - pronto para criar o dNVI e ou dNBR")
        if not baixou_imagem_nova:
            self.error("Imagens selecionadas já descarregadas")
        self.selecionar_imagens()

    # Verifica quais das imagens selecioandas já estão baixadas, e se há alguma por descarregar
    def verifica_selecao(self):
        indices = self.lista.curselection()
        imagens = [self.indice_de_imagens[i] for i in indices]
        data_inicio = self.data_inicio.get_as_datetime()
        imagens_pre_selecionadas = [ficheiro for imagem, ficheiro in imagens if ficheiro and self.obtem_data_imagem_satelite(imagem) <= data_inicio]
        imagens_pos_selecionadas = [ficheiro for imagem, ficheiro in imagens if ficheiro and self.obtem_data_imagem_satelite(imagem) >= data_inicio]
        imagens_por_descarregar = [imagem for imagem, ficheiro in imagens if ficheiro is None]
        return imagens_pre_selecionadas, imagens_pos_selecionadas, imagens_por_descarregar

    #Mostra a lista de imagens disponíveis próximas à data do incêndio deixando data do incêndio em destaque a meio
    def selecionar_imagens(self):
        data_inicio = self.data_inicio.get()
        if not data_inicio:
            self.erro("Preencha a data corretamente: DIA(DD) MÊS (MM) ANO (AAAA)") #se a data está mal preenchida mostra mensagem de erro
            return
        codigo = self.codigo.get()
        if len(codigo) != 4:
            self.erro("Preencha o código do município")#se não existir código DICO preenchido corretamente (4 dígitos) mostra mensagem de erro
            return
        #Chama a api do sentinel2 para obter a lista de imagens disponíveis
        features = self.obter_imagens(data_inicio, codigo)
        #Mostra as datas imagens do sentinel2 diponiveis e se existir mais que uma para a mesma mostra a mesma data mais 1, 2, 3...
        datas = {}
        repetidas = {}
        for imagem in features:
            chave = self.obtem_data_imagem_satelite(imagem)
            contagem = repetidas[chave] = repetidas.setdefault(chave, 0) + 1
            datas[(chave, contagem)] = imagem
        #Cria uma lista das imagens já descarregadas e os controles de seleção, se ainda não foram criados.
        if not hasattr(self, "lista"):
            self.cria_lista()
        else:
            self.lista.delete(0, tk.END)
        #Insere na lista das imagens já descarregadas o nome do ficheiro descarregado e se já existe estes aparecem na ListBox com um * e a verde claro 
        def _insere_uma_na_lista(data, contador):
            nonlocal cont_imagem
            imagem = datas[data, contador]
            ja_existe = import_img.imagem_ja_descarregada(imagem["properties"]["uuid"])

            self.lista.insert(
                tk.END,
                data.strftime("%d/%m/%Y") +
                ("" if contador == 1 else f"({contador})") + (' *' if ja_existe else '')
            )

            if ja_existe:
                self.lista.itemconfig(tk.END, bg="#dfb")
            self.indice_de_imagens[cont_imagem] = (imagem, ja_existe)
            cont_imagem += 1

        #Função para mostar a lista de imagens na ListBox do tkinter
        def _insere_varias_na_lista(lista_imagens):
            nonlocal cont_imagem
            for data_antes, cont2 in lista_imagens:
                _insere_uma_na_lista(data_antes, cont2)

        #para separar as imagens de antes ou depois da data do incêndio
        antes_do_incendio = True
        self.indice_de_imagens = {}
        imagens_antes_incendio = []
        cont_imagem = 0
        #Percorre as imagens disponiveis, pelas datas da mais antiga para a mais recente
        for data, cont1 in reversed(list(datas)):
            #se a imagem atual é a primeira depois da data do incêndio
            #preencher a lista com as imagens anteriores ao incêndio
            if data.isoformat() > data_inicio.isoformat() and antes_do_incendio:
                #mostra apenas as 5 imagens antes do incêndio (NUMERO_DE_IMAGENS) definido no início
                _insere_varias_na_lista(imagens_antes_incendio[-NUMERO_DE_IMAGENS:])
                imagens_antes_incendio.clear()
                self.lista.insert(tk.END, 'Data do Incêndio ' + data_inicio.strftime("%d/%m/%Y"))
                self.lista.itemconfig(tk.END, fg="green")
                cont_imagem += 1
                antes_do_incendio = False
            # Se esta data é ainda antes do incendio, guardar a data para incluir na lista depois.
            if antes_do_incendio:
                imagens_antes_incendio.append((data, cont1))
                continue
            # se a data é após o incêndio, incluir na ListBox diretamente até ao máximo de imagens 5 datas depois do incêndio
            _insere_uma_na_lista(data, cont1)
            if cont_imagem >= 2 * NUMERO_DE_IMAGENS + 1:
                break
        # Se não existirem imagens disponiveis depois do incendio mostra a vermelho a mensagem "Sem imagens após data".
        if imagens_antes_incendio:
            _insere_varias_na_lista(imagens_antes_incendio)
            self.lista.insert(tk.END, f'Sem imagens após {data_inicio.strftime("%d/%m/%Y")}')
            self.lista.itemconfig(tk.END, bg="red")

    #Chama a função para obter as imagens disponiveis do sentinel2 60 dias antes e depois do incendio
    def obter_imagens(self, data_incendio, codigo):
        bbox=ler_envelope.envelope(codigo)
        print(bbox)
        data_inicio=(data_incendio - timedelta(days=60)).strftime("%Y%m%d")
        data_fim=(data_incendio + timedelta(days=60)).strftime("%Y%m%d")
        lista=import_img.lerimagens(bbox,data_inicio,data_fim, self.cobertura_maxima)
        return lista["features"]


#Chama o ficheiro"__main__" para executar a ferramenta
def main():
    MainApp()
    tk.mainloop()
    return


if __name__ == "__main__":
    main()

