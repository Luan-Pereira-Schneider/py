# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import platform
import subprocess
import json
from datetime import datetime, date # Importado date especificamente
from typing import List, Dict, Any, Optional, Tuple

# Verificação do ReportLab
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# --- TENTATIVA DE IMPORTAR PyMuPDF (fitz) ---
# Necessário para a funcionalidade de pré-visualização de PDF
# Instalar com: pip install pymupdf
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False


# --- Constantes ---
COR_PRIMARIA = "#1E3D59"
COR_SECUNDARIA = "#F5F0E1"
COR_DESTAQUE = "#FF6E40"
COR_TEXTO = "#2B2B2B"
COR_BORDA = "#D3D3D3"
FONTE_PADRAO = ('Segoe UI', 11)
FONTE_TITULO = ('Segoe UI', 18, 'bold')
FONTE_LABEL_ENTRADA = ('Segoe UI', 9, 'bold')
FONTE_RESULTADO = ('Segoe UI', 26, 'bold')
FONTE_CABECALHO_TABELA = ('Helvetica-Bold', 11) # Reduzi levemente para caber melhor
NOME_ARQUIVO_DADOS = "servicos_salvos.json"
NOME_DIRETORIO_DADOS = ".calculadora_imobiliaria"


class CalculadoraImobiliaria:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Calculadora Imobiliária")
        self.root.state('zoomed') # Inicia maximizado

        # --- Dados da Empresa (Configurável) ---
        self.nome_empresa = "Sua Imobiliária Aqui"
        self.telefone_empresa = "(XX) XXXX-XXXX"
        self.email_empresa = "contato@suaimobiliaria.com"
        self.endereco_empresa = "Seu Endereço Completo"

        # --- Estado da Aplicação ---
        self.entries: List[Dict[str, Any]] = []
        self.servicos_salvos: List[Dict[str, Any]] = []
        self.filtro_servicos_var = tk.StringVar()
        self.filtro_data_unica_var = tk.StringVar() # ADICIONADO

        # Estado da Aba de PDF
        self.pdf_preview_path = None
        self.pdf_preview_doc = None
        self.pdf_preview_page_num = 0
        self.pdf_preview_image_label = None # Label para exibir a imagem da página
        self.pdf_preview_canvas = None # Canvas para a imagem (caso precise de scroll)
        self.pdf_page_display = None # Referência para a imagem Tkinter

        self.carregar_servicos_salvos()
        self.configurar_estilo()
        self.criar_interface()
        self.atualizar_resultado() # Inicia loop de atualização

    def _obter_caminho_arquivo_dados(self) -> str:
        """Retorna o caminho completo para o arquivo de dados JSON."""
        diretorio_dados = os.path.join(os.path.expanduser("~"), NOME_DIRETORIO_DADOS)
        if not os.path.exists(diretorio_dados):
            try:
                os.makedirs(diretorio_dados)
            except OSError as e:
                messagebox.showerror("Erro de Permissão", f"Não foi possível criar o diretório de dados:\n{diretorio_dados}\nErro: {e}")
                # Retornar um caminho temporário ou lidar com o erro de outra forma
                return os.path.join(os.getcwd(), NOME_ARQUIVO_DADOS)
        return os.path.join(diretorio_dados, NOME_ARQUIVO_DADOS)

    def _formatar_moeda(self, valor: float) -> str:
        """Formata um valor float para o formato de moeda BRL."""
        try:
             # Garante que é float antes de formatar
             valor_float = float(valor)
             return f"R$ {valor_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except (ValueError, TypeError):
             return "R$ Erro" # Retorna um valor indicando erro se não for número

    # --- Configuração da UI ---
    def configurar_estilo(self):
        """Configura os estilos dos widgets ttk."""
        estilo = ttk.Style()
        estilo.theme_use('clam')

        # Estilos gerais
        estilo.configure('TFrame', background=COR_SECUNDARIA)
        estilo.configure('TLabel', background=COR_SECUNDARIA, foreground=COR_TEXTO, font=FONTE_PADRAO)
        estilo.configure('TNotebook', background=COR_SECUNDARIA)
        estilo.configure('TEntry', fieldbackground='white', foreground=COR_TEXTO, font=FONTE_PADRAO)
        estilo.configure('TCombobox', fieldbackground='white', background=COR_SECUNDARIA, foreground=COR_TEXTO, padding=(5, 3), font=FONTE_PADRAO)

        # Estilos específicos
        estilo.configure('Titulo.TLabel', background=COR_PRIMARIA, foreground='white', font=FONTE_TITULO, padding=10)
        estilo.configure('TNotebook.Tab', background=COR_PRIMARIA, foreground='white', padding=[15, 5], font=FONTE_PADRAO)
        estilo.map('TNotebook.Tab', background=[('selected', COR_DESTAQUE)], foreground=[('selected', 'white')])
        estilo.configure('TButton', background=COR_PRIMARIA, foreground='white', borderwidth=0, font=FONTE_PADRAO)
        estilo.map('TButton', background=[('active', COR_DESTAQUE)], foreground=[('active', 'white')])
        estilo.configure("Vertical.TScrollbar", background=COR_PRIMARIA, troughcolor=COR_SECUNDARIA, arrowcolor='white', borderwidth=0, arrowsize=16)
        estilo.map("Vertical.TScrollbar", background=[('active', COR_DESTAQUE), ('pressed', COR_DESTAQUE)])
        estilo.configure("Treeview", rowheight=25, fieldbackground=COR_SECUNDARIA, font=('Segoe UI', 10))
        estilo.configure("Treeview.Heading", font=('Segoe UI', 10, 'bold'), background=COR_PRIMARIA, foreground='white')
        estilo.map("Treeview.Heading", background=[('active', COR_DESTAQUE)])


    def criar_interface(self):
        """Cria a estrutura principal da interface."""
        self.frame_principal = ttk.Frame(self.root)
        self.frame_principal.pack(fill=tk.BOTH, expand=True)

        self.notebook = ttk.Notebook(self.frame_principal)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Aba 1: Calculadora
        self.tab_calculadora = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_calculadora, text=" Calculadora 🧮 ")

        # Aba 2: Serviços Salvos
        self.tab_servicos_salvos = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_servicos_salvos, text=" Serviços Salvos 💾 ")

        # --- INÍCIO: Adição da Nova Aba ---
        # Aba 3: Visualizar PDF
        self.tab_pdf_preview = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_pdf_preview, text=" Visualizar PDF 📄 ")
        # --- FIM: Adição da Nova Aba ---

        self._criar_aba_calculadora()
        self._criar_aba_servicos_salvos()
        self._criar_aba_pdf_preview() # Chama a função para criar o conteúdo da nova aba
        self._criar_rodape()

    def _criar_cabecalho(self, frame_pai: ttk.Frame, titulo: str, icone: str):
        """Cria um cabeçalho padronizado."""
        frame_cabecalho = ttk.Frame(frame_pai)
        frame_cabecalho.pack(fill=tk.X, pady=(0, 10))

        cabecalho_bg = tk.Frame(frame_cabecalho, bg=COR_PRIMARIA, height=60)
        cabecalho_bg.pack(fill=tk.X)
        cabecalho_bg.pack_propagate(False)

        lbl_titulo = ttk.Label(cabecalho_bg, text=titulo, style='Titulo.TLabel')
        lbl_titulo.pack(side=tk.LEFT, padx=20, pady=5)

        lbl_icone = tk.Label(cabecalho_bg, text=icone, bg=COR_PRIMARIA, fg="white", font=('Segoe UI Emoji', 24))
        lbl_icone.pack(side=tk.RIGHT, padx=20, pady=5)

    def _criar_rodape(self):
        """Cria o rodapé da aplicação."""
        self.frame_rodape = tk.Frame(self.frame_principal, bg=COR_PRIMARIA, height=30)
        self.frame_rodape.pack(fill=tk.X, side=tk.BOTTOM)
        self.frame_rodape.pack_propagate(False)

        center_frame = tk.Frame(self.frame_rodape, bg=COR_PRIMARIA)
        center_frame.pack(expand=True, fill=tk.BOTH)

        # Obtém o ano atual dinamicamente
        ano_atual = datetime.now().year
        self.lbl_copyright = tk.Label(center_frame,
                                     text=f"© {ano_atual} {self.nome_empresa}",
                                     bg=COR_PRIMARIA, fg=COR_SECUNDARIA, font=('Segoe UI', 9))
        self.lbl_copyright.pack()

    # --- Aba Calculadora ---
    def _criar_aba_calculadora(self):
        """Cria os widgets da aba Calculadora."""
        self._criar_cabecalho(self.tab_calculadora, "Calculadora de Serviços", "🏠")

        frame_conteudo = ttk.Frame(self.tab_calculadora)
        frame_conteudo.pack(fill=tk.BOTH, expand=True)

        # Painel Esquerdo (Entradas)
        frame_left = ttk.Frame(frame_conteudo)
        frame_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        self._criar_frame_entradas(frame_left)

        # Painel Direito (Resultado e Ações)
        frame_right = ttk.Frame(frame_conteudo, width=300) # Largura fixa para o painel direito
        frame_right.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        frame_right.pack_propagate(False) # Impede que o frame encolha
        self._criar_frame_resultado(frame_right)
        self._criar_frame_botoes_calculadora(frame_right)


    def _criar_frame_entradas(self, parent_frame: ttk.Frame):
        """Cria a seção de entradas de serviços na aba Calculadora."""
        ttk.Label(parent_frame, text="Serviços Imobiliários:", font=('Segoe UI', 12, 'bold')).pack(anchor=tk.W)
        ttk.Label(parent_frame, text="Adicione ou remova serviços e valores abaixo.", font=('Segoe UI', 10)).pack(anchor=tk.W, pady=(0, 10))

        # Área de Rolagem
        frame_scroll = ttk.Frame(parent_frame)
        frame_scroll.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(frame_scroll, bg=COR_SECUNDARIA, highlightthickness=1, highlightbackground=COR_BORDA)
        self.scrollbar = ttk.Scrollbar(frame_scroll, orient="vertical", command=self.canvas.yview, style="Vertical.TScrollbar")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.frame_interno = ttk.Frame(self.canvas) # Frame onde as entradas serão adicionadas
        self.canvas_window = self.canvas.create_window((0, 0), window=self.frame_interno, anchor='nw')

        # Bindings para scroll e resize
        self.frame_interno.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        # Bind para roda do mouse em diferentes plataformas
        if platform.system() == "Windows":
            self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        elif platform.system() == "Darwin": # macOS
            self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        else: # Linux
            self.canvas.bind_all("<Button-4>", self._on_mousewheel) # Rolar para cima
            self.canvas.bind_all("<Button-5>", self._on_mousewheel) # Rolar para baixo


        # Botão Adicionar
        self.botao_adicionar = ttk.Button(parent_frame, text="✚ Adicionar Serviço", command=self.adicionar_servico_ui, width=20)
        self.botao_adicionar.pack(anchor=tk.W, pady=(10, 0))

    def _criar_frame_resultado(self, parent_frame: ttk.Frame):
        """Cria a seção de exibição do resultado total."""
        frame_moldura = tk.Frame(parent_frame, bg=COR_PRIMARIA, bd=2, relief=tk.SUNKEN, padx=20, pady=20)
        frame_moldura.pack(pady=(0, 15), fill=tk.X) # Fill X para ocupar a largura do painel direito

        tk.Label(frame_moldura, text="VALOR TOTAL", bg=COR_PRIMARIA, fg=COR_SECUNDARIA, font=('Segoe UI', 14, 'bold')).pack()
        self.label_resultado = tk.Label(frame_moldura, text=self._formatar_moeda(0.0), bg=COR_PRIMARIA, fg="white", font=FONTE_RESULTADO)
        self.label_resultado.pack(pady=10)
        tk.Label(frame_moldura, text="💰", bg=COR_PRIMARIA, fg="white", font=('Segoe UI Emoji', 28)).pack(pady=(5, 0))


    def _criar_frame_botoes_calculadora(self, parent_frame: ttk.Frame):
        """Cria os botões de ação principais da Calculadora."""
        frame_botoes = ttk.Frame(parent_frame)
        frame_botoes.pack(pady=10, fill=tk.X) # Fill X

        btn_salvar = ttk.Button(frame_botoes, text="💾 Salvar Grupo Atual", command=self.salvar_servicos_atuais)
        btn_salvar.pack(pady=4, fill=tk.X, padx=5)

        btn_pdf = ttk.Button(frame_botoes, text="📄 Gerar PDF Atual", command=lambda: self.gerar_pdf()) # Chama sem argumento
        btn_pdf.pack(pady=4, fill=tk.X, padx=5)
        if not REPORTLAB_AVAILABLE:
            btn_pdf.config(state=tk.DISABLED, text="📄 Gerar PDF (ReportLab Ausente)")

        btn_limpar = ttk.Button(frame_botoes, text="🗑 Limpar Tudo", command=self.limpar_campos)
        btn_limpar.pack(pady=4, fill=tk.X, padx=5)

    # --- Aba Serviços Salvos ---
    def _criar_aba_servicos_salvos(self):
        """Cria os widgets da aba Serviços Salvos."""
        self._criar_cabecalho(self.tab_servicos_salvos, "Serviços Salvos", "📋")

        frame_conteudo_salvos = ttk.Frame(self.tab_servicos_salvos)
        frame_conteudo_salvos.pack(fill=tk.BOTH, expand=True)

        # Painel Esquerdo (Lista de Grupos e Filtro)
        frame_lista = ttk.Frame(frame_conteudo_salvos)
        frame_lista.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        self._criar_frame_lista_grupos(frame_lista) # Modificado para incluir filtros

        # Painel Direito (Detalhes do Grupo)
        self.frame_detalhes = ttk.Frame(frame_conteudo_salvos, relief=tk.GROOVE, borderwidth=1)
        self.frame_detalhes.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        self._criar_frame_detalhes_grupo(self.frame_detalhes)

        # Preencher a lista inicialmente
        self.atualizar_lista_servicos_salvos()

    def _criar_frame_lista_grupos(self, parent_frame: ttk.Frame):
        """Cria a seção da lista de grupos salvos e filtro."""
        # Frame para todos os filtros
        frame_filtros_geral = ttk.Frame(parent_frame)
        frame_filtros_geral.pack(fill=tk.X, pady=(0, 10))

        # Filtro por Nome
        frame_filtro_nome = ttk.Frame(frame_filtros_geral)
        frame_filtro_nome.pack(fill=tk.X)
        ttk.Label(frame_filtro_nome, text="Filtrar por nome:", font=('Segoe UI', 10), width=15).pack(side=tk.LEFT, padx=(0, 5)) # Largura fixa para alinhar
        entry_filtro = ttk.Entry(frame_filtro_nome, textvariable=self.filtro_servicos_var, font=('Segoe UI', 10))
        entry_filtro.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.filtro_servicos_var.trace_add("write", self._filtrar_servicos_salvos) # Filtrar ao digitar

        # --- INÍCIO DA MODIFICAÇÃO DO FILTRO DE DATA ---
        # Filtro por Data Única
        frame_filtro_data = ttk.Frame(frame_filtros_geral)
        frame_filtro_data.pack(fill=tk.X, pady=(5, 0))

        ttk.Label(frame_filtro_data, text="Filtrar por Data (DD/MM/AAAA):", font=('Segoe UI', 10)).pack(side=tk.LEFT, padx=(0, 5))
        entry_data_unica = ttk.Entry(frame_filtro_data, textvariable=self.filtro_data_unica_var, font=('Segoe UI', 10), width=15)
        entry_data_unica.pack(side=tk.LEFT, fill=tk.X, expand=True)
        # Atualize o trace para chamar a mesma função de filtro
        self.filtro_data_unica_var.trace_add("write", self._filtrar_servicos_salvos)
        # --- FIM DA MODIFICAÇÃO DO FILTRO DE DATA ---


        # Treeview para Grupos
        frame_lista_scroll = ttk.Frame(parent_frame)
        frame_lista_scroll.pack(fill=tk.BOTH, expand=True, pady=(5,0)) # Espaço acima da lista

        colunas = ('nome', 'data', 'valor', 'itens')
        self.tree_servicos = ttk.Treeview(frame_lista_scroll, columns=colunas,
                                         show='headings', selectmode='extended')

        self.tree_servicos.heading('nome', text='Nome do Grupo')
        self.tree_servicos.heading('data', text='Data')
        self.tree_servicos.heading('valor', text='Valor Total')
        self.tree_servicos.heading('itens', text='Itens')

        self.tree_servicos.column('nome', width=200, anchor=tk.W)
        self.tree_servicos.column('data', width=100, anchor=tk.CENTER)
        self.tree_servicos.column('valor', width=120, anchor=tk.E)
        self.tree_servicos.column('itens', width=60, anchor=tk.CENTER)

        # Scrollbar
        scrollbar_tree = ttk.Scrollbar(frame_lista_scroll, orient="vertical",
                                      command=self.tree_servicos.yview,
                                      style="Vertical.TScrollbar")
        self.tree_servicos.configure(yscrollcommand=scrollbar_tree.set)

        scrollbar_tree.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_servicos.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.tree_servicos.bind('<<TreeviewSelect>>', self.exibir_detalhes_grupo)

        # Botões de Ação da Lista
        frame_acoes = ttk.Frame(parent_frame)
        frame_acoes.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(frame_acoes, text="✏️ Editar", command=self.editar_grupo_selecionado, width=12).pack(side=tk.LEFT, padx=3)
        ttk.Button(frame_acoes, text="🗑️ Excluir", command=self.excluir_grupos_selecionados, width=12).pack(side=tk.LEFT, padx=3)
        ttk.Button(frame_acoes, text="📄 Gerar PDF", command=self.gerar_pdf_grupo_selecionado, width=14).pack(side=tk.LEFT, padx=3)
        ttk.Button(frame_acoes, text="📄 Gerar PDF Selecionados", command=self.gerar_pdf_grupos_selecionados, width=22).pack(side=tk.LEFT, padx=3)


    def _criar_frame_detalhes_grupo(self, parent_frame: ttk.Frame):
        """Cria a seção de detalhes do grupo selecionado."""
        self.lbl_titulo_detalhes = ttk.Label(parent_frame, text="Detalhes do Grupo", font=('Segoe UI', 12, 'bold'))
        self.lbl_titulo_detalhes.pack(anchor=tk.W, padx=10, pady=(10, 5))

        # Treeview para Detalhes
        frame_tabela_detalhes = ttk.Frame(parent_frame)
        frame_tabela_detalhes.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        colunas_detalhes = ('servico', 'locacao', 'descricao', 'valor')
        self.tree_detalhes = ttk.Treeview(frame_tabela_detalhes, columns=colunas_detalhes,
                                         show='headings')

        self.tree_detalhes.heading('servico', text='Serviço')
        self.tree_detalhes.heading('locacao', text='Locação')
        self.tree_detalhes.heading('descricao', text='Descrição')
        self.tree_detalhes.heading('valor', text='Valor')

        self.tree_detalhes.column('servico', width=100, anchor=tk.W)
        self.tree_detalhes.column('locacao', width=150, anchor=tk.W)
        self.tree_detalhes.column('descricao', width=200, anchor=tk.W)
        self.tree_detalhes.column('valor', width=100, anchor=tk.E)

        # Scrollbar
        scrollbar_detalhes = ttk.Scrollbar(frame_tabela_detalhes, orient="vertical",
                                           command=self.tree_detalhes.yview,
                                           style="Vertical.TScrollbar")
        self.tree_detalhes.configure(yscrollcommand=scrollbar_detalhes.set)

        scrollbar_detalhes.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_detalhes.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Botão Carregar na Calculadora
        self.btn_carregar_na_calculadora = ttk.Button(parent_frame,
                                                     text="📋 Carregar na Calculadora",
                                                     command=self.carregar_grupo_na_calculadora,
                                                     width=25)
        self.btn_carregar_na_calculadora.pack(pady=10)


    # --- INÍCIO: Criação da Aba de Visualização/Edição de PDF ---
    def _criar_aba_pdf_preview(self):
        """Cria os widgets da aba Visualizar PDF (Placeholders)."""
        self._criar_cabecalho(self.tab_pdf_preview, "Visualizador de PDF", "🔍")

        # Frame principal da aba
        frame_conteudo_pdf = ttk.Frame(self.tab_pdf_preview)
        frame_conteudo_pdf.pack(fill=tk.BOTH, expand=True)

        # --- Painel de Controle (Esquerda ou Topo) ---
        frame_controle_pdf = ttk.Frame(frame_conteudo_pdf, width=250) # Largura fixa para controles
        frame_controle_pdf.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10), pady=5)
        frame_controle_pdf.pack_propagate(False)

        ttk.Label(frame_controle_pdf, text="Controles do PDF", font=('Segoe UI', 11, 'bold')).pack(pady=(0, 10), anchor=tk.W)

        # Botão para carregar PDF
        btn_carregar = ttk.Button(frame_controle_pdf, text="📂 Carregar PDF...", command=self._carregar_pdf_para_preview)
        btn_carregar.pack(fill=tk.X, pady=4)

        # Aviso sobre PyMuPDF
        if not PYMUPDF_AVAILABLE:
            lbl_aviso = tk.Label(frame_controle_pdf,
                                 text="Pré-visualização requer PyMuPDF.\nInstale com: pip install pymupdf",
                                 font=('Segoe UI', 8), fg='red', bg=COR_SECUNDARIA, justify=tk.LEFT)
            lbl_aviso.pack(fill=tk.X, pady=5)
            # Desabilitar botões que dependem do PyMuPDF
            btn_carregar.config(state=tk.DISABLED)


        # Placeholder para informações do arquivo
        self.lbl_pdf_info = ttk.Label(frame_controle_pdf, text="Nenhum PDF carregado.", wraplength=230, justify=tk.LEFT)
        self.lbl_pdf_info.pack(pady=10, anchor=tk.W)

        # Placeholder para controles de página (dependem de PyMuPDF)
        frame_paginacao = ttk.Frame(frame_controle_pdf)
        frame_paginacao.pack(fill=tk.X, pady=5)

        self.btn_prev_page = ttk.Button(frame_paginacao, text="◀ Anterior", command=self._pagina_anterior_pdf, state=tk.DISABLED)
        self.btn_prev_page.pack(side=tk.LEFT, expand=True, padx=2)

        self.lbl_page_num = ttk.Label(frame_paginacao, text="Página: - / -")
        self.lbl_page_num.pack(side=tk.LEFT, padx=5)

        self.btn_next_page = ttk.Button(frame_paginacao, text="Próxima ▶", command=self._proxima_pagina_pdf, state=tk.DISABLED)
        self.btn_next_page.pack(side=tk.LEFT, expand=True, padx=2)

        ttk.Separator(frame_controle_pdf, orient='horizontal').pack(fill='x', pady=15)

        ttk.Label(frame_controle_pdf, text="Edição (Placeholder)", font=('Segoe UI', 11, 'bold')).pack(pady=(0, 10), anchor=tk.W)

        # Botão placeholder para "Editar Dados"
        btn_editar_dados = ttk.Button(frame_controle_pdf, text="✏️ Editar Dados Originais", command=self._editar_dados_pdf_placeholder)
        btn_editar_dados.pack(fill=tk.X, pady=4)

        # Explicação sobre a edição
        lbl_edit_info = tk.Label(frame_controle_pdf,
                                 text="Nota: A edição direta de PDF é complexa. "
                                      "Este botão poderia carregar os dados originais "
                                      "na aba Calculadora para modificação e "
                                      "regeneração do PDF.",
                                 font=('Segoe UI', 8), wraplength=230, justify=tk.LEFT, bg=COR_SECUNDARIA)
        lbl_edit_info.pack(fill=tk.X, pady=5)

        # --- Painel de Visualização (Direita) ---
        frame_visualizacao = ttk.Frame(frame_conteudo_pdf, relief=tk.SUNKEN, borderwidth=1)
        frame_visualizacao.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Canvas para exibir a imagem da página do PDF (permitirá scroll no futuro, se necessário)
        self.pdf_preview_canvas = tk.Canvas(frame_visualizacao, bg="gray", bd=0, highlightthickness=0)
        self.pdf_preview_canvas.pack(fill=tk.BOTH, expand=True)

        # Adicionar um Label dentro do Canvas para conter a imagem
        # O tamanho inicial é irrelevante, será ajustado ao carregar a imagem
        self.pdf_preview_image_label = ttk.Label(self.pdf_preview_canvas, text="Área de Pré-visualização do PDF", background='lightgrey')
        self.pdf_preview_canvas.create_window(0, 0, window=self.pdf_preview_image_label, anchor='nw')

        # Se precisar de scrollbars no canvas (para zoom, por exemplo):
        # vsb = ttk.Scrollbar(frame_visualizacao, orient="vertical", command=self.pdf_preview_canvas.yview)
        # hsb = ttk.Scrollbar(frame_visualizacao, orient="horizontal", command=self.pdf_preview_canvas.xview)
        # self.pdf_preview_canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        # vsb.pack(side="right", fill="y")
        # hsb.pack(side="bottom", fill="x")
        # self.pdf_preview_canvas.bind("<Configure>", self._configurar_scroll_pdf) # Função para configurar scrollregion

        # Mensagem inicial se PyMuPDF não estiver disponível
        if not PYMUPDF_AVAILABLE:
             self.pdf_preview_image_label.config(text="Pré-visualização indisponível.\nInstale PyMuPDF (fitz).", font=('Segoe UI', 12, 'bold'), foreground='darkred')

    def _configurar_scroll_pdf(self, event=None):
         """Atualiza a região de scroll do canvas de PDF."""
         # Necessário se usar scrollbars
         self.pdf_preview_canvas.configure(scrollregion=self.pdf_preview_canvas.bbox("all"))

    def _carregar_pdf_para_preview(self):
        """Abre diálogo para selecionar um PDF e tenta carregá-lo para preview."""
        if not PYMUPDF_AVAILABLE:
            messagebox.showerror("Dependência Ausente", "PyMuPDF (fitz) é necessário para visualizar PDFs.", parent=self.root)
            return

        file_path = filedialog.askopenfilename(
            title="Selecionar PDF para Visualizar",
            filetypes=[("Arquivos PDF", "*.pdf"), ("Todos os arquivos", "*.*")],
            parent=self.root
        )

        if not file_path:
            return # Usuário cancelou

        try:
            # Fechar documento anterior, se houver
            if self.pdf_preview_doc:
                self.pdf_preview_doc.close()

            self.pdf_preview_doc = fitz.open(file_path)
            self.pdf_preview_path = file_path
            self.pdf_preview_page_num = 0 # Começa na primeira página

            # Atualizar informações
            num_pages = len(self.pdf_preview_doc)
            filename = os.path.basename(file_path)
            self.lbl_pdf_info.config(text=f"Arquivo: {filename}\nPáginas: {num_pages}")

            # Habilitar/desabilitar botões de paginação
            self.btn_prev_page.config(state=tk.DISABLED)
            self.btn_next_page.config(state=tk.NORMAL if num_pages > 1 else tk.DISABLED)

            # Exibir a primeira página
            self._exibir_pagina_pdf()

        except Exception as e:
            messagebox.showerror("Erro ao Abrir PDF", f"Não foi possível carregar ou processar o arquivo PDF:\n{file_path}\n\nErro: {e}", parent=self.root)
            # Limpar estado
            if self.pdf_preview_doc:
                self.pdf_preview_doc.close()
            self.pdf_preview_doc = None
            self.pdf_preview_path = None
            self.pdf_preview_page_num = 0
            self.lbl_pdf_info.config(text="Falha ao carregar PDF.")
            self.lbl_page_num.config(text="Página: - / -")
            self.pdf_preview_image_label.config(image='', text='Falha ao carregar PDF.') # Limpa imagem
            self.btn_prev_page.config(state=tk.DISABLED)
            self.btn_next_page.config(state=tk.DISABLED)


    def _exibir_pagina_pdf(self):
        """Renderiza e exibe a página atual do PDF."""
        if not self.pdf_preview_doc or not PYMUPDF_AVAILABLE:
            return

        try:
            page = self.pdf_preview_doc.load_page(self.pdf_preview_page_num)

            # Definir zoom (ajustar conforme necessário, afeta qualidade e tamanho)
            zoom_matrix = fitz.Matrix(1.5, 1.5) # Exemplo: Zoom de 150%

            # Renderizar página como imagem (pixmap)
            pix = page.get_pixmap(matrix=zoom_matrix, alpha=False)

            # Converter para formato que Tkinter entende (PNG)
            img_data = pix.tobytes("ppm") # Usar PPM que tk.PhotoImage suporta nativamente

            # Criar PhotoImage e manter referência
            self.pdf_page_display = tk.PhotoImage(data=img_data)

            # Exibir a imagem no Label dentro do Canvas
            self.pdf_preview_image_label.config(image=self.pdf_page_display, text="") # Exibe imagem
            # Ajustar o tamanho do Label para o tamanho da imagem
            self.pdf_preview_image_label.config(width=self.pdf_page_display.width(), height=self.pdf_page_display.height())


            # Atualizar label do número da página
            num_pages = len(self.pdf_preview_doc)
            self.lbl_page_num.config(text=f"Página: {self.pdf_preview_page_num + 1} / {num_pages}")

            # Habilitar/desabilitar botões de paginação
            self.btn_prev_page.config(state=tk.NORMAL if self.pdf_preview_page_num > 0 else tk.DISABLED)
            self.btn_next_page.config(state=tk.NORMAL if self.pdf_preview_page_num < num_pages - 1 else tk.DISABLED)

            # Atualizar scroll region se estiver usando scrollbars
            self.root.after_idle(self._configurar_scroll_pdf)


        except Exception as e:
            messagebox.showerror("Erro ao Renderizar Página", f"Não foi possível renderizar a página {self.pdf_preview_page_num + 1}.\n\nErro: {e}", parent=self.root)
            self.pdf_preview_image_label.config(image='', text=f"Erro na pág. {self.pdf_preview_page_num + 1}") # Limpa imagem


    def _pagina_anterior_pdf(self):
        """Vai para a página anterior do PDF."""
        if self.pdf_preview_doc and self.pdf_preview_page_num > 0:
            self.pdf_preview_page_num -= 1
            self._exibir_pagina_pdf()

    def _proxima_pagina_pdf(self):
        """Vai para a próxima página do PDF."""
        if self.pdf_preview_doc and self.pdf_preview_page_num < len(self.pdf_preview_doc) - 1:
            self.pdf_preview_page_num += 1
            self._exibir_pagina_pdf()

    def _editar_dados_pdf_placeholder(self):
        """Função placeholder para a ação de editar dados do PDF."""
        if not self.pdf_preview_path:
             messagebox.showinfo("Nenhum PDF Carregado", "Carregue um arquivo PDF primeiro.", parent=self.root)
             return

        # --- Lógica Placeholder ---
        # Idealmente, aqui você tentaria encontrar os dados originais que geraram
        # este PDF (talvez buscando um grupo salvo com nome similar ou metadados no PDF).
        # Se encontrados, carregaria na aba Calculadora.

        messagebox.showinfo("Funcionalidade Placeholder",
                            "Esta é uma função placeholder.\n\n"
                            "A edição direta do PDF não está implementada devido à sua complexidade.\n\n"
                            "Para editar, idealmente, carregue os dados originais na aba 'Calculadora', "
                            "faça as alterações e gere um novo PDF.",
                            parent=self.root)

        # Exemplo de como poderia tentar carregar um grupo relacionado (requer lógica adicional)
        # nome_arquivo = os.path.basename(self.pdf_preview_path)
        # nome_grupo_potencial = nome_arquivo.replace("Orcamento_", "").replace(".pdf", "").replace("_", " ")
        # # ... (lógica para encontrar o grupo 'nome_grupo_potencial' em self.servicos_salvos) ...
        # # ... (se encontrar, chamar self.carregar_grupo_na_calculadora(indice_do_grupo)) ...

    # --- FIM: Criação da Aba de Visualização/Edição de PDF ---


    # --- Lógica de Negócio e Eventos ---

    def adicionar_servico_ui(self):
        """Adiciona uma nova linha de entrada de serviço na UI."""
        frame_entrada = ttk.Frame(self.frame_interno, padding=(5, 2))
        frame_entrada.pack(fill=tk.X, padx=5, pady=(0, 4))
        frame_entrada.columnconfigure(1, weight=1) # Faz a coluna 'Locação' expandir

        # Estilos para tk.Entry (ttk não tem highlight nativo fácil)
        entrada_estilo_tk = {
            'borderwidth': 1, 'relief': tk.SOLID, 'bg': 'white',
            'fg': COR_TEXTO, 'font': ('Segoe UI', 10),
            'highlightthickness': 1, 'highlightbackground': COR_BORDA,
            'highlightcolor': COR_DESTAQUE, 'insertbackground': COR_TEXTO
        }

        # --- Linha 1: Serviço, Locação, Valor ---
        ttk.Label(frame_entrada, text="Serviço:", font=FONTE_LABEL_ENTRADA).grid(row=0, column=0, padx=(0, 5), pady=(1,0), sticky=tk.W)
        tipos_servico = ['Venda', 'Aluguel', 'Avaliação', 'Consultoria', 'Reforma', 'Documentação', 'Outro']
        combo_servico = ttk.Combobox(frame_entrada, values=tipos_servico, width=18, state="readonly", font=('Segoe UI', 10))
        combo_servico.current(0)
        combo_servico.grid(row=1, column=0, padx=(0, 10), pady=(0,1), sticky=tk.EW)

        ttk.Label(frame_entrada, text="Locação:", font=FONTE_LABEL_ENTRADA).grid(row=0, column=1, padx=(0, 5), pady=(1,0), sticky=tk.W)
        entry_locacao = tk.Entry(frame_entrada, **entrada_estilo_tk)
        entry_locacao.grid(row=1, column=1, padx=(0, 10), pady=(0,1), sticky=tk.EW)

        ttk.Label(frame_entrada, text="Valor (R$):", font=FONTE_LABEL_ENTRADA).grid(row=0, column=2, padx=(0, 5), pady=(1,0), sticky=tk.W)
        novo_entry_valor = tk.Entry(frame_entrada, justify=tk.RIGHT, width=15, **entrada_estilo_tk)
        novo_entry_valor.grid(row=1, column=2, padx=(0, 10), pady=(0,1), sticky=tk.EW)

        # --- Linha 2: Descrição ---
        ttk.Label(frame_entrada, text="Descrição:", font=FONTE_LABEL_ENTRADA).grid(row=2, column=0, columnspan=2, padx=(0, 5), pady=(5,0), sticky=tk.W)
        entry_descricao = tk.Entry(frame_entrada, **entrada_estilo_tk)
        entry_descricao.grid(row=3, column=0, columnspan=3, padx=(0, 10), pady=(0,1), sticky=tk.EW) # Colspan 3

        # --- Botão Remover ---
        btn_remover = tk.Button(frame_entrada, text="✕",
                               command=lambda f=frame_entrada: self.remover_servico_ui(f),
                               bg=COR_DESTAQUE, fg='white', font=('Segoe UI', 10, 'bold'),
                               relief=tk.RAISED, borderwidth=1, width=3, height=2, cursor="hand2")
        btn_remover.grid(row=0, column=3, rowspan=4, padx=(5, 0), pady=(1,1), sticky='ns') # Ocupa 4 linhas

        # Separador visual
        ttk.Separator(frame_entrada, orient='horizontal').grid(row=4, column=0, columnspan=4, sticky='ew', pady=(8, 0))

        # Armazenar referência aos widgets
        entrada_info = {
            'frame': frame_entrada,
            'valor': novo_entry_valor,
            'servico': combo_servico,
            'locacao': entry_locacao,
            'descricao': entry_descricao
        }
        self.entries.append(entrada_info)

        entry_locacao.focus_set() # Foca no campo Locação
        self.root.update_idletasks() # Garante que o canvas atualize seu tamanho
        self.canvas.yview_moveto(1.0) # Rola para o final

    def remover_servico_ui(self, frame_a_remover: ttk.Frame):
        """Remove uma linha de entrada de serviço da UI."""
        entrada_para_remover = None
        for i, entrada_info in enumerate(self.entries):
            if entrada_info['frame'] == frame_a_remover:
                entrada_para_remover = self.entries.pop(i)
                break
        if entrada_para_remover:
            frame_a_remover.destroy()
            self.root.update_idletasks() # Necessário antes de reconfigurar o scroll
            self._on_frame_configure() # Atualiza a região de rolagem

    def atualizar_resultado(self):
        """Calcula o total dos serviços e atualiza o label de resultado. Chamado periodicamente."""
        total = 0.0
        try:
            for entrada_info in self.entries:
                valor_entry = entrada_info['valor']
                valor_text = valor_entry.get().strip()
                # Resetar borda
                valor_entry.config(highlightbackground=COR_BORDA, highlightcolor=COR_DESTAQUE)

                if valor_text:
                    try:
                        # Limpeza mais robusta do valor
                        valor_limpo = ''.join(filter(lambda c: c.isdigit() or c == ',', valor_text))
                        valor_limpo = valor_limpo.replace(",", ".")
                        if not valor_limpo: valor_limpo = '0'
                        total += float(valor_limpo)
                    except ValueError:
                        valor_entry.config(highlightbackground='red', highlightcolor='red') # Destaca erro

            self.label_resultado.config(text=self._formatar_moeda(total))
        except Exception as e:
            print(f"Erro ao atualizar resultado: {e}") # Log para debug
            self.label_resultado.config(text="Erro")

        # Reagendar a atualização
        self.root.after(250, self.atualizar_resultado)

    def limpar_campos(self):
        """Remove todas as entradas de serviço da calculadora."""
        if not self.entries:
            return

        if messagebox.askyesno("Confirmar Limpeza", "Deseja realmente limpar todos os campos da calculadora?"):
            # Itera sobre uma cópia da lista para poder remover enquanto itera
            for entrada_info in list(self.entries):
                self.remover_servico_ui(entrada_info['frame'])
            # Garante que a lista esteja vazia
            self.entries.clear()
            self._on_frame_configure() # Atualiza scroll

    def _get_dados_calculadora_atual(self) -> Optional[Tuple[List[Dict[str, Any]], float]]:
        """Pega e valida os dados das entradas atuais da calculadora."""
        dados_servicos = []
        total = 0.0
        erro = False
        for i, entrada_info in enumerate(self.entries):
            valor_entry = entrada_info['valor']
            servico = entrada_info['servico'].get()
            locacao = entrada_info['locacao'].get().strip()
            descricao = entrada_info['descricao'].get().strip()
            valor_text = valor_entry.get().strip()

            valor_entry.config(highlightbackground=COR_BORDA, highlightcolor=COR_DESTAQUE) # Reseta borda

            # Considera linha vazia se nenhum campo essencial estiver preenchido
            if not (servico or locacao or descricao or valor_text):
                 continue

            valor = 0.0
            if valor_text:
                try:
                    valor_limpo = ''.join(filter(lambda c: c.isdigit() or c == ',', valor_text)).replace(",", ".")
                    if not valor_limpo: valor_limpo = '0' # Considera vazio como 0
                    valor = float(valor_limpo)
                except ValueError:
                    valor_entry.config(highlightbackground='red', highlightcolor='red')
                    messagebox.showerror("Erro de Valor", f"Valor inválido na linha {i+1} ('{valor_text}')")
                    valor_entry.focus_set()
                    erro = True
                    break # Para na primeira linha com erro
            # Se valor_text for vazio, valor continua 0.0

            dados_servicos.append({
                'servico': servico,
                'locacao': locacao,
                'descricao': descricao,
                'valor': valor # Salva como float
            })
            total += valor

        if erro:
            return None
        return dados_servicos, total

    def salvar_servicos_atuais(self):
        """Salva os serviços atualmente na calculadora como um novo grupo."""
        resultado = self._get_dados_calculadora_atual()
        if resultado is None: # Erro de validação ocorreu
            return
        dados_servicos, total = resultado

        if not dados_servicos:
            messagebox.showinfo("Sem Dados", "Não há serviços preenchidos para salvar.")
            return

        # --- Janela para nome do grupo ---
        dialogo = tk.Toplevel(self.root)
        dialogo.title("Salvar Grupo de Serviços")
        dialogo.geometry("400x150")
        dialogo.resizable(False, False)
        dialogo.transient(self.root) # Mantém sobre a janela principal
        dialogo.grab_set() # Bloqueia interação com a janela principal

        # Centralizar diálogo
        dialogo.update_idletasks()
        w_root, h_root = self.root.winfo_width(), self.root.winfo_height()
        x_root, y_root = self.root.winfo_x(), self.root.winfo_y()
        w_dialog, h_dialog = dialogo.winfo_width(), dialogo.winfo_height()
        x_dialog = x_root + (w_root - w_dialog) // 2
        y_dialog = y_root + (h_root - h_dialog) // 2
        dialogo.geometry(f"+{x_dialog}+{y_dialog}")

        frame = ttk.Frame(dialogo, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Nome do Grupo:", font=FONTE_PADRAO).pack(anchor=tk.W, pady=(0, 5))
        nome_var = tk.StringVar()
        entry_nome = ttk.Entry(frame, textvariable=nome_var, font=FONTE_PADRAO, width=35)
        entry_nome.pack(fill=tk.X, pady=(0, 15))
        entry_nome.focus_set()

        frame_botoes = ttk.Frame(frame)
        frame_botoes.pack(fill=tk.X)

        btn_cancelar = ttk.Button(frame_botoes, text="Cancelar", command=dialogo.destroy, width=10)
        btn_cancelar.pack(side=tk.RIGHT, padx=5)

        def confirmar_salvar():
            nome_grupo = nome_var.get().strip()
            if not nome_grupo:
                messagebox.showwarning("Nome Inválido", "Por favor, digite um nome para o grupo.", parent=dialogo)
                entry_nome.focus_set()
                return

            grupo_existente = None
            indice_existente = -1
            for i, g in enumerate(self.servicos_salvos):
                if g['nome'].lower() == nome_grupo.lower():
                    grupo_existente = g
                    indice_existente = i
                    break

            if grupo_existente:
                 if not messagebox.askyesno("Nome Duplicado", f"Já existe um grupo chamado '{nome_grupo}'.\nDeseja sobrescrevê-lo?", parent=dialogo):
                      entry_nome.focus_set()
                      return
                 else:
                    # Remove o grupo existente antes de adicionar o novo (usando o índice encontrado)
                    if indice_existente != -1:
                        del self.servicos_salvos[indice_existente]

            grupo = {
                'nome': nome_grupo,
                'data': datetime.now().strftime("%d/%m/%Y"),
                'total': total,
                'itens': dados_servicos
            }

            self.servicos_salvos.append(grupo)
            # Ordena alfabeticamente (opcional, mas bom para consistência)
            self.servicos_salvos.sort(key=lambda g: g['nome'].lower())

            if self.salvar_servicos_no_arquivo():
                # Atualiza a lista, limpando filtros para mostrar o novo item
                self.filtro_servicos_var.set("")
                self.filtro_data_unica_var.set("") # LIMPA O NOVO CAMPO
                self.atualizar_lista_servicos_salvos() # ATUALIZA A LISTA (JÁ LÊ OS FILTROS VAZIOS)
                dialogo.destroy()
                messagebox.showinfo("Sucesso", f"Grupo '{nome_grupo}' salvo com sucesso!")
            # else: erro já foi mostrado em salvar_servicos_no_arquivo

        btn_salvar_conf = ttk.Button(frame_botoes, text="Salvar", command=confirmar_salvar, width=10)
        btn_salvar_conf.pack(side=tk.RIGHT, padx=5)

        entry_nome.bind("<Return>", lambda event: confirmar_salvar()) # Enter para salvar
        dialogo.bind("<Escape>", lambda event: dialogo.destroy()) # ESC para cancelar

        dialogo.wait_window()

    def salvar_servicos_no_arquivo(self) -> bool:
        """Salva a lista completa de serviços salvos no arquivo JSON."""
        arquivo_dados = self._obter_caminho_arquivo_dados()
        try:
            # Cria backup antes de salvar
            if os.path.exists(arquivo_dados):
                try:
                    backup_path = arquivo_dados + ".bak"
                    import shutil
                    shutil.copy2(arquivo_dados, backup_path)
                except Exception as backup_err:
                     print(f"Aviso: Falha ao criar backup de {arquivo_dados}: {backup_err}")

            with open(arquivo_dados, 'w', encoding='utf-8') as f:
                json.dump(self.servicos_salvos, f, ensure_ascii=False, indent=4) # indent=4 para legibilidade
            return True
        except Exception as e:
            messagebox.showerror("Erro ao Salvar Arquivo", f"Não foi possível salvar os dados em:\n{arquivo_dados}\nErro: {str(e)}")
            return False

    def carregar_servicos_salvos(self):
        """Carrega os serviços salvos do arquivo JSON ao iniciar."""
        arquivo_dados = self._obter_caminho_arquivo_dados()
        if not os.path.exists(arquivo_dados):
            self.servicos_salvos = []
            return

        try:
            with open(arquivo_dados, 'r', encoding='utf-8') as f:
                self.servicos_salvos = json.load(f)
                # Validação básica
                if not isinstance(self.servicos_salvos, list):
                    print("Arquivo de dados corrompido (não é uma lista). Iniciando com lista vazia.")
                    self.servicos_salvos = []
                else:
                    # Validar estrutura interna (opcional, mas recomendado)
                    for i, grupo in enumerate(self.servicos_salvos):
                         if not isinstance(grupo, dict) or 'nome' not in grupo or 'itens' not in grupo:
                              print(f"Aviso: Grupo inválido encontrado no índice {i}. Removendo.")
                              # Poderia remover o item inválido aqui
                              pass # Por enquanto só avisa
                # Ordenar ao carregar (opcional, mas garante consistência)
                self.servicos_salvos.sort(key=lambda g: g.get('nome', '').lower())
        except json.JSONDecodeError:
             messagebox.showerror("Erro ao Carregar", f"Arquivo de dados '{NOME_ARQUIVO_DADOS}' parece estar corrompido.\nVerifique o arquivo ou restaure um backup (.bak, se existir).\nSerá iniciado com uma lista vazia.")
             self.servicos_salvos = []
        except Exception as e:
            messagebox.showerror("Erro ao Carregar Arquivo", f"Não foi possível carregar os dados de:\n{arquivo_dados}\nErro: {str(e)}")
            self.servicos_salvos = [] # Inicia vazio em caso de erro grave

    # --- Funções de Filtragem e Atualização da Lista (MODIFICADAS) ---

    def _filtrar_servicos_salvos(self, *args):
        """Filtra a TreeView de serviços salvos com base nos filtros."""
        filtro_nome = self.filtro_servicos_var.get().lower()
        # --- INÍCIO DA MODIFICAÇÃO ---
        # Obtenha a data única do novo campo
        filtro_data_unica_str = self.filtro_data_unica_var.get()

        # Tenta converter a data única
        data_filtro = self._get_date_from_string(filtro_data_unica_str)

        # Adicionar feedback visual de data inválida (ex: borda vermelha) - Fica como sugestão
        # entry_data_unica = self.root.nametowidget(...) # precisaria guardar a ref do entry
        # if filtro_data_unica_str and data_filtro is None:
        #     entry_data_unica.config(...) # Borda vermelha
        # else:
        #     entry_data_unica.config(...) # Borda normal

        # Chame a atualização passando a data única (ou None se inválida/vazia)
        self.atualizar_lista_servicos_salvos(filtro_nome, data_filtro)
        # --- FIM DA MODIFICAÇÃO ---

    # --- MODIFICADA A ASSINATURA E LÓGICA DE DATA ---
    def atualizar_lista_servicos_salvos(self, filtro_nome: str = "",
                                     filtro_data_unica: Optional[date] = None): # Renomeado e tipo Date
        """Atualiza a TreeView de serviços salvos, aplicando filtros."""
        # Limpa a árvore
        for item in self.tree_servicos.get_children():
            self.tree_servicos.delete(item)

        # Limpa detalhes também
        for item in self.tree_detalhes.get_children():
            self.tree_detalhes.delete(item)
        self.lbl_titulo_detalhes.config(text="Detalhes do Grupo")


        # Adiciona itens filtrados
        for i, grupo in enumerate(self.servicos_salvos):
            # Validar se o grupo é um dicionário antes de tentar acessar
            if not isinstance(grupo, dict):
                print(f"Aviso: Item inválido na lista self.servicos_salvos no índice {i}. Pulando.")
                continue

            nome = grupo.get('nome', 'Sem Nome')
            data_str = grupo.get('data', '??/??/????')

            # 1. Filtrar por nome
            if filtro_nome and filtro_nome not in nome.lower():
                continue # Pula se não corresponder ao filtro de nome

            # 2. Filtrar por data única (LÓGICA MODIFICADA)
            data_grupo = self._get_date_from_string(data_str)
            if filtro_data_unica: # Se uma data de filtro foi fornecida e é válida
                if not data_grupo: # Se o grupo não tem data válida, não pode corresponder
                    print(f"Aviso: Grupo '{nome}' tem data inválida ('{data_str}') e foi pulado pelo filtro de data.")
                    continue
                # Compara se a data do grupo é DIFERENTE da data do filtro
                if data_grupo != filtro_data_unica:
                    continue # Pula se não for exatamente o dia do filtro
            # Se filtro_data_unica for None (campo vazio ou inválido), não filtra por data

            # Se passou pelos filtros, adiciona na Treeview
            total = grupo.get('total', 0.0)
            num_itens = len(grupo.get('itens', []))
            valor_formatado = self._formatar_moeda(total)

            # Usa um IID prefixado com o índice ORIGINAL para recuperação posterior
            iid_grupo = f"grupo_{i}"
            self.tree_servicos.insert('', 'end', iid=iid_grupo, values=(nome, data_str, valor_formatado, num_itens))


    # --- Funções de Ação para Serviços Salvos (com ajuste para IID) ---

    def _get_index_from_iid(self, iid_str: str) -> Optional[int]:
        """Extrai o índice original da lista a partir do IID da Treeview."""
        if isinstance(iid_str, str) and iid_str.startswith("grupo_"):
            try:
                index = int(iid_str.split('_')[1])
                # Validação extra: Verifica se o índice ainda é válido na lista atual
                if 0 <= index < len(self.servicos_salvos):
                     # Verifica se o item no índice corresponde minimamente (opcional, mas bom)
                     # if self.servicos_salvos[index].get('nome') == self.tree_servicos.item(iid_str, 'values')[0]:
                     return index
                     # else:
                     #     print(f"Aviso: Inconsistência entre IID {iid_str} (índice {index}) e dados atuais.")
                     #     return None
                else:
                     # O índice está fora dos limites. A lista pode ter mudado (excluído item?)
                     # Não deve acontecer se a atualização da treeview for feita corretamente.
                     print(f"Aviso: Índice {index} do IID '{iid_str}' está fora dos limites da lista atual ({len(self.servicos_salvos)} itens).")
                     return None
            except (ValueError, IndexError, TypeError):
                print(f"Erro ao extrair índice do IID: {iid_str}")
                return None
        # print(f"Formato de IID inválido ou tipo incorreto: {iid_str} (Tipo: {type(iid_str)})")
        return None

    def exibir_detalhes_grupo(self, event=None):
        """Exibe os detalhes do primeiro grupo selecionado na TreeView."""
        selection = self.tree_servicos.selection()

        # Limpa detalhes anteriores
        for item in self.tree_detalhes.get_children():
            self.tree_detalhes.delete(item)

        if not selection:
            self.lbl_titulo_detalhes.config(text="Detalhes do Grupo")
            return

        primeiro_item_id_str = selection[0]
        index = self._get_index_from_iid(primeiro_item_id_str)

        if index is not None:
            try:
                grupo = self.servicos_salvos[index]
                # Verifica se grupo é um dicionário
                if not isinstance(grupo, dict):
                     raise TypeError(f"Item no índice {index} não é um dicionário.")

                nome = grupo.get('nome', 'Sem Nome')
                self.lbl_titulo_detalhes.config(text=f"Detalhes: {nome}")

                itens_grupo = grupo.get('itens', [])
                if not isinstance(itens_grupo, list): # Valida se 'itens' é lista
                     print(f"Aviso: 'itens' no grupo '{nome}' não é uma lista. Detalhes podem estar incompletos.")
                     itens_grupo = []

                for item in itens_grupo:
                    # Valida se cada item é um dicionário
                    if not isinstance(item, dict):
                         print(f"Aviso: Item inválido encontrado nos detalhes do grupo '{nome}'. Pulando.")
                         continue

                    servico = item.get('servico', '')
                    locacao = item.get('locacao', '')
                    descricao = item.get('descricao', '')
                    valor = item.get('valor', 0.0)
                    valor_formatado = self._formatar_moeda(valor)
                    self.tree_detalhes.insert('', 'end', values=(servico, locacao, descricao, valor_formatado))
            except (IndexError, TypeError, Exception) as e: # Captura erro de índice, tipo ou outro inesperado
                print(f"Erro ao acessar/processar dados do grupo no índice {index}: {e}")
                self.lbl_titulo_detalhes.config(text="Erro ao carregar detalhes")
                messagebox.showerror("Erro Detalhes", f"Não foi possível exibir os detalhes do grupo selecionado.\nErro: {e}", parent=self.root)
        else:
             # Se _get_index_from_iid retornou None, o IID era inválido ou o índice não existe mais
             self.lbl_titulo_detalhes.config(text="Erro ao encontrar grupo")


    def carregar_grupo_na_calculadora(self):
        """Carrega o primeiro grupo selecionado na aba da calculadora."""
        selection = self.tree_servicos.selection()
        if not selection:
            messagebox.showinfo("Nenhum Grupo Selecionado", "Selecione um grupo na lista para carregar.", parent=self.root)
            return
        if len(selection) > 1:
             messagebox.showwarning("Múltiplos Grupos", "Apenas o primeiro grupo selecionado será carregado na calculadora.", parent=self.root)

        primeiro_item_id_str = selection[0]
        index = self._get_index_from_iid(primeiro_item_id_str)

        if index is None:
            messagebox.showerror("Erro ao Carregar", "Não foi possível encontrar o grupo selecionado (índice inválido ou inconsistente).", parent=self.root)
            return

        try:
            grupo = self.servicos_salvos[index]
            # Validações básicas
            if not isinstance(grupo, dict): raise TypeError("Formato de grupo inválido.")
            nome_grupo = grupo.get('nome', 'Sem Nome')
            itens_grupo = grupo.get('itens', [])
            if not isinstance(itens_grupo, list): raise TypeError("Formato de itens inválido.")


            if self.entries: # Verifica se há algo na calculadora
                if not messagebox.askyesno("Confirmar Carregamento",
                                         f"Isto substituirá os dados atuais na calculadora pelo grupo '{nome_grupo}'.\nContinuar?",
                                         parent=self.root):
                    return

            # Limpa campos atuais SOMENTE se o usuário confirmar ou se estiver vazio
            while self.entries: # Limpa a lista e a UI
                self.remover_servico_ui(self.entries[0]['frame'])

            # Adiciona itens do grupo à calculadora
            for item_dict in itens_grupo:
                # Valida cada item antes de usar
                if not isinstance(item_dict, dict):
                     print(f"Aviso: Item inválido no grupo '{nome_grupo}' ignorado durante o carregamento.")
                     continue

                self.adicionar_servico_ui() # Cria a linha na UI
                entry_info = self.entries[-1] # Pega a última linha adicionada

                entry_info['servico'].set(item_dict.get('servico', ''))
                # Limpa e insere nos tk.Entry
                entry_info['locacao'].delete(0, tk.END)
                entry_info['locacao'].insert(0, item_dict.get('locacao', ''))
                entry_info['descricao'].delete(0, tk.END)
                entry_info['descricao'].insert(0, item_dict.get('descricao', ''))
                entry_info['valor'].delete(0, tk.END)

                # Formata o valor para exibição no Entry (com vírgula decimal)
                try:
                    valor_float = float(item_dict.get('valor', 0.0))
                    valor_str = f"{valor_float:.2f}".replace('.', ',')
                except (ValueError, TypeError):
                    valor_str = "0,00" # Valor padrão em caso de erro
                entry_info['valor'].insert(0, valor_str)


            # Mudar para a aba da calculadora
            self.notebook.select(self.tab_calculadora)
            messagebox.showinfo("Sucesso", f"Grupo '{nome_grupo}' carregado na calculadora!", parent=self.root)

        except (IndexError, TypeError, Exception) as e: # Captura erro de índice, tipo ou outro inesperado
            messagebox.showerror("Erro ao Carregar", f"Não foi possível carregar o grupo selecionado.\nErro: {e}", parent=self.root)
            # Pode ser útil limpar a calculadora se o carregamento falhou no meio
            while self.entries:
                self.remover_servico_ui(self.entries[0]['frame'])


    def editar_grupo_selecionado(self):
        """Carrega o primeiro grupo selecionado para edição na calculadora (exclui o original)."""
        selection = self.tree_servicos.selection()
        if not selection:
            messagebox.showinfo("Nenhum Grupo Selecionado", "Selecione um grupo para editar.", parent=self.root)
            return
        if len(selection) > 1:
             messagebox.showwarning("Múltiplos Grupos", "Apenas o primeiro grupo selecionado será carregado para edição.", parent=self.root)

        primeiro_item_id_str = selection[0]
        index_para_editar = self._get_index_from_iid(primeiro_item_id_str)

        if index_para_editar is None:
            messagebox.showerror("Erro ao Editar", "Não foi possível encontrar o grupo selecionado para edição (índice inválido ou inconsistente).", parent=self.root)
            return

        try:
            # Valida antes de pegar o nome
            if not (0 <= index_para_editar < len(self.servicos_salvos) and isinstance(self.servicos_salvos[index_para_editar], dict)):
                 raise IndexError("Índice ou tipo de dado inválido para edição.")
            nome_grupo = self.servicos_salvos[index_para_editar].get('nome', 'Sem Nome')

            if messagebox.askyesno("Confirmar Edição",
                                 f"O grupo '{nome_grupo}' será carregado na calculadora e removido da lista de salvos.\n"
                                 "Você poderá salvá-lo novamente com as alterações.\n\nContinuar?",
                                 parent=self.root):

                # 1. Armazena temporariamente os dados do grupo ANTES de qualquer modificação
                grupo_original_data = self.servicos_salvos[index_para_editar]

                # 2. Exclui o grupo original da lista e do arquivo PRIMEIRO
                del self.servicos_salvos[index_para_editar]
                if not self.salvar_servicos_no_arquivo():
                    # Se falhar ao salvar a exclusão, restaura o grupo na lista e aborta
                    self.servicos_salvos.insert(index_para_editar, grupo_original_data)
                    messagebox.showerror("Erro ao Salvar", "Não foi possível salvar a remoção do grupo original. A edição foi cancelada.", parent=self.root)
                    return
                else:
                    # A exclusão foi salva, atualiza a lista visual ANTES de carregar
                    # Limpa os filtros antes de atualizar a lista visual da exclusão
                    filtro_nome_atual = self.filtro_servicos_var.get().lower()
                    filtro_data_atual = self._get_date_from_string(self.filtro_data_unica_var.get())
                    self.atualizar_lista_servicos_salvos(filtro_nome_atual, filtro_data_atual)


                # 3. Agora, carrega os dados armazenados (grupo_original_data) na calculadora
                # Reutiliza a lógica de carregar, mas com os dados em memória
                if self.entries: # Limpa calculadora se necessário (sem perguntar de novo)
                     while self.entries:
                          self.remover_servico_ui(self.entries[0]['frame'])

                itens_originais = grupo_original_data.get('itens', [])
                if not isinstance(itens_originais, list): itens_originais = []

                for item_dict in itens_originais:
                     if not isinstance(item_dict, dict): continue
                     self.adicionar_servico_ui()
                     entry_info = self.entries[-1]
                     entry_info['servico'].set(item_dict.get('servico', ''))
                     entry_info['locacao'].delete(0, tk.END)
                     entry_info['locacao'].insert(0, item_dict.get('locacao', ''))
                     entry_info['descricao'].delete(0, tk.END)
                     entry_info['descricao'].insert(0, item_dict.get('descricao', ''))
                     entry_info['valor'].delete(0, tk.END)
                     try:
                          valor_float = float(item_dict.get('valor', 0.0))
                          valor_str = f"{valor_float:.2f}".replace('.', ',')
                     except (ValueError, TypeError): valor_str = "0,00"
                     entry_info['valor'].insert(0, valor_str)

                # 4. Muda para a aba da calculadora
                self.notebook.select(self.tab_calculadora)
                messagebox.showinfo("Pronto para Editar", f"Grupo '{nome_grupo}' carregado para edição. Faça suas alterações e salve novamente.", parent=self.root)


        except (IndexError, TypeError, Exception) as e: # Captura erro ao obter nome, confirmar, excluir ou carregar
            messagebox.showerror("Erro ao Editar", f"Não foi possível iniciar a edição do grupo.\nErro: {e}", parent=self.root)
            # Se o erro ocorreu depois da exclusão, a lista pode estar inconsistente.
            # Recarregar a lista pode ser uma opção, mas pode perder o estado do filtro.
            # Tenta reatualizar com filtros atuais como melhor esforço:
            try:
                filtro_nome_atual = self.filtro_servicos_var.get().lower()
                filtro_data_atual = self._get_date_from_string(self.filtro_data_unica_var.get())
                self.atualizar_lista_servicos_salvos(filtro_nome_atual, filtro_data_atual)
            except Exception as update_err:
                 print(f"Erro adicional ao tentar atualizar lista após falha na edição: {update_err}")


    def _get_date_from_string(self, date_str: str) -> Optional[date]: # Retorna date
        """Tenta converter uma string DD/MM/YYYY para objeto date."""
        if not isinstance(date_str, str): return None # Garante que é string
        try:
            # Tenta formatos comuns, incluindo DDMMYYYY
            formats_to_try = ["%d/%m/%Y", "%d-%m-%Y", "%d%m%Y"]
            parsed_date = None
            for fmt in formats_to_try:
                 try:
                      parsed_date = datetime.strptime(date_str.strip(), fmt).date()
                      break # Sai do loop se encontrar um formato válido
                 except ValueError:
                      continue # Tenta o próximo formato
            return parsed_date # Retorna a data ou None se nenhum formato funcionou

        except ValueError: # Captura erro final se nenhum formato funcionou
            pass # Ignora formato inválido
        return None

    def excluir_grupos_selecionados(self):
        """Exclui o(s) grupo(s) selecionado(s) da lista e do arquivo."""
        selection = self.tree_servicos.selection()
        if not selection:
            messagebox.showinfo("Nenhum Grupo Selecionado", "Selecione um ou mais grupos para excluir.", parent=self.root)
            return

        nomes_grupos = []
        indices_para_excluir = set() # Usar set para evitar duplicatas e lidar com índices inválidos

        for item_id in selection:
            index = self._get_index_from_iid(item_id)
            if index is not None:
                 # Verifica se o índice é realmente válido ANTES de adicionar ao set
                 if 0 <= index < len(self.servicos_salvos):
                     indices_para_excluir.add(index)
                     # Pega o nome apenas para a mensagem de confirmação
                     try:
                        nome = self.servicos_salvos[index].get('nome', f'Índice {index} Sem Nome')
                        nomes_grupos.append(nome)
                     except Exception: # Se houver erro ao pegar nome, ainda tenta excluir pelo índice
                        nomes_grupos.append(f"Grupo no índice {index}")
                 else:
                      print(f"Aviso: Índice {index} do IID {item_id} é inválido para a lista atual.")
            else:
                 print(f"Item selecionado inválido ignorado: {item_id}")


        if not indices_para_excluir:
             messagebox.showwarning("Seleção Inválida", "Nenhum grupo válido encontrado na seleção para excluir.", parent=self.root)
             return

        nomes_str = "\n - ".join(nomes_grupos)
        num_grupos = len(indices_para_excluir)
        plural_s = "s" if num_grupos > 1 else ""
        plural_este = "Estes" if num_grupos > 1 else "Este"

        if messagebox.askyesno("Confirmar Exclusão",
                             f"Deseja realmente excluir o{plural_s} {num_grupos} grupo{plural_s} selecionado{plural_s}?\n\n - {nomes_str}\n\n{plural_este} grupo{plural_s} ser{('ão' if num_grupos > 1 else 'á')} removido{plural_s} permanentemente.",
                             parent=self.root):

            # Remove os itens da lista self.servicos_salvos pelos índices
            # É mais seguro remover pelos índices em ordem reversa para não afetar os índices subsequentes
            indices_ordenados_reverso = sorted(list(indices_para_excluir), reverse=True)
            grupos_removidos_cont = 0
            for index in indices_ordenados_reverso:
                try:
                    # Confirma novamente se o índice ainda é válido antes de deletar
                    if 0 <= index < len(self.servicos_salvos):
                         del self.servicos_salvos[index]
                         grupos_removidos_cont += 1
                    else:
                         print(f"Erro: Índice {index} tornou-se inválido antes da exclusão (pulado).")
                except IndexError:
                     print(f"Erro: Índice {index} já não existia ao tentar excluir (pulado).") # Segurança extra

            if grupos_removidos_cont < num_grupos:
                 messagebox.showwarning("Aviso de Exclusão", f"{num_grupos - grupos_removidos_cont} grupo(s) não puderam ser removidos pois seus índices se tornaram inválidos durante o processo.", parent=self.root)


            # Salva a lista atualizada no arquivo
            if self.salvar_servicos_no_arquivo():
                # Atualiza a TreeView com os filtros atuais
                # Busca os valores atuais dos filtros antes de chamar a atualização
                filtro_nome_atual = self.filtro_servicos_var.get().lower()
                filtro_data_atual = self._get_date_from_string(self.filtro_data_unica_var.get())
                self.atualizar_lista_servicos_salvos(filtro_nome_atual, filtro_data_atual)

                # Limpa os detalhes, pois o item pode ter sido excluído
                for item in self.tree_detalhes.get_children():
                    self.tree_detalhes.delete(item)
                self.lbl_titulo_detalhes.config(text="Detalhes do Grupo")
                if grupos_removidos_cont > 0:
                     messagebox.showinfo("Sucesso", f"{grupos_removidos_cont} grupo{plural_s if grupos_removidos_cont > 1 else ''} excluído{plural_s if grupos_removidos_cont > 1 else ''} com sucesso!", parent=self.root)
            # else: O erro já foi mostrado ao salvar

    # --- Geração de PDF ---

    def _preparar_dados_pdf_grupo(self, index: int) -> Optional[Dict[str, Any]]:
        """Prepara os dados de um único grupo para o formato do PDF.
           Valida o índice e o tipo de dado antes de usar.
        """
        if not (0 <= index < len(self.servicos_salvos)):
            print(f"Erro interno: Índice inválido {index} para preparar dados PDF.")
            return None

        grupo_raw = self.servicos_salvos[index]
        if not isinstance(grupo_raw, dict):
            print(f"Erro interno: Dado no índice {index} não é um dicionário.")
            return None

        dados_formatados = {
            'nome_grupo': grupo_raw.get('nome', 'Grupo Sem Nome'),
            'total': grupo_raw.get('total', 0.0),
            'itens': []
        }

        itens_raw = grupo_raw.get('itens', [])
        if not isinstance(itens_raw, list):
             print(f"Aviso: 'itens' no grupo '{dados_formatados['nome_grupo']}' não é uma lista. PDF pode ficar incompleto.")
             itens_raw = [] # Trata como lista vazia

        for item_raw in itens_raw:
            if isinstance(item_raw, dict): # Garante que cada item é um dicionário
                dados_formatados['itens'].append({
                    'servico': item_raw.get('servico', ''), # Default para string vazia
                    'locacao': item_raw.get('locacao', ''),
                    'descricao': item_raw.get('descricao', ''),
                    'valor': item_raw.get('valor', 0.0) # Default para 0.0
                })
            else:
                 print(f"Aviso: Item inválido encontrado no grupo '{dados_formatados['nome_grupo']}'. Ignorado no PDF.")

        return dados_formatados

    def gerar_pdf_grupo_selecionado(self):
        """Gera PDF para o primeiro grupo selecionado na lista."""
        if not REPORTLAB_AVAILABLE:
            messagebox.showerror("Dependência Ausente", "A biblioteca ReportLab é necessária para gerar PDFs.\nInstale com: pip install reportlab", parent=self.root)
            return

        selection = self.tree_servicos.selection()
        if not selection:
            messagebox.showinfo("Nenhum Grupo Selecionado", "Selecione um grupo para gerar o PDF.", parent=self.root)
            return
        if len(selection) > 1:
             messagebox.showwarning("Múltiplos Grupos", "Apenas o PDF do primeiro grupo selecionado será gerado.", parent=self.root)

        primeiro_item_id_str = selection[0]
        index = self._get_index_from_iid(primeiro_item_id_str)

        if index is None:
            messagebox.showerror("Erro ao Gerar PDF", "Não foi possível encontrar o grupo selecionado (índice inválido ou inconsistente).", parent=self.root)
            return

        try:
            dados_grupo = self._preparar_dados_pdf_grupo(index)
            if dados_grupo:
                # Sugere nome baseado no grupo
                nome_sugerido = f"Orcamento_{dados_grupo['nome_grupo']}.pdf"
                # Limpa caracteres inválidos para nome de arquivo
                nome_sugerido = "".join(c if c.isalnum() or c in ['_', '-'] else '_' for c in nome_sugerido)
                # Chama gerar_pdf com uma lista contendo apenas este grupo
                self.gerar_pdf(grupos_para_pdf=[dados_grupo], nome_arquivo_sugerido=nome_sugerido)
            else:
                # _preparar_dados_pdf_grupo retornou None
                raise ValueError("Falha ao preparar dados do grupo selecionado (verifique logs/console).")
        except Exception as e: # Captura erro na preparação ou chamada do gerar_pdf
            messagebox.showerror("Erro ao Gerar PDF", f"Não foi possível obter ou processar os dados do grupo selecionado.\nErro: {e}", parent=self.root)


    def gerar_pdf_grupos_selecionados(self):
        """Gera um PDF único contendo todos os grupos selecionados."""
        if not REPORTLAB_AVAILABLE:
            messagebox.showerror("Dependência Ausente", "A biblioteca ReportLab é necessária para gerar PDFs.\nInstale com: pip install reportlab", parent=self.root)
            return

        selection = self.tree_servicos.selection()
        if not selection:
            messagebox.showinfo("Nenhum Grupo Selecionado", "Selecione um ou mais grupos para gerar o PDF combinado.", parent=self.root)
            return

        grupos_pdf = []
        nomes_grupos = []
        ids_falha = []

        for item_id in selection:
            index = self._get_index_from_iid(item_id)
            if index is not None:
                dados = self._preparar_dados_pdf_grupo(index)
                if dados:
                    grupos_pdf.append(dados)
                    nomes_grupos.append(dados['nome_grupo'])
                else:
                    # O índice era válido mas a preparação falhou
                    ids_falha.append(item_id)
                    print(f"Aviso: Falha ao preparar dados para PDF do índice {index} (IID: {item_id}). Verifique console.")
            else:
                ids_falha.append(item_id) # IID inválido ou índice inconsistente

        if not grupos_pdf:
            messagebox.showerror("Erro", "Nenhum grupo válido encontrado ou preparado na seleção para gerar o PDF.", parent=self.root)
            return

        if ids_falha:
             messagebox.showwarning("Aviso", f"Alguns itens selecionados ({len(ids_falha)}) não puderam ser processados ou encontrados e foram ignorados.", parent=self.root)

        # Sugere um nome de arquivo baseado nos grupos
        nome_sugerido = f"Orcamento_Multiplos"
        if nomes_grupos:
             nome_sugerido = f"Orcamento_{nomes_grupos[0]}"
             if len(nomes_grupos) > 1:
                 nome_sugerido += f"_e_{len(nomes_grupos)-1}_outros"
        nome_sugerido += ".pdf"
        nome_sugerido = "".join(c if c.isalnum() or c in ['_', '-'] else '_' for c in nome_sugerido) # Limpa caracteres inválidos

        # Chama gerar_pdf passando a lista de grupos
        self.gerar_pdf(grupos_para_pdf=grupos_pdf, nome_arquivo_sugerido=nome_sugerido)


    def gerar_pdf(self, grupos_para_pdf: Optional[List[Dict[str, Any]]] = None, nome_arquivo_sugerido: Optional[str] = None):
        """Gera o arquivo PDF. Pode receber dados da calculadora ou de grupos salvos."""
        if not REPORTLAB_AVAILABLE:
            messagebox.showerror("Dependência Ausente", "A biblioteca ReportLab é necessária para gerar PDFs.", parent=self.root)
            return

        dados_pdf: List[Dict[str, Any]] = []
        grand_total = 0.0
        is_calculadora_atual = False

        if grupos_para_pdf is not None: # Verifica se foi passado argumento (pode ser lista vazia)
            # Usar dados dos grupos fornecidos (já validados e preparados)
            dados_pdf = grupos_para_pdf
            # Calcula o total geral a partir dos totais individuais dos grupos preparados
            try:
                 grand_total = sum(float(g.get('total', 0.0)) for g in dados_pdf)
            except (ValueError, TypeError):
                 messagebox.showerror("Erro Interno PDF", "Erro ao calcular total geral dos grupos.", parent=self.root)
                 return
            # O nome sugerido já deve ter sido tratado antes
        else:
            # Usar dados da calculadora atual
            is_calculadora_atual = True
            resultado = self._get_dados_calculadora_atual()
            if resultado is None: # Erro de validação nos campos da calculadora
                return
            itens_calculadora, total_calculadora = resultado
            if not itens_calculadora:
                messagebox.showinfo("Sem Dados", "Não há serviços na calculadora para gerar o PDF.", parent=self.root)
                return
            # Encapsula os dados da calculadora como um único "grupo" para o PDF
            dados_pdf = [{
                'nome_grupo': "Orçamento Atual da Calculadora", # Nome padrão
                'total': total_calculadora,
                'itens': itens_calculadora # Já validado em _get_dados_calculadora_atual
            }]
            grand_total = total_calculadora # Já é float
            nome_arquivo_sugerido = nome_arquivo_sugerido or "Orcamento_Imobiliario_Atual.pdf"


        if not dados_pdf: # Checa se, após toda a lógica, ainda não há dados
             messagebox.showerror("Erro PDF", "Não há dados válidos para gerar o PDF.", parent=self.root)
             return


        # --- Solicitar local para salvar o PDF ---
        file_path = filedialog.asksaveasfilename(
            initialfile=nome_arquivo_sugerido or "Orcamento.pdf",
            defaultextension=".pdf",
            filetypes=[("Arquivos PDF", "*.pdf"), ("Todos os arquivos", "*.*")],
            title="Salvar Orçamento em PDF",
            parent=self.root
        )
        if not file_path:
            return # Usuário cancelou

        # --- Geração do PDF com ReportLab ---
        try:
            doc = SimpleDocTemplate(file_path, pagesize=A4,
                                    leftMargin=1.5*cm, rightMargin=1.5*cm,
                                    topMargin=1.5*cm, bottomMargin=1.5*cm)
            styles = getSampleStyleSheet()
            elements = []

            # --- >>> INÍCIO DAS DEFINIÇÕES DE ESTILO <<< ---
            # Estilos personalizados
            styles.add(ParagraphStyle(name='NormalRight', parent=styles['Normal'], alignment=2)) # TA_RIGHT = 2
            styles.add(ParagraphStyle(name='NormalCenter', parent=styles['Normal'], alignment=1)) # TA_CENTER = 1
            styles.add(ParagraphStyle(name='CompanyName', parent=styles['h1'], alignment=1, textColor=COR_PRIMARIA))
            styles.add(ParagraphStyle(name='CompanyInfo', parent=styles['Normal'], alignment=1, fontSize=9, spaceBefore=2, spaceAfter=8))
            styles.add(ParagraphStyle(name='DocTitle', parent=styles['h2'], alignment=1, spaceAfter=10, textColor=COR_PRIMARIA))
            styles.add(ParagraphStyle(name='GroupTitle', parent=styles['Heading2'], spaceBefore=12, spaceAfter=6, textColor=COR_PRIMARIA, alignment=0)) # Esquerda
            styles.add(ParagraphStyle(name='TotalLabel', parent=styles['Normal'], alignment=2, fontName='Helvetica-Bold'))
            styles.add(ParagraphStyle(name='TotalValue', parent=styles['Normal'], alignment=2, fontName='Helvetica-Bold'))

            # Definição do estilo TableHeader usando os elementos da tupla FONTE_CABECALHO_TABELA
            styles.add(ParagraphStyle(name='TableHeader',
                              parent=styles['Normal'],
                              fontName=FONTE_CABECALHO_TABELA[0], # Correto
                              fontSize=FONTE_CABECALHO_TABELA[1], # Correto
                              alignment=1,
                              textColor=colors.white))
            styles.add(ParagraphStyle(name='TableCell', parent=styles['Normal'], fontSize=10)) # Estilo base para células
            styles.add(ParagraphStyle(name='TableCellRight', parent=styles['TableCell'], alignment=2))
            styles.add(ParagraphStyle(name='NotesHeader', parent=styles['h3'], spaceBefore=15, spaceAfter=5))
            styles.add(ParagraphStyle(name='NotesText', parent=styles['Normal'], fontSize=9, leftIndent=10, spaceBefore=2))
            styles.add(ParagraphStyle(name='SignatureLine', parent=styles['Normal'], alignment=1, spaceBefore=40))
            # --- >>> FIM DAS DEFINIÇÕES DE ESTILO <<< ---


            # 1. Cabeçalho da Empresa
            elements.append(Paragraph(self.nome_empresa, styles['CompanyName']))
            elements.append(Paragraph(f"Telefone: {self.telefone_empresa} | E-mail: {self.email_empresa}", styles['CompanyInfo']))
            elements.append(Paragraph(f"Endereço: {self.endereco_empresa}", styles['CompanyInfo']))
            elements.append(Paragraph(f"Data de Geração: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['CompanyInfo']))
            #elements.append(Spacer(1, 0.5*cm))

            # 2. Título Principal do Documento
            elements.append(Paragraph("Orçamento de Serviços Imobiliários", styles['DocTitle']))
            #elements.append(Spacer(1, 0.3*cm))


            # --- Loop através dos grupos ---
            for idx_grupo, grupo_data in enumerate(dados_pdf):
                # Validações básicas do grupo_data (já feito em _preparar_dados...)
                nome_grupo = grupo_data.get('nome_grupo', f'Grupo {idx_grupo + 1}')
                itens_grupo = grupo_data.get('itens', []) # Deve ser lista
                total_grupo = grupo_data.get('total', 0.0) # Deve ser float/int

                # Adiciona espaço antes do próximo grupo (exceto o primeiro)
                if idx_grupo > 0:
                     elements.append(Spacer(1, 0.8*cm))
                     # Considerar PageBreak se a lista de grupos for muito grande?
                     # elements.append(PageBreak())

                # Adiciona o nome do grupo como título (se houver mais de um grupo total ou se for da calculadora)
                if len(dados_pdf) > 1 or is_calculadora_atual:
                     elements.append(Paragraph(f"{nome_grupo}", styles['GroupTitle']))

                # --- Tabela de Itens do Grupo (LÓGICA REVISADA) ---
                data_table = [] # Initialize empty list for table data
                # Cabeçalhos da Tabela (sempre presentes)
                # Usa o estilo 'TableHeader' corrigido
                header_row = [
                    Paragraph('Serviço', styles['TableHeader']),
                    Paragraph('Locação', styles['TableHeader']),
                    Paragraph('Descrição', styles['TableHeader']),
                    Paragraph('Valor', styles['TableHeader'])
                ]
                data_table.append(header_row)

                # Adiciona linhas de itens SOMENTE se itens_grupo não for vazio
                if isinstance(itens_grupo, list) and itens_grupo:
                    for item_dict in itens_grupo:
                        # Valida se item é dict (redundante se _preparar_dados_pdf_grupo fez certo)
                        if not isinstance(item_dict, dict): continue

                        # Usa .get com default empty strings/0.0 para segurança
                        servico_txt = str(item_dict.get('servico', ''))
                        locacao_txt = str(item_dict.get('locacao', ''))
                        descricao_txt = str(item_dict.get('descricao', ''))
                        valor_num = item_dict.get('valor', 0.0)
                        valor_fmt = self._formatar_moeda(valor_num) # Já trata erro de formatação

                        data_table.append([
                            Paragraph(servico_txt, styles['TableCell']),
                            Paragraph(locacao_txt, styles['TableCell']),
                            Paragraph(descricao_txt, styles['TableCell']),
                            Paragraph(valor_fmt, styles['TableCellRight'])
                        ])
                # else: Se itens_grupo for vazio ou não for lista, data_table só terá o header

                # Adiciona linha de subtotal do grupo
                # Condições: Mais de um grupo no PDF E este grupo tinha itens
                add_subtotal_row = len(dados_pdf) > 1 and isinstance(itens_grupo, list) and itens_grupo
                if add_subtotal_row:
                    subtotal_row = [
                         '', '', # Colunas vazias
                         Paragraph('Subtotal do Grupo:', styles['TotalLabel']),
                         Paragraph(self._formatar_moeda(total_grupo), styles['TotalValue'])
                    ]
                    data_table.append(subtotal_row)

                # --- Cria e Estiliza a Tabela ---
                # Só cria a tabela se tiver pelo menos o cabeçalho (data_table não estará vazia)
                largura_util = A4[0] - 3*cm # Largura total da página menos margens
                col_widths = [largura_util * 0.20, # Serviço
                              largura_util * 0.25, # Locação
                              largura_util * 0.35, # Descrição
                              largura_util * 0.20] # Valor
                table = Table(data_table, colWidths=col_widths)

                # Estilo Base da Tabela (Comandos para TableStyle já estavam usando o índice da tupla corretamente)
                table_style_commands = [
                    # Header Style
                    ('BACKGROUND', (0, 0), (-1, 0), COR_PRIMARIA),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
                    ('FONTNAME', (0, 0), (-1, 0), FONTE_CABECALHO_TABELA[0]), # Nome da fonte
                    ('FONTSIZE', (0, 0), (-1, 0), FONTE_CABECALHO_TABELA[1]), # Tamanho da fonte
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    ('TOPPADDING', (0, 0), (-1, 0), 8),
                    # Grid only for header initially
                    ('GRID', (0, 0), (-1, 0), 0.5, colors.grey),
                ]

                # Estilos do Corpo (se houver linhas de dados, i.e. num_rows > 1)
                if len(data_table) > 1:
                    # Define a última linha de dados (pode ser a subtotal ou a última de itens)
                    last_data_row_index = len(data_table) - 1

                    table_style_commands.extend([
                        # Body Background and Alignment
                        ('BACKGROUND', (0, 1), (-1, last_data_row_index), colors.white),
                        ('VALIGN', (0, 1), (-1, last_data_row_index), 'TOP'),
                        ('ALIGN', (3, 1), (3, last_data_row_index), 'RIGHT'), # Align Valor column
                        ('BOTTOMPADDING', (0, 1), (-1, last_data_row_index), 5),
                        ('TOPPADDING', (0, 1), (-1, last_data_row_index), 5),
                        # Grid for all data rows (including subtotal if present)
                        ('GRID', (0, 1), (-1, last_data_row_index), 0.5, colors.grey),
                    ])

                    # Estilo Específico para linha de subtotal (se foi adicionada)
                    if add_subtotal_row:
                        subtotal_row_index = last_data_row_index # É a última linha
                        table_style_commands.extend([
                            ('BACKGROUND', (0, subtotal_row_index), (-1, subtotal_row_index), COR_SECUNDARIA),
                            ('ALIGN', (2, subtotal_row_index), (2, subtotal_row_index), 'RIGHT'), # Label 'Subtotal'
                            ('ALIGN', (3, subtotal_row_index), (3, subtotal_row_index), 'RIGHT'), # Valor do subtotal
                            ('VALIGN', (0, subtotal_row_index), (-1, subtotal_row_index), 'MIDDLE'),
                            ('FONTNAME', (2, subtotal_row_index), (3, subtotal_row_index), 'Helvetica-Bold'),
                            ('TEXTCOLOR', (2, subtotal_row_index), (3, subtotal_row_index), COR_TEXTO), # Garante cor do texto
                            ('BOTTOMPADDING', (0, subtotal_row_index), (-1, subtotal_row_index), 6),
                            ('TOPPADDING', (0, subtotal_row_index), (-1, subtotal_row_index), 6),
                        ])

                # Aplica o estilo compilado
                table.setStyle(TableStyle(table_style_commands))
                elements.append(table)
                # Fim da lógica da tabela do grupo


            # --- Grand Total (mostra sempre) ---
            elements.append(Spacer(1, 0.5*cm))
            # Tabela para o total geral
            total_geral_data = [[
                Paragraph('VALOR TOTAL GERAL:', styles['TotalLabel']),
                Paragraph(self._formatar_moeda(grand_total), styles['TotalValue'])
            ]]
            total_geral_table = Table(total_geral_data, colWidths=[col_widths[0] + col_widths[1] + col_widths[2], col_widths[3]])
            total_geral_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 12),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
                ('BACKGROUND', (0, 0), (-1, -1), COR_PRIMARIA),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            elements.append(total_geral_table)
            #elements.append(Spacer(1, 0.5*cm))


            # --- Rodapé / Observações ---
            elements.append(Paragraph("Observações:", styles['NotesHeader']))
            elements.append(Paragraph("Valores sujeitos a alteração sem aviso prévio.", styles['NotesText']))
            elements.append(Paragraph("Validade desta proposta: 30 dias (salvo indicação contrária).", styles['NotesText']))
            elements.append(Paragraph("Condições de pagamento a combinar.", styles['NotesText']))

            # Assinatura
            elements.append(Paragraph("_______________________________", styles['SignatureLine']))
            elements.append(Paragraph(self.nome_empresa, styles['NormalCenter']))


            # --- Construir o PDF ---
            doc.build(elements)

            # --- Abrir PDF ---
            if messagebox.askyesno("PDF Gerado", f"PDF '{os.path.basename(file_path)}' gerado com sucesso!\nDeseja abri-lo agora?", parent=self.root):
                self.abrir_arquivo(file_path)

            # --- Tentar carregar o PDF recém-criado na aba de preview ---
            if PYMUPDF_AVAILABLE:
                 if self.pdf_preview_doc:
                      self.pdf_preview_doc.close() # Fecha o anterior
                 try:
                      self.pdf_preview_doc = fitz.open(file_path)
                      self.pdf_preview_path = file_path
                      self.pdf_preview_page_num = 0
                      num_pages = len(self.pdf_preview_doc)
                      filename = os.path.basename(file_path)
                      self.lbl_pdf_info.config(text=f"Arquivo: {filename}\nPáginas: {num_pages}")
                      self.btn_prev_page.config(state=tk.DISABLED)
                      self.btn_next_page.config(state=tk.NORMAL if num_pages > 1 else tk.DISABLED)
                      self._exibir_pagina_pdf()
                      # Opcional: Mudar para a aba de preview automaticamente
                      # self.notebook.select(self.tab_pdf_preview)
                 except Exception as load_err:
                      print(f"Aviso: Não foi possível carregar automaticamente o PDF gerado para preview: {load_err}")


        except PermissionError:
             messagebox.showerror("Erro de Permissão", f"Não foi possível salvar o arquivo em:\n{file_path}\n\nVerifique se o arquivo já está aberto ou se você tem permissão para escrever neste local.", parent=self.root)
        except Exception as e:
            messagebox.showerror("Erro ao Gerar PDF", f"Ocorreu um erro inesperado ao gerar o PDF:\n{str(e)}", parent=self.root)
            import traceback
            print("--- ERRO DETALHADO NA GERAÇÃO DO PDF ---")
            traceback.print_exc() # Log completo no console
            print("--- FIM DO ERRO DETALHADO ---")


    def abrir_arquivo(self, file_path: str):
        """Abre um arquivo usando o aplicativo padrão do sistema."""
        try:
            # Garante que o caminho é absoluto e normalizado
            abs_path = os.path.abspath(file_path)
            if platform.system() == 'Windows':
                # Tenta usar startfile que é mais robusto no Windows
                os.startfile(abs_path)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', abs_path], check=True)
            else:  # Linux e outros
                subprocess.run(['xdg-open', abs_path], check=True)
        except FileNotFoundError:
             messagebox.showwarning("Erro ao Abrir", f"Não foi possível encontrar o aplicativo padrão ou o próprio arquivo PDF:\n{abs_path}", parent=self.root)
        except Exception as e:
            messagebox.showwarning("Erro ao Abrir", f"Não foi possível abrir o arquivo automaticamente:\n{abs_path}\nErro: {e}", parent=self.root)


    # --- Funções de Callback para Scroll ---
    def _on_frame_configure(self, event=None):
        """Atualiza a região de rolagem do canvas quando o frame interno muda de tamanho."""
        # Usar after_idle pode ser mais seguro que um tempo fixo
        self.root.after_idle(lambda: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

    def _on_canvas_configure(self, event=None):
        """Redimensiona o frame interno para preencher a largura do canvas."""
        canvas_width = self.canvas.winfo_width()
        if canvas_width > 0: # Evita definir largura 0 durante inicialização
            self.canvas.itemconfig(self.canvas_window, width=canvas_width)

    def _on_mousewheel(self, event):
        """Permite rolar a área de entradas com a roda do mouse."""
        # Verifica se o widget sob o mouse está DENTRO da área rolável
        widget_sob_mouse = self.root.winfo_containing(event.x_root, event.y_root)

        # --- Verifica se o scroll é para o canvas da calculadora OU para o canvas do PDF ---
        target_canvas = None
        target_frame = None

        parent_check = widget_sob_mouse
        while parent_check is not None:
             if parent_check == self.frame_interno: # Scroll na lista da calculadora
                  target_canvas = self.canvas
                  break
             # Verifica se está dentro do canvas de PDF ou do seu label filho
             if hasattr(self, 'pdf_preview_canvas') and (parent_check == self.pdf_preview_canvas or parent_check == self.pdf_preview_image_label):
                 # ATENÇÃO: Scroll no canvas de PDF não está implementado por padrão
                 # Esta parte apenas identifica que o mouse está sobre ele.
                 # Para scroll de imagem/zoom, seria necessário implementar a lógica aqui.
                 # target_canvas = self.pdf_preview_canvas # Descomente se implementar scroll no PDF
                 print("Scroll sobre área de PDF (não implementado)") # Apenas para debug
                 return # Impede o scroll padrão no canvas de PDF por enquanto
             parent_check = parent_check.master # Sobe na hierarquia

        # Se o alvo for o canvas da calculadora, faz o scroll
        if target_canvas == self.canvas:
            delta = 0
            if platform.system() == 'Windows':
                delta = -1 * int(event.delta / 120)
            elif platform.system() == 'Darwin':
                 delta = -1 * int(event.delta)
            else: # Linux
                if event.num == 4: delta = -1
                elif event.num == 5: delta = 1

            if delta != 0: # Só rola se houver delta
                 target_canvas.yview_scroll(delta, "units")


# --- Inicialização ---
def main():
    root = tk.Tk()
    # Tenta definir um ícone (opcional)
    # ... (código do ícone) ...

    app = CalculadoraImobiliaria(root)

    # Adiciona uma rotina para fechar o documento PDF ao sair
    def on_closing():
        if hasattr(app, 'pdf_preview_doc') and app.pdf_preview_doc:
            print("Fechando documento PDF aberto...")
            app.pdf_preview_doc.close()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    # Verifica dependências e avisa
    if not REPORTLAB_AVAILABLE:
        temp_root = tk.Tk()
        temp_root.withdraw()
        messagebox.showwarning("Dependência Ausente: ReportLab",
                               "A biblioteca 'ReportLab' não foi encontrada.\nA funcionalidade de gerar PDF estará desativada.\n\nInstale com: pip install reportlab",
                               parent=None)
        temp_root.destroy()
        # return # Descomente para sair se ReportLab for essencial

    if not PYMUPDF_AVAILABLE:
        temp_root = tk.Tk()
        temp_root.withdraw()
        messagebox.showwarning("Dependência Ausente: PyMuPDF",
                               "A biblioteca 'PyMuPDF' (fitz) não foi encontrada.\nA funcionalidade de pré-visualização de PDF na nova aba estará desativada.\n\nInstale com: pip install pymupdf",
                               parent=None)
        temp_root.destroy()

    main()
