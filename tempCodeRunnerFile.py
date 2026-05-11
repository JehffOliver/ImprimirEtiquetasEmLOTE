# -*- coding: utf-8 -*-
# Gerador de Etiquetas Zebra 100x40 - Interface com Abas
#
# Requisitos:
#   pip install pywin32

import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import random
import string
from datetime import datetime

try:
    import win32print
except ImportError:
    win32print = None

CONFIG_IMPRESSORA_ARQ = "config_impressora.json"
CONFIG_LAYOUT_ARQ = "config_layout_zebra.json"

DPI = 203
LARGURA_MM = 100
ALTURA_MM = 40

def mm_to_dots(mm, dpi=DPI):
    return int(round(mm * dpi / 25.4))

LABEL_WIDTH = mm_to_dots(LARGURA_MM)
LABEL_HEIGHT = mm_to_dots(ALTURA_MM)

PADRAO_IMPRESSORA = {
    "impressora_padrao": ""
}

PADRAO_LAYOUT = {
    "descricao_x": 20,
    "descricao_y": 18,
    "descricao_font": 22,

    "lote_x": 20,
    "lote_y": 92,
    "lote_font": 18,

    "volume_x": 20,
    "volume_y": 126,
    "volume_font": 24,

    "qr_x": 610,
    "qr_y": 28,
    "qr_magnification": 4,

    "linha2_offset_y": 24,
    "orientacao": "N"
}

