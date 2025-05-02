import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import platform
import subprocess
import json
from datetime import datetime
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
FONTE_CABECALHO_TABELA = ('Helvetica-Bold', 12)
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
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

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

        self._criar_aba_calculadora()
        self._criar_aba_servicos_salvos()
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

        self.lbl_copyright = tk.Label(center_frame,
                                     text=f"© {datetime.now().year} {self.nome_empresa}",
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
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel) # Roda do mouse

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
        self._criar_frame_lista_grupos(frame_lista)

        # Painel Direito (Detalhes do Grupo)
        self.frame_detalhes = ttk.Frame(frame_conteudo_salvos, relief=tk.GROOVE, borderwidth=1)
        self.frame_detalhes.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        self._criar_frame_detalhes_grupo(self.frame_detalhes)

        # Preencher a lista inicialmente
        self.atualizar_lista_servicos_salvos()

    def _criar_frame_lista_grupos(self, parent_frame: ttk.Frame):
        """Cria a seção da lista de grupos salvos e filtro."""
        # Filtro
        frame_filtro = ttk.Frame(parent_frame)
        frame_filtro.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(frame_filtro, text="Filtrar por nome:", font=('Segoe UI', 10)).pack(side=tk.LEFT, padx=(0, 5))
        entry_filtro = ttk.Entry(frame_filtro, textvariable=self.filtro_servicos_var, font=('Segoe UI', 10))
        entry_filtro.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.filtro_servicos_var.trace_add("write", self._filtrar_servicos_salvos) # Filtrar ao digitar

        # Treeview para Grupos
        frame_lista_scroll = ttk.Frame(parent_frame)
        frame_lista_scroll.pack(fill=tk.BOTH, expand=True)

        colunas = ('nome', 'data', 'valor', 'itens')
        self.tree_servicos = ttk.Treeview(frame_lista_scroll, columns=colunas,
                                         show='headings', selectmode='extended') # selectmode='extended' para multiselect

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
        # NOVO BOTÃO para múltiplos PDFs
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
        # Serviço
        ttk.Label(frame_entrada, text="Serviço:", font=FONTE_LABEL_ENTRADA).grid(row=0, column=0, padx=(0, 5), pady=(1,0), sticky=tk.W)
        tipos_servico = ['Venda', 'Aluguel', 'Avaliação', 'Consultoria', 'Reforma', 'Documentação', 'Outro']
        combo_servico = ttk.Combobox(frame_entrada, values=tipos_servico, width=18, state="readonly", font=('Segoe UI', 10))
        combo_servico.current(0)
        combo_servico.grid(row=1, column=0, padx=(0, 10), pady=(0,1), sticky=tk.EW)

        # Locação
        ttk.Label(frame_entrada, text="Locação:", font=FONTE_LABEL_ENTRADA).grid(row=0, column=1, padx=(0, 5), pady=(1,0), sticky=tk.W)
        entry_locacao = tk.Entry(frame_entrada, **entrada_estilo_tk)
        entry_locacao.grid(row=1, column=1, padx=(0, 10), pady=(0,1), sticky=tk.EW)

        # Valor
        ttk.Label(frame_entrada, text="Valor (R$):", font=FONTE_LABEL_ENTRADA).grid(row=0, column=2, padx=(0, 5), pady=(1,0), sticky=tk.W)
        novo_entry_valor = tk.Entry(frame_entrada, justify=tk.RIGHT, width=15, **entrada_estilo_tk)
        novo_entry_valor.grid(row=1, column=2, padx=(0, 10), pady=(0,1), sticky=tk.EW)

        # --- Linha 2: Descrição ---
        ttk.Label(frame_entrada, text="Descrição:", font=FONTE_LABEL_ENTRADA).grid(row=2, column=0, columnspan=2, padx=(0, 5), pady=(5,0), sticky=tk.W)
        entry_descricao = tk.Entry(frame_entrada, **entrada_estilo_tk)
        entry_descricao.grid(row=3, column=0, columnspan=3, padx=(0, 10), pady=(0,1), sticky=tk.EW) # Colspan 3

        # --- Botão Remover ---
        # Usando tk.Button para cor de fundo mais fácil
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

            if not (servico or locacao or descricao or valor_text): # Pula linha completamente vazia
                 continue

            valor = 0.0
            if valor_text:
                try:
                    valor_limpo = ''.join(filter(lambda c: c.isdigit() or c == ',', valor_text)).replace(",", ".")
                    if not valor_limpo: valor_limpo = '0'
                    valor = float(valor_limpo)
                except ValueError:
                    valor_entry.config(highlightbackground='red', highlightcolor='red')
                    messagebox.showerror("Erro de Valor", f"Valor inválido na linha {i+1} ('{valor_text}')")
                    valor_entry.focus_set()
                    erro = True
                    break # Para na primeira linha com erro

            dados_servicos.append({
                'servico': servico,
                'locacao': locacao,
                'descricao': descricao,
                'valor': valor
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

            # Verifica se nome já existe (opcional, mas bom)
            if any(g['nome'].lower() == nome_grupo.lower() for g in self.servicos_salvos):
                 if not messagebox.askyesno("Nome Duplicado", f"Já existe um grupo chamado '{nome_grupo}'.\nDeseja sobrescrevê-lo?", parent=dialogo):
                      entry_nome.focus_set()
                      return
                 else:
                     # Remove o grupo existente antes de adicionar o novo
                     self.servicos_salvos = [g for g in self.servicos_salvos if g['nome'].lower() != nome_grupo.lower()]


            grupo = {
                'nome': nome_grupo,
                'data': datetime.now().strftime("%d/%m/%Y"),
                'total': total,
                'itens': dados_servicos
            }

            self.servicos_salvos.append(grupo)
            # Ordena alfabeticamente (opcional)
            self.servicos_salvos.sort(key=lambda g: g['nome'].lower())

            if self.salvar_servicos_no_arquivo():
                self.atualizar_lista_servicos_salvos()
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
                # Validação básica (opcional)
                if not isinstance(self.servicos_salvos, list):
                    print("Arquivo de dados corrompido (não é uma lista). Iniciando com lista vazia.")
                    self.servicos_salvos = []
        except json.JSONDecodeError:
             messagebox.showerror("Erro ao Carregar", f"Arquivo de dados '{NOME_ARQUIVO_DADOS}' parece estar corrompido.\nSerá iniciado com uma lista vazia.")
             self.servicos_salvos = []
        except Exception as e:
            messagebox.showerror("Erro ao Carregar Arquivo", f"Não foi possível carregar os dados de:\n{arquivo_dados}\nErro: {str(e)}")
            self.servicos_salvos = [] # Inicia vazio em caso de erro grave

    def _filtrar_servicos_salvos(self, *args):
        """Filtra a TreeView de serviços salvos com base no texto do filtro."""
        filtro = self.filtro_servicos_var.get().lower()
        self.atualizar_lista_servicos_salvos(filtro)

    def atualizar_lista_servicos_salvos(self, filtro: str = ""):
        """Atualiza a TreeView de serviços salvos, aplicando um filtro opcional."""
        # Limpa a árvore
        for item in self.tree_servicos.get_children():
            self.tree_servicos.delete(item)

        # Limpa detalhes também
        for item in self.tree_detalhes.get_children():
            self.tree_detalhes.delete(item)
        self.lbl_titulo_detalhes.config(text="Detalhes do Grupo")


        # Adiciona itens filtrados
        for i, grupo in enumerate(self.servicos_salvos):
            nome = grupo.get('nome', 'Sem Nome')
            if filtro and filtro not in nome.lower():
                continue # Pula se não corresponder ao filtro

            data = grupo.get('data', '??/??/????')
            total = grupo.get('total', 0.0)
            num_itens = len(grupo.get('itens', []))
            valor_formatado = self._formatar_moeda(total)

            # Usa o índice original como ID para fácil recuperação
            self.tree_servicos.insert('', 'end', iid=str(i), values=(nome, data, valor_formatado, num_itens))

    def exibir_detalhes_grupo(self, event=None):
        """Exibe os detalhes do(s) grupo(s) selecionado(s) na TreeView."""
        selection = self.tree_servicos.selection() # Pode retornar múltiplos IDs com selectmode='extended'

        # Limpa detalhes anteriores
        for item in self.tree_detalhes.get_children():
            self.tree_detalhes.delete(item)

        if not selection:
            self.lbl_titulo_detalhes.config(text="Detalhes do Grupo")
            return

        # Se múltiplos selecionados, mostra detalhes do primeiro
        primeiro_item_id = selection[0]
        try:
            # O IID da TreeView foi definido como o índice na lista self.servicos_salvos
            index = int(primeiro_item_id)
            if 0 <= index < len(self.servicos_salvos):
                grupo = self.servicos_salvos[index]
                nome = grupo.get('nome', 'Sem Nome')
                self.lbl_titulo_detalhes.config(text=f"Detalhes: {nome}")

                for item in grupo.get('itens', []):
                    servico = item.get('servico', '')
                    locacao = item.get('locacao', '')
                    descricao = item.get('descricao', '')
                    valor = item.get('valor', 0.0)
                    valor_formatado = self._formatar_moeda(valor)
                    self.tree_detalhes.insert('', 'end', values=(servico, locacao, descricao, valor_formatado))
            else:
                 print(f"Índice inválido recuperado da seleção: {index}")
                 self.lbl_titulo_detalhes.config(text="Erro ao carregar detalhes")

        except (ValueError, IndexError) as e:
            print(f"Erro ao processar seleção {primeiro_item_id}: {e}")
            self.lbl_titulo_detalhes.config(text="Erro ao carregar detalhes")


    def carregar_grupo_na_calculadora(self):
        """Carrega o primeiro grupo selecionado na aba da calculadora."""
        selection = self.tree_servicos.selection()
        if not selection:
            messagebox.showinfo("Nenhum Grupo Selecionado", "Selecione um grupo na lista para carregar.", parent=self.root)
            return
        if len(selection) > 1:
             messagebox.showwarning("Múltiplos Grupos", "Apenas o primeiro grupo selecionado será carregado na calculadora.", parent=self.root)


        primeiro_item_id = selection[0]
        try:
            index = int(primeiro_item_id)
            if not (0 <= index < len(self.servicos_salvos)):
                raise IndexError("Índice fora do limite")

            grupo = self.servicos_salvos[index]
            nome_grupo = grupo.get('nome', 'Sem Nome')

            if self.entries:
                if not messagebox.askyesno("Confirmar Carregamento",
                                         f"Isto substituirá os dados atuais na calculadora pelo grupo '{nome_grupo}'.\nContinuar?",
                                         parent=self.root):
                    return

            # Limpa campos atuais antes de carregar
            self.limpar_campos()

            # Adiciona itens do grupo à calculadora
            for item in grupo.get('itens', []):
                self.adicionar_servico_ui() # Cria a linha na UI
                entry_info = self.entries[-1] # Pega a última linha adicionada

                entry_info['servico'].set(item.get('servico', ''))
                # Limpa e insere nos tk.Entry
                entry_info['locacao'].delete(0, tk.END)
                entry_info['locacao'].insert(0, item.get('locacao', ''))
                entry_info['descricao'].delete(0, tk.END)
                entry_info['descricao'].insert(0, item.get('descricao', ''))
                entry_info['valor'].delete(0, tk.END)
                entry_info['valor'].insert(0, f"{item.get('valor', 0.0):.2f}".replace('.', ',')) # Formato para entrada

            # Mudar para a aba da calculadora
            self.notebook.select(self.tab_calculadora)
            messagebox.showinfo("Sucesso", f"Grupo '{nome_grupo}' carregado na calculadora!", parent=self.root)

        except (ValueError, IndexError) as e:
            messagebox.showerror("Erro ao Carregar", f"Não foi possível encontrar ou carregar o grupo selecionado.\nErro: {e}", parent=self.root)


    def editar_grupo_selecionado(self):
        """Carrega o primeiro grupo selecionado para edição na calculadora (exclui o original)."""
        selection = self.tree_servicos.selection()
        if not selection:
            messagebox.showinfo("Nenhum Grupo Selecionado", "Selecione um grupo para editar.", parent=self.root)
            return
        if len(selection) > 1:
             messagebox.showwarning("Múltiplos Grupos", "Apenas o primeiro grupo selecionado será carregado para edição.", parent=self.root)

        primeiro_item_id = selection[0]
        try:
            index = int(primeiro_item_id)
            if not (0 <= index < len(self.servicos_salvos)):
                raise IndexError("Índice fora do limite")

            nome_grupo = self.servicos_salvos[index].get('nome', 'Sem Nome')

            if messagebox.askyesno("Confirmar Edição",
                                 f"O grupo '{nome_grupo}' será carregado na calculadora e removido da lista de salvos.\n"
                                 "Você poderá salvá-lo novamente com as alterações.\n\nContinuar?",
                                 parent=self.root):

                # Carrega na calculadora (já faz a limpeza e troca de aba)
                self.carregar_grupo_na_calculadora()

                # Exclui o grupo original da lista e do arquivo *após* carregar
                # Precisa recalcular o índice caso a lista tenha sido filtrada/modificada
                try:
                    # Busca novamente pelo nome, pois o índice pode ter mudado se houve filtro
                    idx_real = next(i for i, g in enumerate(self.servicos_salvos) if g.get('nome') == nome_grupo)
                    del self.servicos_salvos[idx_real]
                    self.salvar_servicos_no_arquivo()
                    self.atualizar_lista_servicos_salvos() # Atualiza a lista sem o item editado
                except StopIteration:
                     messagebox.showwarning("Aviso","Não foi possível remover o grupo original da lista (talvez já tenha sido removido).", parent=self.root)
                except Exception as e:
                     messagebox.showerror("Erro ao Remover", f"Erro ao remover grupo original '{nome_grupo}': {e}", parent=self.root)


        except (ValueError, IndexError) as e:
            messagebox.showerror("Erro ao Editar", f"Não foi possível encontrar o grupo para edição.\nErro: {e}", parent=self.root)


    def excluir_grupos_selecionados(self):
        """Exclui o(s) grupo(s) selecionado(s) da lista e do arquivo."""
        selection = self.tree_servicos.selection()
        if not selection:
            messagebox.showinfo("Nenhum Grupo Selecionado", "Selecione um ou mais grupos para excluir.", parent=self.root)
            return

        nomes_grupos = []
        indices_para_excluir = set() # Usar set para evitar duplicatas e facilitar remoção
        for item_id in selection:
            try:
                index = int(item_id)
                if 0 <= index < len(self.servicos_salvos):
                    nomes_grupos.append(self.servicos_salvos[index].get('nome', 'Sem Nome'))
                    indices_para_excluir.add(index)
            except (ValueError, IndexError):
                 print(f"Item selecionado inválido ignorado: {item_id}")


        if not indices_para_excluir:
             messagebox.showwarning("Seleção Inválida", "Nenhum grupo válido encontrado na seleção.", parent=self.root)
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
            for index in indices_ordenados_reverso:
                try:
                    del self.servicos_salvos[index]
                except IndexError:
                     print(f"Erro: Índice {index} já não existia ao tentar excluir.") # Segurança extra

            # Salva a lista atualizada no arquivo
            if self.salvar_servicos_no_arquivo():
                # Atualiza a TreeView
                self.atualizar_lista_servicos_salvos()
                # Limpa os detalhes, pois o item pode ter sido excluído
                for item in self.tree_detalhes.get_children():
                    self.tree_detalhes.delete(item)
                self.lbl_titulo_detalhes.config(text="Detalhes do Grupo")
                messagebox.showinfo("Sucesso", f"{num_grupos} grupo{plural_s} excluído{plural_s} com sucesso!", parent=self.root)

    # --- Geração de PDF ---

    def _preparar_dados_pdf_grupo(self, index: int) -> Optional[Dict[str, Any]]:
        """Prepara os dados de um único grupo para o formato do PDF."""
        if not (0 <= index < len(self.servicos_salvos)):
            return None

        grupo = self.servicos_salvos[index]
        dados_formatados = {
            'nome_grupo': grupo.get('nome', 'Grupo Sem Nome'),
            'total': grupo.get('total', 0.0),
            'itens': []
        }
        for item in grupo.get('itens', []):
            dados_formatados['itens'].append({
                'servico': item.get('servico', ''),
                'locacao': item.get('locacao', ''),
                'descricao': item.get('descricao', ''),
                'valor': item.get('valor', 0.0)
            })
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


        primeiro_item_id = selection[0]
        try:
            index = int(primeiro_item_id)
            dados_grupo = self._preparar_dados_pdf_grupo(index)
            if dados_grupo:
                # Chama gerar_pdf com uma lista contendo apenas este grupo
                self.gerar_pdf(grupos_para_pdf=[dados_grupo])
            else:
                raise ValueError("Grupo não encontrado ou inválido.")
        except (ValueError, IndexError) as e:
            messagebox.showerror("Erro ao Gerar PDF", f"Não foi possível obter os dados do grupo selecionado.\nErro: {e}", parent=self.root)


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
        indices_invalidos = []

        for item_id in selection:
            try:
                index = int(item_id)
                dados = self._preparar_dados_pdf_grupo(index)
                if dados:
                    grupos_pdf.append(dados)
                    nomes_grupos.append(dados['nome_grupo'])
                else:
                    indices_invalidos.append(item_id)
            except (ValueError, IndexError):
                indices_invalidos.append(item_id)

        if not grupos_pdf:
            messagebox.showerror("Erro", "Nenhum grupo válido encontrado na seleção para gerar o PDF.", parent=self.root)
            return

        if indices_invalidos:
             messagebox.showwarning("Aviso", f"Alguns itens selecionados ({len(indices_invalidos)}) não puderam ser processados e foram ignorados.", parent=self.root)

        # Sugere um nome de arquivo baseado nos grupos
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
            messagebox.showerror("Dependência Ausente", "A biblioteca ReportLab é necessária para gerar PDFs.\nInstale com: pip install reportlab", parent=self.root)
            return

        dados_pdf: List[Dict[str, Any]] = []
        grand_total = 0.0

        if grupos_para_pdf:
            # Usar dados dos grupos fornecidos
            dados_pdf = grupos_para_pdf
            grand_total = sum(g.get('total', 0.0) for g in dados_pdf)
        else:
            # Usar dados da calculadora atual
            resultado = self._get_dados_calculadora_atual()
            if resultado is None: # Erro de validação
                return
            itens_calculadora, total_calculadora = resultado
            if not itens_calculadora:
                messagebox.showinfo("Sem Dados", "Não há serviços na calculadora para gerar o PDF.", parent=self.root)
                return
            # Encapsula os dados da calculadora como um único "grupo" para o PDF
            dados_pdf = [{
                'nome_grupo': "Orçamento Atual", # Nome padrão
                'total': total_calculadora,
                'itens': itens_calculadora
            }]
            grand_total = total_calculadora
            nome_arquivo_sugerido = nome_arquivo_sugerido or "Orcamento_Imobiliario.pdf"


        if not dados_pdf:
             messagebox.showerror("Erro Interno", "Não foi possível preparar os dados para o PDF.", parent=self.root)
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

            # Estilo para nome do grupo
            group_title_style = ParagraphStyle(name='GroupTitle', parent=styles['Heading2'], spaceBefore=10, spaceAfter=5, textColor=COR_PRIMARIA)
            total_label_style = ParagraphStyle(name='TotalLabel', parent=styles['Normal'], alignment=2, fontName='Helvetica-Bold') # Alinhado à direita e negrito
            total_value_style = ParagraphStyle(name='TotalValue', parent=styles['Normal'], alignment=2, fontName='Helvetica-Bold') # Alinhado à direita e negrito

            # 1. Cabeçalho da Empresa (Apenas na primeira página por padrão)
            elements.append(Paragraph(self.nome_empresa, styles['h1']))
            elements.append(Paragraph(f"Telefone: {self.telefone_empresa} | E-mail: {self.email_empresa}", styles['Normal']))
            elements.append(Paragraph(f"Endereço: {self.endereco_empresa}", styles['Normal']))
            elements.append(Paragraph(f"Data: {datetime.now().strftime('%d/%m/%Y')}", styles['Normal']))
            elements.append(Spacer(1, 0.8*cm))

            # 2. Título Principal do Documento
            elements.append(Paragraph("Orçamento de Serviços Imobiliários", styles['h2']))
            elements.append(Spacer(1, 0.5*cm))


            # --- Loop através dos grupos ---
            for grupo_data in dados_pdf:
                nome_grupo = grupo_data.get('nome_grupo', 'Itens')
                itens_grupo = grupo_data.get('itens', [])
                total_grupo = grupo_data.get('total', 0.0)

                # Adiciona o nome do grupo como título (se houver mais de um grupo total)
                if len(dados_pdf) > 1:
                     elements.append(Paragraph(f"Grupo: {nome_grupo}", group_title_style))
                     # elements.append(Spacer(1, 0.2*cm)) # Pequeno espaço após título do grupo

                # Tabela de Itens do Grupo
                if itens_grupo:
                    data_table = [['Serviço', 'Locação', 'Descrição', 'Valor']]
                    for item in itens_grupo:
                        valor_fmt = self._formatar_moeda(item.get('valor', 0.0))
                        data_table.append([
                            Paragraph(item.get('servico', '-'), styles['Normal']),
                            Paragraph(item.get('locacao', '-'), styles['Normal']),
                            Paragraph(item.get('descricao', '-'), styles['Normal']),
                            Paragraph(valor_fmt, styles['Normal']) # Usar Paragraph para quebrar linha se necessário
                        ])

                    # Adicionar linha de subtotal do grupo (se houver mais de um grupo)
                    if len(dados_pdf) > 1:
                         data_table.append(['', '', Paragraph('Subtotal do Grupo:', total_label_style), Paragraph(self._formatar_moeda(total_grupo), total_value_style)])

                    # Cria a tabela
                    table = Table(data_table, colWidths=[3.5*cm, 4.5*cm, 6*cm, 3*cm]) # Ajuste as larguras conforme necessário

                    # Estilo da Tabela
                    table_style = TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), COR_PRIMARIA), # Cabeçalho
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 11),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                        ('TOPPADDING', (0, 0), (-1, 0), 8),

                        ('BACKGROUND', (0, 1), (-1, -1), colors.white), # Corpo
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey), # Grid
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), # Alinhamento vertical
                        ('ALIGN', (3, 1), (3, -1), 'RIGHT'), # Coluna Valor alinhada à direita

                        # Estilo para linha de subtotal (se existir)
                        ('BACKGROUND', (0, -1), (-1, -1), COR_SECUNDARIA),
                        ('ALIGN', (2, -1), (2, -1), 'RIGHT'), # Label 'Subtotal'
                        ('ALIGN', (3, -1), (3, -1), 'RIGHT'), # Valor do subtotal
                        ('FONTNAME', (2, -1), (3, -1), 'Helvetica-Bold'),
                        ('BOTTOMPADDING', (0, -1), (-1, -1), 6),
                        ('TOPPADDING', (0, -1), (-1, -1), 6),
                    ])
                    # Remove a grid da linha de subtotal se ela existir e for a última
                    if len(dados_pdf) > 1:
                        table_style.add('GRID', (0, -1), (-1,-1), 0.5, colors.grey) # Mantem grid na linha total
                        # table_style.add('LINEABOVE', (0,-1), (-1,-1), 1, colors.black) # Linha acima do subtotal


                    table.setStyle(table_style)
                    elements.append(table)
                    elements.append(Spacer(1, 0.5*cm))
                else:
                     # Caso um grupo esteja vazio (improvável, mas seguro)
                     if len(dados_pdf) > 1: # Só mostra se for um grupo nomeado
                         elements.append(Paragraph(f"Grupo: {nome_grupo} (Vazio)", group_title_style))
                         elements.append(Spacer(1, 0.3*cm))


            # --- Grand Total (se houver mais de um grupo) ---
            if len(dados_pdf) > 1:
                elements.append(Spacer(1, 0.5*cm))
                total_data = [['', '', Paragraph('VALOR TOTAL GERAL:', total_label_style), Paragraph(self._formatar_moeda(grand_total), total_value_style)]]
                total_table = Table(total_data, colWidths=[3.5*cm, 4.5*cm, 6*cm, 3*cm])
                total_table.setStyle(TableStyle([
                    ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
                    ('ALIGN', (3, 0), (3, 0), 'RIGHT'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('FONTNAME', (2, 0), (3, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (2, 0), (3, 0), 12),
                    ('BACKGROUND', (0, 0), (-1, 0), COR_PRIMARIA),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                     ('TOPPADDING', (0, 0), (-1, -1), 8),
                     ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ]))
                elements.append(total_table)
                elements.append(Spacer(1, 1*cm))


            # --- Rodapé / Observações ---
            elements.append(Paragraph("Observações:", styles['h3']))
            elements.append(Paragraph("1. Valores sujeitos a alteração sem aviso prévio.", styles['Normal']))
            elements.append(Paragraph("2. Validade desta proposta: 30 dias.", styles['Normal']))
            elements.append(Paragraph("3. Condições de pagamento a combinar.", styles['Normal']))
            elements.append(Spacer(1, 2*cm))
            elements.append(Paragraph("_______________________________", styles['Normal']))
            elements.append(Paragraph(self.nome_empresa, styles['Normal']))


            # --- Construir o PDF ---
            doc.build(elements)

            # --- Abrir PDF ---
            if messagebox.askyesno("PDF Gerado", f"PDF '{os.path.basename(file_path)}' gerado com sucesso!\nDeseja abri-lo agora?", parent=self.root):
                self.abrir_arquivo(file_path)

        except PermissionError:
             messagebox.showerror("Erro de Permissão", f"Não foi possível salvar o arquivo em:\n{file_path}\n\nVerifique se o arquivo já está aberto ou se você tem permissão para escrever neste local.", parent=self.root)
        except Exception as e:
            messagebox.showerror("Erro ao Gerar PDF", f"Ocorreu um erro inesperado:\n{str(e)}", parent=self.root)
            import traceback
            print(traceback.format_exc()) # Log completo no console


    def abrir_arquivo(self, file_path: str):
        """Abre um arquivo usando o aplicativo padrão do sistema."""
        try:
            if platform.system() == 'Windows':
                os.startfile(file_path)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.call(('open', file_path))
            else:  # Linux e outros
                subprocess.call(('xdg-open', file_path))
        except Exception as e:
            messagebox.showwarning("Erro ao Abrir", f"Não foi possível abrir o arquivo automaticamente:\n{file_path}\nErro: {e}", parent=self.root)


    # --- Funções de Callback para Scroll ---
    def _on_frame_configure(self, event=None):
        """Atualiza a região de rolagem do canvas quando o frame interno muda de tamanho."""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event=None):
        """Redimensiona o frame interno para preencher a largura do canvas."""
        canvas_width = self.canvas.winfo_width() # Usar winfo_width que é mais confiável aqui
        self.canvas.itemconfig(self.canvas_window, width=canvas_width)
        # Chamar _on_frame_configure pode ser redundante aqui se o tamanho do frame interno não mudou
        # self._on_frame_configure()


    def _on_mousewheel(self, event):
        """Permite rolar a área de entradas com a roda do mouse."""
        if self.canvas.yview() == (0.0, 1.0) and event.delta > 0: # Impede scroll para cima quando já está no topo
             if platform.system() == 'Windows' and self.canvas.yview()[0] == 0.0: return
             if platform.system() != 'Windows' and event.delta > 0 and self.canvas.yview()[0] == 0.0: return


        if platform.system() == 'Windows':
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        elif platform.system() == 'Darwin':  # macOS
             # A sensibilidade pode precisar de ajuste no macOS
             self.canvas.yview_scroll(int(-1 * event.delta), "units")
        else:  # Linux (event.num 4 para cima, 5 para baixo)
            if event.num == 4:
                self.canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                self.canvas.yview_scroll(1, "units")


# --- Inicialização ---
def main():
    root = tk.Tk()
    # Tenta definir um ícone (opcional, requer arquivo .ico ou .png dependendo do SO)
    # try:
    #     # Para Windows:
    #     # root.iconbitmap('path/to/your/icon.ico')
    #     # Para Linux/macOS (usando PhotoImage):
    #     # icon = tk.PhotoImage(file='path/to/your/icon.png')
    #     # root.iconphoto(True, icon)
    #     pass
    # except Exception as e:
    #     print(f"Erro ao definir ícone: {e}")

    app = CalculadoraImobiliaria(root)
    root.mainloop()

if __name__ == "__main__":
    # Verifica se o ReportLab está disponível e avisa se não estiver
    if not REPORTLAB_AVAILABLE:
        root_check = tk.Tk()
        root_check.withdraw() # Esconde a janela principal temporária
        messagebox.showwarning("Dependência Ausente",
                               "A biblioteca 'ReportLab' não foi encontrada.\nA funcionalidade de gerar PDF estará desativada.\n\nPara habilitá-la, instale usando:\npip install reportlab",
                               parent=None) # Mostra antes da janela principal
        root_check.destroy()

    main()