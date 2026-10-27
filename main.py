import json
import re
import tkinter as tk
from tkinter import messagebox
from datetime import datetime, timedelta
from pathlib import Path
from PIL import Image, ImageTk

# CONFIGURAÇÕES


ARQUIVO_AGENDA = Path(__file__).with_name("agenda.json")
BG = "#101010"

SURFACE = "#181818"

CARD = "#1F1F1F"

HOVER = "#292929"

TEXT = "#F4F1EC"

MUTED = "#99938A"

BORDER = "#2B2B2B"

ACCENT = "#C99A5A"

LIGHT = "#E0B77B"

GREEN = "#6FA77B"

DANGER = "#C96B6B"


# Usuários que podem entrar no sistema (troque a senha antes de usar de verdade)

USUARIOS = {
    "admin": "1234",
}


# Programa de fidelidade: a cada N agendamentos, o próximo serviço é grátis

META_FIDELIDADE = 5


SERVICOS = {

    "Corte": {"preco": 35.0, "duracao": "30 min"},

    "Barba": {"preco": 25.0, "duracao": "20 min"},

    "Corte + Barba": {"preco": 55.0, "duracao": "50 min"},

    "Platinado": {"preco": 120.0, "duracao": "90 min"},

}


BARBEIROS = [

    ("João", "Especialista em cortes"),

    ("Pedro", "Corte e barba"),

    ("Lucas", "Especialista em degradê"),

]


HORARIOS = [

    "09:00", "09:30", "10:00", "10:30", "11:00",

    "13:00", "13:30", "14:00", "14:30", "15:00",

    "15:30", "16:00", "16:30", "17:00", "17:30",

    "18:00", "18:30",

]


DIAS_SEMANA = ["SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM"]

MESES = [

    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",

    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",

]


# Dias em que a barbearia fecha (0 = segunda ... 6 = domingo)

DIAS_FECHADOS = {6}


# AGENDA (salva em arquivo JSON)

def carregar_agenda():

    try:

        return json.loads(ARQUIVO_AGENDA.read_text(encoding="utf-8"))

    except (FileNotFoundError, json.JSONDecodeError):

        return []


def salvar_agenda(agenda):

    ARQUIVO_AGENDA.write_text(

        json.dumps(agenda, ensure_ascii=False, indent=2),

        encoding="utf-8",

    )


def novos_dados():

    return {

        "servico": None,

        "barbeiro": None,

        "data": None,

        "horario": None,

        "nome": "",

        "telefone": "",

        "observacao": "",

    }


# APLICATIVO