# ==========================================================
# JSON
# ==========================================================
def garantir_json(nome, padrao):
    if not os.path.exists(nome):
        with open(nome, "w", encoding="utf-8") as f:
            json.dump(padrao, f, indent=4, ensure_ascii=False)

    try:
        with open(nome, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}

    alterado = False
    for k, v in padrao.items():
        if k not in data:
            data[k] = v
            alterado = True

    if alterado:
        with open(nome, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    return data

def salvar_configuracao(arquivo, dados):
    with open(arquivo, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

CONFIG_IMPRESSORA = garantir_json(CONFIG_IMPRESSORA_ARQ, PADRAO_IMPRESSORA)
CONFIG_LAYOUT = garantir_json(CONFIG_LAYOUT_ARQ, PADRAO_LAYOUT)

# ==========================================================
# UTILS
# ==========================================================
def ensure_os_prefix(lote_str: str) -> str:
    s = lote_str.strip().upper()
    if s.startswith("OS"):
        return s
    return "OS" + s

def gerar_chave_unica():
    dt = datetime.now().strftime("%Y%m%d")
    rand = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"{dt}{rand}"

def zpl_escape(texto: str) -> str:
    if texto is None:
        return ""
    return str(texto).replace("^", " ").replace("~", " ").replace("\r", " ").replace("\n", " ")

def quebrar_texto(texto, tamanho_max_linha=32, max_linhas=2):
    palavras = texto.split()
    linhas = []
    atual = ""

    for palavra in palavras:
        teste = (atual + " " + palavra).strip()
        if len(teste) <= tamanho_max_linha:
            atual = teste
        else:
            if atual:
                linhas.append(atual)
            atual = palavra
            if len(linhas) >= max_linhas:
                break

    if atual and len(linhas) < max_linhas:
        linhas.append(atual)

    return linhas[:max_linhas]

# ==========================================================
# IMPRESSORAS
# ==========================================================
def listar_impressoras():
    if win32print is None:
        return []

    nomes = []
    flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
    try:
        impressoras = win32print.EnumPrinters(flags)
        for item in impressoras:
            if len(item) >= 3 and isinstance(item[2], str) and item[2].strip():
                nomes.append(item[2].strip())
    except Exception as e:
        print("Erro ao listar impressoras:", e)

    return sorted(list(set(nomes)))

def obter_impressora_padrao_windows():
    if win32print is None:
        return ""
    try:
        return win32print.GetDefaultPrinter()
    except Exception:
        return ""

def imprimir_zpl_na_impressora(nome_impressora, zpl):
    if win32print is None:
        raise RuntimeError("pywin32 não está instalado. Rode: pip install pywin32")

    if not nome_impressora:
        raise ValueError("Nenhuma impressora selecionada.")

    hprinter = None
    try:
        hprinter = win32print.OpenPrinter(nome_impressora)
        win32print.StartDocPrinter(hprinter, 1, ("Etiqueta Zebra", None, "RAW"))
        win32print.StartPagePrinter(hprinter)
        win32print.WritePrinter(hprinter, zpl.encode("utf-8"))
        win32print.EndPagePrinter(hprinter)
        win32print.EndDocPrinter(hprinter)
    finally:
        if hprinter:
            win32print.ClosePrinter(hprinter)

# ==========================================================
# ZPL
# ==========================================================
def gerar_zpl_uma_etiqueta(codigo, descricao, lote, volume_atual, volume_total):
    codigo = zpl_escape(codigo)
    descricao = zpl_escape(descricao)
    lote = zpl_escape(ensure_os_prefix(lote))
    volume_atual = zpl_escape(str(volume_atual))
    volume_total = zpl_escape(str(volume_total))
    chave = gerar_chave_unica()

    qr_payload = f"{codigo}|{lote}|{descricao}|{volume_atual}|{volume_total}|{chave}"

    texto_topo = f"{codigo} / {descricao}" if descricao else codigo
    linhas_desc = quebrar_texto(texto_topo, tamanho_max_linha=32, max_linhas=2)

    linha1 = linhas_desc[0] if len(linhas_desc) > 0 else ""
    linha2 = linhas_desc[1] if len(linhas_desc) > 1 else ""

    txt_lote = f"Lote: {lote}"
    txt_vol = f"Volume {volume_atual}/{volume_total}"

    desc_x = int(CONFIG_LAYOUT["descricao_x"])
    desc_y = int(CONFIG_LAYOUT["descricao_y"])
    desc_font = int(CONFIG_LAYOUT["descricao_font"])

    lote_x = int(CONFIG_LAYOUT["lote_x"])
    lote_y = int(CONFIG_LAYOUT["lote_y"])
    lote_font = int(CONFIG_LAYOUT["lote_font"])

    vol_x = int(CONFIG_LAYOUT["volume_x"])
    vol_y = int(CONFIG_LAYOUT["volume_y"])
    vol_font = int(CONFIG_LAYOUT["volume_font"])

    qr_x = int(CONFIG_LAYOUT["qr_x"])
    qr_y = int(CONFIG_LAYOUT["qr_y"])
    qr_m = int(CONFIG_LAYOUT["qr_magnification"])

    linha2_offset = int(CONFIG_LAYOUT["linha2_offset_y"])
    orient = CONFIG_LAYOUT.get("orientacao", "N")

    zpl = f"""
^XA
^PW{LABEL_WIDTH}
^LL{LABEL_HEIGHT}
^LH0,0
^CI28
^FWN
^FO{desc_x},{desc_y}^A0{orient},{desc_font},{desc_font}^FD{linha1}^FS
"""

    if linha2:
        zpl += f"^FO{desc_x},{desc_y + linha2_offset}^A0{orient},{desc_font},{desc_font}^FD{linha2}^FS\n"

    zpl += f"""
^FO{lote_x},{lote_y}^A0{orient},{lote_font},{lote_font}^FD{txt_lote}^FS
^FO{vol_x},{vol_y}^A0{orient},{vol_font},{vol_font}^FD{txt_vol}^FS
^FO{qr_x},{qr_y}^BQN,2,{qr_m}
^FDLA,{qr_payload}^FS
^XZ
"""
    return zpl.strip() + "\n"

def gerar_zpl_lote(dados, quantidade):
    lote = dados["lote"].strip()
    codigo = dados["codigo_produto"].strip()
    descricao = dados["descricao"].strip()

    total_volumes = int(dados["total_volumes"])
    if total_volumes <= 0:
        raise ValueError("Volume total deve ser maior que zero.")

    if quantidade <= 0:
        raise ValueError("Quantidade deve ser maior que zero.")

    if quantidade > total_volumes:
        raise ValueError("Quantidade de etiquetas não pode ser maior que o volume total.")

    etiquetas = []
    for contador in range(1, quantidade + 1):
        etiquetas.append(
            gerar_zpl_uma_etiqueta(
                codigo=codigo,
                descricao=descricao,
                lote=lote,
                volume_atual=contador,
                volume_total=total_volumes,
            )
        )
    return "\n".join(etiquetas)

# ==========================================================
# DADOS
# ==========================================================
def coletar_dados():
    return {
        "lote": entry_lote.get(),
        "codigo_produto": entry_codigo.get(),
        "descricao": text_desc.get("1.0", tk.END).strip(),
        "total_volumes": entry_volume_total.get(),
        "quantidade": entry_quantidade.get()
    }

def validar_dados(dados):
    if not dados["lote"]:
        return "Preencha o lote."
    if not dados["codigo_produto"]:
        return "Preencha o código do produto."
    if not dados["descricao"]:
        return "Preencha a descrição."
    if not dados["total_volumes"]:
        return "Preencha o volume total."
    if not dados["quantidade"]:
        return "Preencha a quantidade de etiquetas."

    try:
        total = int(dados["total_volumes"])
        if total <= 0:
            return "Volume total deve ser maior que zero."
    except Exception:
        return "Volume total inválido."

    try:
        qtd = int(dados["quantidade"])
        if qtd <= 0:
            return "Quantidade deve ser maior que zero."
    except Exception:
        return "Quantidade inválida."

    if qtd > total:
        return "A quantidade de etiquetas não pode ser maior que o volume total."

    return None

# ==========================================================
# PREVIEW
# ==========================================================
PREVIEW_SCALE = 0.5

def dots_to_canvas(v):
    return int(v * PREVIEW_SCALE)

def desenhar_previa():
    canvas_preview.delete("all")

    largura = dots_to_canvas(LABEL_WIDTH)
    altura = dots_to_canvas(LABEL_HEIGHT)

    x0 = 20
    y0 = 20
    x1 = x0 + largura
    y1 = y0 + altura

    canvas_preview.create_rectangle(x0, y0, x1, y1, fill="white", outline="#222", width=2)
    canvas_preview.create_text((x0 + x1)//2, 8, text="Prévia da Etiqueta 100x40", font=("Segoe UI", 10, "bold"))

    dados = coletar_dados()
    codigo = dados["codigo_produto"].strip() or "132483"
    descricao = dados["descricao"].strip() or "Descrição do produto"
    lote = ensure_os_prefix(dados["lote"].strip() or "25-000000")

    try:
        total = int(dados["total_volumes"])
    except Exception:
        total = 10

    texto_topo = f"{codigo} / {descricao}"
    linhas_desc = quebrar_texto(texto_topo, tamanho_max_linha=32, max_linhas=2)

    desc_x = x0 + dots_to_canvas(int(CONFIG_LAYOUT["descricao_x"]))
    desc_y = y0 + dots_to_canvas(int(CONFIG_LAYOUT["descricao_y"]))
    desc_font = max(8, int(CONFIG_LAYOUT["descricao_font"] * 0.42))

    lote_x = x0 + dots_to_canvas(int(CONFIG_LAYOUT["lote_x"]))
    lote_y = y0 + dots_to_canvas(int(CONFIG_LAYOUT["lote_y"]))
    lote_font = max(8, int(CONFIG_LAYOUT["lote_font"] * 0.42))

    vol_x = x0 + dots_to_canvas(int(CONFIG_LAYOUT["volume_x"]))
    vol_y = y0 + dots_to_canvas(int(CONFIG_LAYOUT["volume_y"]))
    vol_font = max(8, int(CONFIG_LAYOUT["volume_font"] * 0.42))

    qr_x = x0 + dots_to_canvas(int(CONFIG_LAYOUT["qr_x"]))
    qr_y = y0 + dots_to_canvas(int(CONFIG_LAYOUT["qr_y"]))
    qr_size = max(42, int(CONFIG_LAYOUT["qr_magnification"]) * 16)

    linha2_offset = dots_to_canvas(int(CONFIG_LAYOUT["linha2_offset_y"]))

    if len(linhas_desc) > 0:
        canvas_preview.create_text(desc_x, desc_y, anchor="nw", text=linhas_desc[0], font=("Segoe UI", desc_font, "bold"))
    if len(linhas_desc) > 1:
        canvas_preview.create_text(desc_x, desc_y + linha2_offset, anchor="nw", text=linhas_desc[1], font=("Segoe UI", desc_font, "bold"))

    canvas_preview.create_text(lote_x, lote_y, anchor="nw", text=f"Lote: {lote}", font=("Segoe UI", lote_font))
    canvas_preview.create_text(vol_x, vol_y, anchor="nw", text=f"Volume 1/{total}", font=("Segoe UI", vol_font, "bold"))

    canvas_preview.create_rectangle(qr_x, qr_y, qr_x + qr_size, qr_y + qr_size, outline="#222", width=2)
    canvas_preview.create_text(qr_x + qr_size // 2, qr_y + qr_size // 2, text="QR", font=("Segoe UI", 10, "bold"))

# ==========================================================
# LAYOUT / SLIDERS
# ==========================================================
def atualizar_layout_de_sliders(*args):
    CONFIG_LAYOUT["descricao_x"] = int(scale_desc_x.get())
    CONFIG_LAYOUT["descricao_y"] = int(scale_desc_y.get())
    CONFIG_LAYOUT["descricao_font"] = int(scale_desc_font.get())

    CONFIG_LAYOUT["lote_x"] = int(scale_lote_x.get())
    CONFIG_LAYOUT["lote_y"] = int(scale_lote_y.get())
    CONFIG_LAYOUT["lote_font"] = int(scale_lote_font.get())

    CONFIG_LAYOUT["volume_x"] = int(scale_vol_x.get())
    CONFIG_LAYOUT["volume_y"] = int(scale_vol_y.get())
    CONFIG_LAYOUT["volume_font"] = int(scale_vol_font.get())

    CONFIG_LAYOUT["qr_x"] = int(scale_qr_x.get())
    CONFIG_LAYOUT["qr_y"] = int(scale_qr_y.get())
    CONFIG_LAYOUT["qr_magnification"] = int(scale_qr_m.get())

    CONFIG_LAYOUT["linha2_offset_y"] = int(scale_linha2.get())
    CONFIG_LAYOUT["orientacao"] = combo_orientacao.get()

    atualizar_labels_sliders()
    desenhar_previa()

def atualizar_labels_sliders():
    labels = [
        (lbl_desc_x, scale_desc_x), (lbl_desc_y, scale_desc_y), (lbl_desc_font, scale_desc_font),
        (lbl_lote_x, scale_lote_x), (lbl_lote_y, scale_lote_y), (lbl_lote_font, scale_lote_font),
        (lbl_vol_x, scale_vol_x), (lbl_vol_y, scale_vol_y), (lbl_vol_font, scale_vol_font),
        (lbl_qr_x, scale_qr_x), (lbl_qr_y, scale_qr_y), (lbl_qr_m, scale_qr_m),
        (lbl_linha2, scale_linha2)
    ]
    for lbl, scl in labels:
        lbl.config(text=str(int(scl.get())))

def salvar_layout():
    atualizar_layout_de_sliders()
    salvar_configuracao(CONFIG_LAYOUT_ARQ, CONFIG_LAYOUT)
    messagebox.showinfo("Sucesso", "Layout salvo com sucesso.")

def carregar_layout_nos_sliders():
    scale_desc_x.set(CONFIG_LAYOUT["descricao_x"])
    scale_desc_y.set(CONFIG_LAYOUT["descricao_y"])
    scale_desc_font.set(CONFIG_LAYOUT["descricao_font"])

    scale_lote_x.set(CONFIG_LAYOUT["lote_x"])
    scale_lote_y.set(CONFIG_LAYOUT["lote_y"])
    scale_lote_font.set(CONFIG_LAYOUT["lote_font"])

    scale_vol_x.set(CONFIG_LAYOUT["volume_x"])
    scale_vol_y.set(CONFIG_LAYOUT["volume_y"])
    scale_vol_font.set(CONFIG_LAYOUT["volume_font"])

    scale_qr_x.set(CONFIG_LAYOUT["qr_x"])
    scale_qr_y.set(CONFIG_LAYOUT["qr_y"])
    scale_qr_m.set(CONFIG_LAYOUT["qr_magnification"])

    scale_linha2.set(CONFIG_LAYOUT["linha2_offset_y"])
    combo_orientacao.set(CONFIG_LAYOUT.get("orientacao", "N"))

    atualizar_labels_sliders()

# ==========================================================
# IMPRESSORA UI
# ==========================================================
def selecionar_impressora():
    impressoras = listar_impressoras()
    if not impressoras:
        messagebox.showwarning("Atenção", "Nenhuma impressora encontrada.")
        return

    janela = tk.Toplevel(root)
    janela.title("Selecionar Impressora")
    janela.geometry("420x300")
    janela.transient(root)
    janela.grab_set()

    ttk.Label(janela, text="Selecione a impressora:").pack(anchor="w", padx=10, pady=10)

    lista = tk.Listbox(janela, height=12)
    lista.pack(fill="both", expand=True, padx=10, pady=5)

    for nome in impressoras:
        lista.insert(tk.END, nome)

    atual = entry_impressora.get().strip()
    if atual in impressoras:
        idx = impressoras.index(atual)
        lista.selection_set(idx)
        lista.see(idx)

    def confirmar():
        sel = lista.curselection()
        if not sel:
            messagebox.showwarning("Atenção", "Selecione uma impressora.")
            return
        nome = lista.get(sel[0])
        entry_impressora.delete(0, tk.END)
        entry_impressora.insert(0, nome)
        janela.destroy()

    ttk.Button(janela, text="Selecionar", command=confirmar).pack(pady=10)

def usar_padrao_windows():
    nome = obter_impressora_padrao_windows()
    if not nome:
        messagebox.showwarning("Atenção", "Nenhuma impressora padrão configurada.")
        return
    entry_impressora.delete(0, tk.END)
    entry_impressora.insert(0, nome)

def salvar_impressora_padrao():
    nome = entry_impressora.get().strip()
    if not nome:
        messagebox.showwarning("Atenção", "Selecione uma impressora.")
        return
    CONFIG_IMPRESSORA["impressora_padrao"] = nome
    salvar_configuracao(CONFIG_IMPRESSORA_ARQ, CONFIG_IMPRESSORA)
    messagebox.showinfo("Sucesso", f"Impressora padrão salva:\n{nome}")

def carregar_impressora_salva():
    nome = CONFIG_IMPRESSORA.get("impressora_padrao", "").strip()
    if nome:
        entry_impressora.delete(0, tk.END)
        entry_impressora.insert(0, nome)
    else:
        padrao = obter_impressora_padrao_windows()
        if padrao:
            entry_impressora.delete(0, tk.END)
            entry_impressora.insert(0, padrao)

# ==========================================================
# AÇÕES
# ==========================================================
def imprimir(apenas_uma=False):
    try:
        dados = coletar_dados()
        erro = validar_dados(dados)
        if erro:
            messagebox.showwarning("Atenção", erro)
            return

        impressora = entry_impressora.get().strip()
        if not impressora:
            messagebox.showwarning("Atenção", "Selecione uma impressora.")
            return

        quantidade = 1 if apenas_uma else int(dados["quantidade"])
        zpl = gerar_zpl_lote(dados, quantidade)
        imprimir_zpl_na_impressora(impressora, zpl)

        if apenas_uma:
            messagebox.showinfo("Sucesso", f"1 etiqueta enviada para:\n{impressora}")
        else:
            messagebox.showinfo("Sucesso", f"{quantidade} etiqueta(s) enviada(s) para:\n{impressora}")
    except Exception as e:
        messagebox.showerror("Erro", str(e))

def limpar_campos():
    entry_lote.delete(0, tk.END)
    entry_codigo.delete(0, tk.END)
    text_desc.delete("1.0", tk.END)
    entry_volume_total.delete(0, tk.END)
    entry_quantidade.delete(0, tk.END)

    entry_lote.insert(0, "25-004855")
    entry_codigo.insert(0, "132483")
    text_desc.insert("1.0", "Tbe IPP 200L AZ 10,3 KG RE BJBR SL Tolerancia MIN10,0 KG - ECZLJ")
    entry_volume_total.insert(0, "10")
    entry_quantidade.insert(0, "2")

    desenhar_previa()

# ==========================================================
# SCROLLABLE FRAME
# ==========================================================
class ScrollableFrame(ttk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)

        canvas = tk.Canvas(self, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)

        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        window_id = canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        def resize_frame(event):
            canvas.itemconfig(window_id, width=event.width)

        canvas.bind("<Configure>", resize_frame)

        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.canvas = canvas

# ==========================================================
# UI
# ==========================================================
root = tk.Tk()
root.title("Gerador de Etiquetas Zebra 100x40")
root.geometry("980x690")
root.minsize(920, 650)

style = ttk.Style()
try:
    if "vista" in style.theme_names():
        style.theme_use("vista")
    else:
        style.theme_use("clam")
except Exception:
    pass

notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True, padx=10, pady=10)

aba_impressao = ttk.Frame(notebook)
aba_ajuste = ttk.Frame(notebook)

notebook.add(aba_impressao, text="Impressão")
notebook.add(aba_ajuste, text="Ajuste da Etiqueta")

# ==========================================================
# ABA 1 - IMPRESSÃO
# ==========================================================
container1 = ttk.Frame(aba_impressao, padding=12)
container1.pack(fill="both", expand=True)

frm_dados = ttk.LabelFrame(container1, text="Dados da Etiqueta", padding=10)
frm_dados.pack(fill="x", pady=(0, 12))

ttk.Label(frm_dados, text="Número do Lote (OS)").grid(row=0, column=0, sticky="w", padx=6, pady=6)
entry_lote = ttk.Entry(frm_dados, width=28)
entry_lote.grid(row=0, column=1, sticky="w", padx=6, pady=6)

ttk.Label(frm_dados, text="Código do Produto").grid(row=1, column=0, sticky="w", padx=6, pady=6)
entry_codigo = ttk.Entry(frm_dados, width=28)
entry_codigo.grid(row=1, column=1, sticky="w", padx=6, pady=6)

ttk.Label(frm_dados, text="Descrição").grid(row=2, column=0, sticky="nw", padx=6, pady=6)
text_desc = tk.Text(frm_dados, width=50, height=5)
text_desc.grid(row=2, column=1, sticky="w", padx=6, pady=6)

ttk.Label(frm_dados, text="Volume total").grid(row=3, column=0, sticky="w", padx=6, pady=6)
entry_volume_total = ttk.Entry(frm_dados, width=12)
entry_volume_total.grid(row=3, column=1, sticky="w", padx=6, pady=6)

ttk.Label(frm_dados, text="Quantidade de etiquetas").grid(row=4, column=0, sticky="w", padx=6, pady=6)
entry_quantidade = ttk.Entry(frm_dados, width=12)
entry_quantidade.grid(row=4, column=1, sticky="w", padx=6, pady=6)

frm_imp = ttk.LabelFrame(container1, text="Impressora", padding=10)
frm_imp.pack(fill="x", pady=(0, 12))

ttk.Label(frm_imp, text="Impressora").grid(row=0, column=0, sticky="w", padx=6, pady=6)
entry_impressora = ttk.Entry(frm_imp, width=42)
entry_impressora.grid(row=0, column=1, sticky="w", padx=6, pady=6)

linha_btn_imp = ttk.Frame(frm_imp)
linha_btn_imp.grid(row=1, column=0, columnspan=2, sticky="w", padx=6, pady=6)

ttk.Button(linha_btn_imp, text="Selecionar...", command=selecionar_impressora).pack(side="left", padx=(0, 6))
ttk.Button(linha_btn_imp, text="Usar padrão do Windows", command=usar_padrao_windows).pack(side="left", padx=(0, 6))
ttk.Button(linha_btn_imp, text="Salvar como padrão", command=salvar_impressora_padrao).pack(side="left")

frm_acoes = ttk.Frame(container1)
frm_acoes.pack(fill="x", pady=(4, 0))

ttk.Button(frm_acoes, text="Imprimir", command=lambda: imprimir(False)).pack(side="left", padx=(0, 8))
ttk.Button(frm_acoes, text="Testar 1 Etiqueta", command=lambda: imprimir(True)).pack(side="left", padx=(0, 8))
ttk.Button(frm_acoes, text="Limpar", command=limpar_campos).pack(side="left")

# ==========================================================
# ABA 2 - AJUSTE
# ==========================================================
container2 = ttk.Frame(aba_ajuste, padding=10)
container2.pack(fill="both", expand=True)

left2 = ttk.Frame(container2)
left2.pack(side="left", fill="both", expand=True, padx=(0, 8))

right2 = ttk.Frame(container2, width=340)
right2.pack(side="right", fill="y")
right2.pack_propagate(False)

frm_preview = ttk.LabelFrame(left2, text="Prévia", padding=8)
frm_preview.pack(fill="both", expand=True)

canvas_preview = tk.Canvas(frm_preview, bg="#efefef", highlightthickness=0)
canvas_preview.pack(fill="both", expand=True)

frm_scroll = ttk.LabelFrame(right2, text="Controles de Ajuste", padding=0)
frm_scroll.pack(fill="both", expand=True)

scrollable = ScrollableFrame(frm_scroll)
scrollable.pack(fill="both", expand=True)

controls = scrollable.scrollable_frame

def add_slider(parent, texto, de, ate, row):
    ttk.Label(parent, text=texto).grid(row=row, column=0, sticky="w", padx=8, pady=(8, 2))
    scale = tk.Scale(parent, from_=de, to=ate, orient="horizontal", length=180,
                     command=atualizar_layout_de_sliders, showvalue=False)
    scale.grid(row=row, column=1, sticky="w", padx=8, pady=(8, 2))
    lbl = ttk.Label(parent, text="0", width=5)
    lbl.grid(row=row, column=2, sticky="w", padx=4, pady=(8, 2))
    return scale, lbl

scale_desc_x, lbl_desc_x = add_slider(controls, "Descrição X", 0, 500, 0)
scale_desc_y, lbl_desc_y = add_slider(controls, "Descrição Y", 0, 220, 1)
scale_desc_font, lbl_desc_font = add_slider(controls, "Descrição Fonte", 10, 40, 2)

scale_lote_x, lbl_lote_x = add_slider(controls, "Lote X", 0, 500, 3)
scale_lote_y, lbl_lote_y = add_slider(controls, "Lote Y", 0, 250, 4)
scale_lote_font, lbl_lote_font = add_slider(controls, "Lote Fonte", 10, 36, 5)

scale_vol_x, lbl_vol_x = add_slider(controls, "Volume X", 0, 500, 6)
scale_vol_y, lbl_vol_y = add_slider(controls, "Volume Y", 0, 280, 7)
scale_vol_font, lbl_vol_font = add_slider(controls, "Volume Fonte", 10, 40, 8)

scale_qr_x, lbl_qr_x = add_slider(controls, "QR X", 300, 700, 9)
scale_qr_y, lbl_qr_y = add_slider(controls, "QR Y", 0, 180, 10)
scale_qr_m, lbl_qr_m = add_slider(controls, "QR Tamanho", 2, 8, 11)

scale_linha2, lbl_linha2 = add_slider(controls, "Espaço Linha 2", 15, 50, 12)

ttk.Label(controls, text="Orientação").grid(row=13, column=0, sticky="w", padx=8, pady=(10, 4))
combo_orientacao = ttk.Combobox(controls, values=["N", "R", "I", "B"], state="readonly", width=8)
combo_orientacao.grid(row=13, column=1, sticky="w", padx=8, pady=(10, 4))
combo_orientacao.bind("<<ComboboxSelected>>", atualizar_layout_de_sliders)

ttk.Button(controls, text="Salvar Layout", command=salvar_layout).grid(row=14, column=1, sticky="w", padx=8, pady=12)

# ==========================================================
# INIT
# ==========================================================
carregar_impressora_salva()
carregar_layout_nos_sliders()
limpar_campos()
atualizar_layout_de_sliders()

root.mainloop()