class BarberFlow(tk.Tk):


    def __init__(self):

        super().__init__()

        self.title("Barber Flow")

        self.geometry("1120x760")

        self.minsize(1000, 700)

        self.configure(bg=BG)


        self.dados = novos_dados()

        self.etapa = 0

        self.usuario = None   # só é preenchido se o cliente fizer login

        self.reserva = None   # última reserva confirmada

        self.mostre_telainicial()


    # Utilidades de interface


    def clear(self):

        for widget in self.winfo_children():

            widget.destroy()


    def button(self, parent, text, command, primary=False):

        return tk.Button(

            parent, text=text, command=command,

            bg=ACCENT if primary else CARD,

            fg="#111111" if primary else TEXT,

            activebackground=LIGHT if primary else HOVER,

            activeforeground="#111111" if primary else TEXT,

            relief="flat", bd=0, cursor="hand2",

            font=("Segoe UI Semibold", 10), padx=22, pady=12,

        )


    def card(self, parent):

        return tk.Frame(parent, bg=CARD, highlightbackground=BORDER,

                        highlightthickness=1)


    def clickable(self, card, command):

        """Torna o card inteiro clicável, com hover sem piscar."""


        widgets = []


        def collect(w):

            widgets.append(w)

            for child in w.winfo_children():

                collect(child)


        collect(card)


        def pintar(cor):

            for w in widgets:

                try:

                    if w.cget("bg") in (CARD, HOVER):

                        w.configure(bg=cor)

                except tk.TclError:

                    pass


        def entrar(_event):

            pintar(HOVER)


        def sair(_event):

            x, y = card.winfo_pointerxy()

            if card.winfo_containing(x, y) in widgets:

                return  # ainda está dentro do card

            pintar(CARD)


        for w in widgets:

            w.bind("<Button-1>", lambda _e: command())

            w.bind("<Enter>", entrar)

            w.bind("<Leave>", sair)

            w.configure(cursor="hand2")


    def selecionar(self, chave, valor, tela):

        self.dados[chave] = valor

        tela()


    def header(self, parent, step, titulo, subtitulo):

        top = tk.Frame(parent, bg=BG)

        top.pack(fill="x")


        tk.Label(top, text="BF", bg=ACCENT, fg="#111111",

                 font=("Segoe UI Black", 12), width=2, pady=4

                 ).pack(side="left")

        tk.Label(top, text="BARBER FLOW", bg=BG, fg=TEXT,

                 font=("Segoe UI Black", 11)).pack(side="left", padx=10)

        tk.Label(top, text=f"{step}/6", bg=BG, fg=MUTED,

                 font=("Segoe UI Semibold", 9)).pack(side="right")


        progress = tk.Frame(parent, bg=BG)

        progress.pack(fill="x", pady=(15, 20))

        for i in range(1, 7):

            tk.Frame(progress, bg=ACCENT if i <= step else BORDER,

                     height=3).pack(side="left", fill="x", expand=True, padx=2)


        tk.Label(parent, text=titulo, bg=BG, fg=TEXT,

                 font=("Segoe UI Semibold", 24)).pack(anchor="w")

        tk.Label(parent, text=subtitulo, bg=BG, fg=MUTED,

                 font=("Segoe UI", 10)).pack(anchor="w", pady=(4, 0))


    def back(self, parent, command):

        tk.Button(

            parent, text="← Voltar", command=command,

            bg=BG, fg=MUTED, activebackground=BG, activeforeground=TEXT,

            relief="flat", bd=0, cursor="hand2", font=("Segoe UI", 9),

        ).pack(anchor="w", pady=(0, 10))


    def page(self, step, titulo, subtitulo, voltar=None,

             texto_btn="Continuar  →", comando=None):

        """

        Monta o esqueleto da página. O rodapé (botão) é empacotado ANTES

        do conteúdo, assim ele nunca fica cortado para fora da janela.

        """

        self.clear()

        self.etapa = step


        area = tk.Frame(self, bg=BG)

        area.pack(fill="both", expand=True, padx=45, pady=25)


        if voltar:

            self.back(area, voltar)


        self.header(area, step, titulo, subtitulo)


        if comando:

            footer = tk.Frame(area, bg=BG)

            footer.pack(side="bottom", fill="x", pady=(10, 0))

            self.button(footer, texto_btn, comando, True).pack(anchor="e")


        content = tk.Frame(area, bg=BG)

        content.pack(fill="both", expand=True, pady=(20, 10))

        return content



    # Login (opcional, depois da reserva confirmada)


    def show_login(self):

        self.clear()


        left = tk.Frame(self, bg=SURFACE, width=500)

        left.pack(side="left", fill="y")

        left.pack_propagate(False)


        brand = tk.Frame(left, bg=SURFACE)

        brand.place(relx=0.5, rely=0.5, anchor="center")


        tk.Label(brand, text="BF", bg=ACCENT, fg="#111111",

                 font=("Segoe UI Black", 25), width=3, height=1

                 ).pack(pady=(0, 25))

        tk.Label(brand, text="BARBER FLOW", bg=SURFACE, fg=TEXT,

                 font=("Segoe UI Black", 25)).pack()

        tk.Label(brand,

                 text="Onde seu estilo ganha forma.",

                 bg=SURFACE, fg=MUTED, font=("Segoe UI", 11),

                 justify="center").pack(pady=(10, 0))

        tk.Frame(brand, bg=ACCENT, height=2, width=45).pack(pady=28)

        tk.Label(brand, text="AGENDA  •  CLIENTES  •  SERVIÇOS",

                 bg=SURFACE, fg="#686868",

                 font=("Segoe UI Semibold", 8)).pack()


        right = tk.Frame(self, bg=BG)

        right.pack(side="right", fill="both", expand=True)


        tk.Button(right, text="← Agora não", command=self.mostrar_sucesso,

                  bg=BG, fg=MUTED, activebackground=BG, activeforeground=TEXT,

                  relief="flat", bd=0, cursor="hand2", font=("Segoe UI", 9)

                  ).place(x=25, y=20, anchor="nw")


        form = tk.Frame(right, bg=BG, width=360)

        form.place(relx=0.5, rely=0.5, anchor="center")


        tk.Label(form, text="Bem-vindo de volta", bg=BG, fg=TEXT,

                 font=("Segoe UI Semibold", 24)).pack(anchor="w")

        tk.Label(form,

                 text="Entre para ver os detalhes da sua reserva\n"

                      "e acompanhar seu programa de fidelidade.",

                 bg=BG, fg=MUTED, font=("Segoe UI", 10), justify="left"

                 ).pack(anchor="w", pady=(6, 35))


        campo = dict(bg="#222222", fg=TEXT, insertbackground=TEXT,

                     relief="flat", bd=0, font=("Segoe UI", 11))


        tk.Label(form, text="USUÁRIO", bg=BG, fg=MUTED,

                 font=("Segoe UI Semibold", 8)).pack(anchor="w", pady=(0, 7))

        username = tk.Entry(form, **campo)

        username.pack(fill="x", ipady=12)


        tk.Label(form, text="SENHA", bg=BG, fg=MUTED,

                 font=("Segoe UI Semibold", 8)).pack(anchor="w", pady=(22, 7))

        password = tk.Entry(form, show="•", **campo)

        password.pack(fill="x", ipady=12)


        erro = tk.Label(form, text="", bg=BG, fg=DANGER,

                        font=("Segoe UI", 9))

        erro.pack(anchor="w", pady=(10, 0))


        def entrar(_event=None):

            if self.login(username.get().strip(), password.get()):

                return

            erro.config(text="Usuário ou senha incorretos.")

            password.delete(0, "end")

            password.focus()


        self.button(form, "ENTRAR", entrar, True).pack(fill="x", pady=(15, 0))


        tk.Label(form, text="Barber Flow • Sistema de gestão", bg=BG,

                 fg="#505050", font=("Segoe UI", 8)).pack(pady=(35, 0))


        username.focus()

        username.bind("<Return>", lambda _e: password.focus())

        password.bind("<Return>", entrar)


    def login(self, usuario, senha):

        """Retorna True se as credenciais estiverem certas."""

        if usuario and USUARIOS.get(usuario) == senha:

            self.usuario = usuario

            self.vincular_reserva()

            self.show_fidelidade()

            return True

        return False


    def logout(self):

        self.usuario = None

        self.reserva = None

        self.dados = novos_dados()

        self.mostre_telainicial()


    def vincular_reserva(self):

        """Associa a reserva recém-feita ao usuário que acabou de entrar."""

        if not self.reserva:

            return

        agenda = carregar_agenda()

        for item in agenda:

            if (item.get("criado_em") == self.reserva["criado_em"]

                    and item.get("telefone") == self.reserva["telefone"]):

                item["usuario"] = self.usuario

        try:

            salvar_agenda(agenda)

        except OSError:

            pass


    # --------------------------------------------------------

    # Tela inicial

    # --------------------------------------------------------


    def mostre_telainicial(self):

        self.clear()

        self.etapa = 0


        left = tk.Frame(self, bg=SURFACE, width=420)

        left.pack(side="left", fill="y")

        left.pack_propagate(False)


        box = tk.Frame(left, bg=SURFACE)

        box.place(relx=0.5, rely=0.5, anchor="center")


        # Logo do Barber Flow
        caminho_logo = Path(__file__).with_name("logo.png")
        logo_carregada = False
        try:
            imagem = Image.open(caminho_logo).convert("RGBA")
            imagem.thumbnail((330, 330), Image.Resampling.LANCZOS)
            self.logo_img = ImageTk.PhotoImage(imagem)
            tk.Label(box, image=self.logo_img, bg=SURFACE, bd=0).pack(pady=(0, 20))
            logo_carregada = True
        except (FileNotFoundError, OSError) as erro:
            # Se a imagem não estiver disponível, mantém o logotipo em texto como alternativa.
            tk.Label(box, text="BF", bg=ACCENT, fg="#111111",
                     font=("Segoe UI Black", 30), width=3).pack(pady=(0, 28))
            print(f"Não foi possível carregar logo.png: {erro}")

        # Só mostra o nome e o slogan em texto quando a imagem não estiver disponível.
        if not logo_carregada:
            tk.Label(box, text="BARBER\nFLOW", bg=SURFACE, fg=TEXT,
                     font=("Segoe UI Black", 31), justify="left").pack(anchor="w")
            tk.Frame(box, bg=ACCENT, height=2, width=45).pack(anchor="w", pady=24)
            tk.Label(box, text="Onde seu estilo ganha forma.",
                     bg=SURFACE, fg=MUTED, font=("Segoe UI", 11),
                     justify="left").pack(anchor="w")


        right = tk.Frame(self, bg=BG)

        right.pack(side="right", fill="both", expand=True)


        box = tk.Frame(right, bg=BG, width=440)

        box.place(relx=0.5, rely=0.5, anchor="center")


        tk.Label(box, text="Agende seu horário", bg=BG, fg=TEXT,

                 font=("Segoe UI Semibold", 28)).pack(anchor="w")

        tk.Label(box,

                 text="Escolha o serviço, profissional e melhor horário\npara você.",

                 bg=BG, fg=MUTED, font=("Segoe UI", 11),

                 justify="left").pack(anchor="w", pady=(8, 35))


        c = self.card(box)

        c.pack(fill="x")

        tk.Label(c, text="ATENDIMENTO RÁPIDO", bg=CARD, fg=ACCENT,

                 font=("Segoe UI Semibold", 8)).pack(anchor="w", padx=20, pady=(18, 5))

        tk.Label(c, text="Escolha seu horário em poucos passos.", bg=CARD,

                 fg=TEXT, font=("Segoe UI Semibold", 12)).pack(anchor="w", padx=20)

        tk.Label(c, text="Sem cadastro complicado.", bg=CARD, fg=MUTED,

                 font=("Segoe UI", 9)).pack(anchor="w", padx=20, pady=(3, 18))


        self.button(box, "COMEÇAR AGENDAMENTO  →", self.show_services,

                    True).pack(fill="x", pady=(25, 0))


    # --------------------------------------------------------

    # 1. Serviços

    # --------------------------------------------------------


    def show_services(self):

        content = self.page(

            1, "Escolha seu serviço",

            "Clique no serviço que deseja realizar.",

            comando=self.next_barber,

        )


        for c in range(2):

            content.grid_columnconfigure(c, weight=1, uniform="col")

        for r in range(2):

            content.grid_rowconfigure(r, weight=1, uniform="row")


        for i, (nome, info) in enumerate(SERVICOS.items()):

            sel = self.dados["servico"] == nome


            card = tk.Frame(

                content, bg=CARD,

                highlightbackground=ACCENT if sel else BORDER,

                highlightthickness=2 if sel else 1,

            )

            card.grid(row=i // 2, column=i % 2, sticky="nsew", padx=8, pady=8)


            topo = tk.Frame(card, bg=CARD)

            topo.pack(fill="x", padx=22, pady=(14, 0))

            tk.Label(topo, text="✂", bg=CARD, fg=ACCENT,

                     font=("Segoe UI", 20)).pack(side="left")

            if sel:

                tk.Label(topo, text="✓ SELECIONADO", bg=CARD, fg=GREEN,

                         font=("Segoe UI Semibold", 8)).pack(side="right")


            tk.Label(card, text=nome, bg=CARD, fg=TEXT,

                     font=("Segoe UI Semibold", 15)).pack(anchor="w", padx=22)

            tk.Label(card, text=f"R$ {info['preco']:.2f}".replace(".", ","),

                     bg=CARD, fg=ACCENT,

                     font=("Segoe UI Black", 18)).pack(anchor="w", padx=22, pady=(6, 0))

            tk.Label(card, text=f"Duração aproximada: {info['duracao']}",

                     bg=CARD, fg=MUTED,

                     font=("Segoe UI", 9)).pack(anchor="w", padx=22, pady=(0, 14))


            self.clickable(

                card,

                lambda n=nome: self.selecionar("servico", n, self.show_services),

            )


    def next_barber(self):

        if not self.dados["servico"]:

            messagebox.showwarning("Escolha um serviço",

                                   "Selecione um serviço antes de continuar.")

            return

        self.show_barbers()


    # --------------------------------------------------------

    # 2. Barbeiros

    # --------------------------------------------------------


    def show_barbers(self):

        content = self.page(

            2, "Escolha o profissional",

            "Quem você prefere para realizar seu atendimento?",

            voltar=self.show_services, comando=self.next_date,

        )


        for i, (nome, descricao) in enumerate(BARBEIROS):

            content.grid_columnconfigure(i, weight=1, uniform="col")

            sel = self.dados["barbeiro"] == nome


            card = tk.Frame(

                content, bg=CARD,

                highlightbackground=ACCENT if sel else BORDER,

                highlightthickness=2 if sel else 1,

            )

            card.grid(row=0, column=i, sticky="nsew", padx=6)


            tk.Label(card, text=nome[0], bg="#302719", fg=LIGHT,

                     font=("Segoe UI Black", 24), width=3

                     ).pack(pady=(30, 20))

            tk.Label(card, text=nome, bg=CARD, fg=TEXT,

                     font=("Segoe UI Semibold", 14)).pack(pady=5)

            tk.Label(card, text=descricao, bg=CARD, fg=MUTED,

                     font=("Segoe UI", 9)).pack(pady=(5, 10))

            tk.Label(card, text="✓ SELECIONADO" if sel else " ", bg=CARD,

                     fg=GREEN, font=("Segoe UI Semibold", 8)

                     ).pack(pady=(0, 25))


            self.clickable(

                card,

                lambda n=nome: self.selecionar("barbeiro", n, self.show_barbers),

            )


    def next_date(self):

        if not self.dados["barbeiro"]:

            messagebox.showwarning("Escolha um profissional",

                                   "Selecione um barbeiro antes de continuar.")

            return

        self.show_date()


    # --------------------------------------------------------

    # 3. Data

    # --------------------------------------------------------


    def show_date(self):

        content = self.page(

            3, "Escolha a data",

            "Selecione o dia em que deseja ser atendido.",

            voltar=self.show_barbers, comando=self.next_time,

        )


        card = self.card(content)

        card.pack(fill="both", expand=True)


        hoje = datetime.now().date()

        fim = hoje + timedelta(days=13)


        if hoje.month == fim.month:

            titulo_mes = f"{MESES[hoje.month - 1]} {hoje.year}"

        else:

            titulo_mes = (f"{MESES[hoje.month - 1]} / "

                          f"{MESES[fim.month - 1]} {fim.year}")


        tk.Label(card, text=titulo_mes, bg=CARD, fg=TEXT,

                 font=("Segoe UI Semibold", 16)).pack(pady=(25, 15))


        grid = tk.Frame(card, bg=CARD)

        grid.pack()


        for i in range(14):

            data = hoje + timedelta(days=i)

            fechado = data.weekday() in DIAS_FECHADOS

            sel = self.dados["data"] == data


            bg = ACCENT if sel else ("#171717" if fechado else "#252525")

            fg = "#111111" if sel else ("#555555" if fechado else TEXT)


            tk.Button(

                grid,

                text=f"{data.day:02d}\n{DIAS_SEMANA[data.weekday()]}",

                command=lambda d=data: self.pick_date(d),

                bg=bg, fg=fg, activebackground=LIGHT,

                relief="flat", bd=0,

                cursor="arrow" if fechado else "hand2",

                font=("Segoe UI Semibold", 10), width=7, height=3,

                state="disabled" if fechado else "normal",

            ).grid(row=i // 7, column=i % 7, padx=4, pady=4)


        tk.Label(card, text="Domingo: fechado", bg=CARD, fg=MUTED,

                 font=("Segoe UI", 9)).pack(pady=(15, 0))


    def pick_date(self, data):

        if self.dados["data"] != data:

            self.dados["horario"] = None  # horário antigo pode não valer

        self.dados["data"] = data

        self.show_date()


    def next_time(self):

        if not self.dados["data"]:

            messagebox.showwarning("Escolha uma data",

                                   "Selecione uma data antes de continuar.")

            return

        self.show_times()


    # --------------------------------------------------------

    # 4. Horários

    # --------------------------------------------------------


    def horarios_ocupados(self):

        data = self.dados["data"].isoformat()

        return {

            a["horario"] for a in carregar_agenda()

            if a["barbeiro"] == self.dados["barbeiro"] and a["data"] == data

        }


    def show_times(self):

        content = self.page(

            4, "Escolha o horário",

            f"Horários de {self.dados['barbeiro']} em "

            f"{self.dados['data'].strftime('%d/%m/%Y')}.",

            voltar=self.show_date, comando=self.next_data,

        )


        ocupados = self.horarios_ocupados()

        agora = datetime.now()

        hoje = agora.date()

        hora_atual = agora.strftime("%H:%M")


        def indisponivel(h):

            passou = self.dados["data"] == hoje and h <= hora_atual

            return h in ocupados, passou


        # Se o horário escolhido deixou de estar livre, limpa

        if self.dados["horario"] and any(indisponivel(self.dados["horario"])):

            self.dados["horario"] = None


        colunas = 5

        for c in range(colunas):

            content.grid_columnconfigure(c, weight=1, uniform="col")


        for i, h in enumerate(HORARIOS):

            ocupado, passou = indisponivel(h)

            bloqueado = ocupado or passou

            sel = self.dados["horario"] == h


            if ocupado:

                texto = f"{h}\nocupado"

            elif passou:

                texto = f"{h}\nencerrado"

            else:

                texto = h


            tk.Button(

                content, text=texto,

                command=lambda x=h: self.pick_time(x),

                bg=ACCENT if sel else ("#171717" if bloqueado else CARD),

                fg="#111111" if sel else ("#555555" if bloqueado else TEXT),

                activebackground=LIGHT, relief="flat", bd=0,

                cursor="arrow" if bloqueado else "hand2",

                font=("Segoe UI Semibold", 10), height=2,

                state="disabled" if bloqueado else "normal",

            ).grid(row=i // colunas, column=i % colunas,

                   sticky="ew", padx=5, pady=5)


    def pick_time(self, horario):

        self.dados["horario"] = horario

        self.show_times()


    def next_data(self):

        if not self.dados["horario"]:

            messagebox.showwarning("Escolha um horário",

                                   "Selecione um horário antes de continuar.")

            return

        self.show_data()


    # --------------------------------------------------------

    # 5. Dados do cliente

    # --------------------------------------------------------


    def label_entry(self, parent, label, entry, value="", top=0):

        tk.Label(parent, text=label, bg=BG, fg=MUTED,

                 font=("Segoe UI Semibold", 8)).pack(anchor="w", pady=(top, 7))

        entry.pack(fill="x", ipady=13)

        entry.insert(0, value)

# DADOS DE CONFIRMAÇÃO DO CLIENTE
    def show_data(self):

        content = self.page(

            5, "Seus dados",

            "Precisamos de algumas informações para confirmar o atendimento.",

            voltar=self.show_times, texto_btn="Revisar agendamento  →",

            comando=self.review,

        )


        left = tk.Frame(content, bg=BG)

        left.pack(side="left", fill="both", expand=True, padx=(0, 15))

        right = tk.Frame(content, bg=BG)

        right.pack(side="right", fill="both", expand=True, padx=(15, 0))


        estilo = dict(bg="#202020", fg=TEXT, insertbackground=TEXT,

                      relief="flat", bd=0, font=("Segoe UI", 11))


        self.nome = tk.Entry(left, **estilo)

        self.label_entry(left, "NOME COMPLETO", self.nome, self.dados["nome"])


        self.telefone = tk.Entry(left, **estilo)

        self.label_entry(left, "WHATSAPP / TELEFONE (com DDD)",

                         self.telefone, self.dados["telefone"], 25)


        tk.Label(right, text="OBSERVAÇÕES (OPCIONAL)", bg=BG, fg=MUTED,

                 font=("Segoe UI Semibold", 8)).pack(anchor="w", pady=(0, 7))


        self.obs = tk.Text(right, bg="#202020", fg=TEXT, insertbackground=TEXT,

                           relief="flat", bd=0, font=("Segoe UI", 10),

                           height=8, wrap="word")

        self.obs.pack(fill="both", expand=True)

        if self.dados["observacao"]:

            self.obs.insert("1.0", self.dados["observacao"])


        self.nome.focus()

# REVISAO DOS DADOS DO CLIENTE
    def review(self):

        nome = self.nome.get().strip()

        telefone = self.telefone.get().strip()

        digitos = re.sub(r"\D", "", telefone)


        if len(nome) < 3:

            messagebox.showwarning("Nome necessário",

                                   "Informe seu nome completo.")

            self.nome.focus()

            return


        if len(digitos) not in (10, 11):

            messagebox.showwarning(

                "Telefone inválido",

                "Informe o telefone com DDD, por exemplo: (11) 91234-5678.")

            self.telefone.focus()

            return


        self.dados["nome"] = nome

        self.dados["telefone"] = telefone

        self.dados["observacao"] = self.obs.get("1.0", "end").strip()

        self.show_confirm()

    # 6. Confirmação


    def show_confirm(self):

        content = self.page(

            6, "Confirme seu agendamento",

            "Confira os dados antes de finalizar.",

            voltar=self.show_data, texto_btn="CONFIRMAR AGENDAMENTO  ✓",

            comando=self.finish,

        )


        card = self.card(content)

        card.pack(fill="both", expand=True)


        top = tk.Frame(card, bg=CARD)

        top.pack(fill="x", padx=25, pady=(22, 10))


        tk.Label(top, text=self.dados["servico"], bg=CARD, fg=TEXT,

                 font=("Segoe UI Semibold", 17)).pack(side="left")

        preco = SERVICOS[self.dados["servico"]]["preco"]

        tk.Label(top, text=f"R$ {preco:.2f}".replace(".", ","), bg=CARD,

                 fg=ACCENT, font=("Segoe UI Black", 17)).pack(side="right")


        tk.Frame(card, bg=BORDER, height=1).pack(fill="x", padx=25)


        info = tk.Frame(card, bg=CARD)

        info.pack(fill="both", expand=True, padx=25, pady=15)


        valores = [

            ("PROFISSIONAL", self.dados["barbeiro"]),

            ("DATA", self.dados["data"].strftime("%d/%m/%Y")),

            ("HORÁRIO", self.dados["horario"]),

            ("CLIENTE", self.dados["nome"]),

            ("WHATSAPP", self.dados["telefone"]),

        ]

        if self.dados["observacao"]:

            valores.append(("OBSERVAÇÃO", self.dados["observacao"]))


        for titulo, valor in valores:

            row = tk.Frame(info, bg=CARD)

            row.pack(fill="x", pady=6)

            tk.Label(row, text=titulo, bg=CARD, fg=MUTED,

                     font=("Segoe UI Semibold", 8), width=15,

                     anchor="w").pack(side="left")

            tk.Label(row, text=valor, bg=CARD, fg=TEXT,

                     font=("Segoe UI Semibold", 10), anchor="w",

                     justify="left", wraplength=500).pack(side="left")


    # --------------------------------------------------------

    # Finalizar

    # --------------------------------------------------------


    def finish(self):

        # Confere de novo: alguém pode ter ocupado o horário

        if self.dados["horario"] in self.horarios_ocupados():

            messagebox.showwarning(

                "Horário indisponível",

                "Esse horário acabou de ser reservado. Escolha outro.")

            self.dados["horario"] = None

            self.show_times()

            return


        agenda = carregar_agenda()

        reserva = {

            "servico": self.dados["servico"],

            "barbeiro": self.dados["barbeiro"],

            "data": self.dados["data"].isoformat(),

            "horario": self.dados["horario"],

            "nome": self.dados["nome"],

            "telefone": self.dados["telefone"],

            "observacao": self.dados["observacao"],

            "criado_em": datetime.now().isoformat(timespec="seconds"),

            "usuario": self.usuario,

        }

        agenda.append(reserva)


        try:

            salvar_agenda(agenda)

        except OSError as erro:

            messagebox.showerror("Erro ao salvar",

                                 f"Não foi possível salvar o agendamento:\n{erro}")

            return


        self.reserva = reserva

        self.mostrar_sucesso()


    def mostrar_sucesso(self):

        # Quem já fez login vai direto para os detalhes e a fidelidade

        if self.usuario:

            self.mostrar_fidelidade()

            return


        self.clear()


        box = tk.Frame(self, bg=BG)

        box.place(relx=0.5, rely=0.5, anchor="center")


        tk.Label(box, text="✓", bg="#26352A", fg=GREEN,

                 font=("Segoe UI Black", 32), width=3).pack(pady=(0, 25))

        tk.Label(box, text="Agendamento confirmado!", bg=BG, fg=TEXT,

                 font=("Segoe UI Semibold", 26)).pack()


        mensagem = (

            f"{self.dados['nome']}, seu horário está reservado.\n\n"

            f"{self.dados['data'].strftime('%d/%m/%Y')} "

            f"às {self.dados['horario']}\n"

            f"{self.dados['servico']} com {self.dados['barbeiro']}"

        )

        tk.Label(box, text=mensagem, bg=BG, fg=MUTED, font=("Segoe UI", 11),

                 justify="center").pack(pady=(12, 25))


        # Pergunta opcional sobre o login

        pergunta = self.card(box)

        pergunta.pack(fill="x", pady=(0, 15))


        tk.Label(pergunta, text="FIDELIDADE", bg=CARD, fg=ACCENT,

                 font=("Segoe UI Semibold", 8)

                 ).pack(anchor="w", padx=20, pady=(16, 4))

        tk.Label(pergunta,

                 text="Você deseja fazer o login para receber mais detalhes "

                      "e serviços de fidelidade?",

                 bg=CARD, fg=TEXT, font=("Segoe UI Semibold", 11),

                 wraplength=400, justify="left"

                 ).pack(anchor="w", padx=20)


        botoes = tk.Frame(pergunta, bg=CARD)

        botoes.pack(fill="x", padx=20, pady=(14, 18))

        botoes.grid_columnconfigure(0, weight=1, uniform="b")

        botoes.grid_columnconfigure(1, weight=1, uniform="b")


        self.button(botoes, "SIM, FAZER LOGIN", self.show_login,

                    True).grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.button(botoes, "AGORA NÃO", pergunta.destroy

                    ).grid(row=0, column=1, sticky="ew", padx=(6, 0))


        self.button(box, "NOVO AGENDAMENTO", self.reset

                    ).pack(fill="x")


    def mostrar_fidelidade(self):

        """Detalhes da reserva + programa de fidelidade (usuário logado)."""

        self.clear()


        box = tk.Frame(self, bg=BG)

        box.place(relx=0.5, rely=0.5, anchor="center")


        tk.Label(box, text="✓", bg="#26352A", fg=GREEN,

                 font=("Segoe UI Black", 22), width=3

                 ).pack(pady=(0, 14))

        tk.Label(box, text=f"Tudo certo, {self.usuario}!", bg=BG, fg=TEXT,

                 font=("Segoe UI Semibold", 24)).pack()

        tk.Label(box, text="Sua reserva está confirmada.", bg=BG, fg=MUTED,

                 font=("Segoe UI", 10)).pack(pady=(4, 18))


        # Detalhes da reserva

        detalhes = self.card(box)

        detalhes.pack(fill="x")


        preco = SERVICOS[self.dados["servico"]]["preco"]

        duracao = SERVICOS[self.dados["servico"]]["duracao"]

        linhas = [

            ("SERVIÇO", f"{self.dados['servico']}  ({duracao})"),

            ("PROFISSIONAL", self.dados["barbeiro"]),

            ("DATA", self.dados["data"].strftime("%d/%m/%Y")),

            ("HORÁRIO", self.dados["horario"]),

            ("VALOR", f"R$ {preco:.2f}".replace(".", ",")),

        ]

        for titulo, valor in linhas:

            row = tk.Frame(detalhes, bg=CARD)

            row.pack(fill="x", padx=22, pady=5)

            tk.Label(row, text=titulo, bg=CARD, fg=MUTED,

                     font=("Segoe UI Semibold", 8), width=14,

                     anchor="w").pack(side="left")

            tk.Label(row, text=valor, bg=CARD, fg=TEXT,

                     font=("Segoe UI Semibold", 10),

                     anchor="w").pack(side="left")

        tk.Label(detalhes, text="Chegue com 10 minutos de antecedência.",

                 bg=CARD, fg=MUTED, font=("Segoe UI", 9)

                 ).pack(anchor="w", padx=22, pady=(6, 14))


        # Programa de fidelidade

        total = sum(1 for a in carregar_agenda()

                    if a.get("usuario") == self.usuario)

        progresso = total % META_FIDELIDADE

        if total > 0 and progresso == 0:

            progresso = META_FIDELIDADE

            msg = "Meta atingida! Seu próximo serviço é por conta da casa."

        else:

            falta = META_FIDELIDADE - progresso

            msg = (f"Falta {falta} agendamento para ganhar um serviço grátis."

                   if falta == 1 else

                   f"Faltam {falta} agendamentos para ganhar um serviço grátis.")


        fid = self.card(box)

        fid.pack(fill="x", pady=(12, 0))


        topo = tk.Frame(fid, bg=CARD)

        topo.pack(fill="x", padx=22, pady=(16, 8))

        tk.Label(topo, text="PROGRAMA DE FIDELIDADE", bg=CARD, fg=ACCENT,

                 font=("Segoe UI Semibold", 8)).pack(side="left")

        tk.Label(topo, text=f"{progresso}/{META_FIDELIDADE}", bg=CARD,

                 fg=TEXT, font=("Segoe UI Semibold", 9)).pack(side="right")


        barra = tk.Frame(fid, bg=CARD)

        barra.pack(fill="x", padx=22)

        for i in range(META_FIDELIDADE):

            tk.Frame(barra, bg=ACCENT if i < progresso else BORDER,

                     height=8).pack(side="left", fill="x", expand=True, padx=2)


        tk.Label(fid, text=msg, bg=CARD, fg=MUTED, font=("Segoe UI", 9)

                 ).pack(anchor="w", padx=22, pady=(10, 16))


        self.button(box, "NOVO AGENDAMENTO", self.reset,

                    True).pack(fill="x", pady=(18, 0))

        tk.Button(box, text="Sair da conta", command=self.logout, bg=BG,

                  fg=MUTED, activebackground=BG, activeforeground=TEXT,

                  relief="flat", bd=0, cursor="hand2", font=("Segoe UI", 9)

                  ).pack(pady=(10, 0))


    def reset(self):

        self.dados = novos_dados()

        self.reserva = None

        self.show_services()


if __name__ == "__main__":

    BarberFlow().mainloop()
