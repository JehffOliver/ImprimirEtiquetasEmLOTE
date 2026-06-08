# -*- coding: utf-8 -*-
# Gerador de Etiquetas Zebra 100x40 - Interface com Abas
#
# Requisitos:
#   pip install pywin32 reportlab

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
import random
import string
from datetime import datetime

try:
    import win32print
except ImportError:
    win32print = None

try:
    from reportlab.pdfgen import canvas as pdf_canvas
    from reportlab.lib.units import mm as rl_mm
    from reportlab.graphics.barcode.qr import QrCodeWidget
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics import renderPDF
    HAS_REPORTLAB = True
except ImportError:
    pdf_canvas = None
    rl_mm = None
    QrCodeWidget = None
    Drawing = None
    renderPDF = None
    HAS_REPORTLAB = False

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
def ensure_os_prefix(valor: str) -> str:
    s = str(valor or "").strip().upper()
    if not s:
        return ""
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

def normalizar_espacos(texto: str) -> str:
    return " ".join(str(texto or "").replace("\n", " ").replace("\r", " ").split()).strip()

def truncar_com_reticencias(texto, limite):
    texto = str(texto or "")
    if limite <= 0:
        return ""
    if len(texto) <= limite:
        return texto
    if limite == 1:
        return "…"
    return texto[:limite - 1].rstrip() + "…"

def wrap_text_by_chars(texto, max_chars):
    texto = normalizar_espacos(texto)
    if not texto:
        return []

    max_chars = max(4, int(max_chars))
    palavras = texto.split()
    linhas = []
    atual = ""

    for palavra in palavras:
        if len(palavra) > max_chars:
            if atual:
                linhas.append(atual)
                atual = ""

            restante = palavra
            while len(restante) > max_chars:
                linhas.append(restante[:max_chars])
                restante = restante[max_chars:]
            if restante:
                atual = restante
            continue

        teste = palavra if not atual else f"{atual} {palavra}"
        if len(teste) <= max_chars:
            atual = teste
        else:
            if atual:
                linhas.append(atual)
            atual = palavra

    if atual:
        linhas.append(atual)

    return linhas

def fit_description_layout(texto, cfg):
    texto = normalizar_espacos(texto)

    if not texto:
        return {
            "font": int(cfg["descricao_font"]),
            "line_height": max(12, int(cfg["descricao_font"]) + 2),
            "lines": [""],
        }

    desc_x = int(cfg["descricao_x"])
    desc_y = int(cfg["descricao_y"])
    lote_y = int(cfg["lote_y"])
    qr_x = int(cfg["qr_x"])

    available_width = max(120, qr_x - desc_x - 24)
    available_height = max(18, lote_y - desc_y - 8)

    preferred_font = int(cfg["descricao_font"])
    min_font = 10
    max_lines_cap = 6

    for font in range(preferred_font, min_font - 1, -1):
        char_width = max(5.0, font * 0.58)
        max_chars = max(8, int(available_width / char_width))
        line_height = max(font + 2, int(font * 1.18))
        lines_by_height = max(1, available_height // line_height)
        allowed_lines = max(1, min(max_lines_cap, lines_by_height))

        lines = wrap_text_by_chars(texto, max_chars)
        if len(lines) <= allowed_lines:
            return {
                "font": font,
                "line_height": line_height,
                "lines": lines,
            }

    font = min_font
    char_width = max(5.0, font * 0.58)
    max_chars = max(8, int(available_width / char_width))
    line_height = max(font + 2, int(font * 1.18))
    lines_by_height = max(1, available_height // line_height)
    allowed_lines = max(1, min(max_lines_cap, lines_by_height))

    lines = wrap_text_by_chars(texto, max_chars)
    if len(lines) > allowed_lines:
        lines = lines[:allowed_lines]
        if lines:
            lines[-1] = truncar_com_reticencias(lines[-1], max_chars)

    return {
        "font": font,
        "line_height": line_height,
        "lines": lines,
    }


def dots_to_points(v):
    return float(v) * 72.0 / DPI

def qr_payload_compacto(codigo, identificador, qtd_pacote_int, volume_atual, volume_total):
    codigo_limpo = zpl_escape(codigo)
    identificador_limpo = zpl_escape(ensure_os_prefix(identificador))
    return f"{codigo_limpo}|{identificador_limpo}|{int(qtd_pacote_int)}|{int(volume_atual)}|{int(volume_total)}"

def gerar_sequencia_volumes(total_volumes, volume_inicial, quantidade, ordem_invertida=False):
    total_volumes = int(total_volumes)
    volume_inicial = int(volume_inicial)
    quantidade = int(quantidade)

    if total_volumes <= 0:
        raise ValueError("Volume total deve ser maior que zero.")

    if volume_inicial <= 0:
        raise ValueError("Volume inicial deve ser maior que zero.")

    if volume_inicial > total_volumes:
        raise ValueError("Volume inicial não pode ser maior que o volume total.")

    if quantidade <= 0:
        raise ValueError("Quantidade deve ser maior que zero.")

    volume_final = volume_inicial + quantidade - 1
    if volume_final > total_volumes:
        raise ValueError(
            f"O intervalo solicitado ultrapassa o volume total. "
            f"Último volume seria {volume_final}, mas o total é {total_volumes}."
        )

    if ordem_invertida:
        return list(range(volume_final, volume_inicial - 1, -1))
    return list(range(volume_inicial, volume_final + 1))

def nome_pdf_padrao(dados, apenas_uma=False):
    tipo = dados.get("tipo_etiqueta", "etiqueta")
    codigo = (dados.get("codigo_produto") or "item").strip() or "item"
    identificador = (dados.get("identificador") or "").strip().replace("/", "-").replace("\\", "-")
    datahora = datetime.now().strftime("%Y%m%d_%H%M%S")
    sufixo = "1etiqueta" if apenas_uma else f"{dados.get('quantidade', 'lote')}etiquetas"
    partes = [tipo, codigo]
    if identificador:
        partes.append(identificador)
    partes.append(sufixo)
    partes.append(datahora)
    return "_".join(partes) + ".pdf"

def desenhar_qr_no_pdf(c, payload, x_dots, y_dots, size_dots):
    if not HAS_REPORTLAB:
        return

    qr_widget = QrCodeWidget(payload)
    bounds = qr_widget.getBounds()
    x1, y1, x2, y2 = bounds
    w = max(1, x2 - x1)
    h = max(1, y2 - y1)

    size_pt = dots_to_points(size_dots)
    drawing = Drawing(size_pt, size_pt, transform=[size_pt / w, 0, 0, size_pt / h, 0, 0])
    drawing.add(qr_widget)

    page_h = dots_to_points(LABEL_HEIGHT)
    x_pt = dots_to_points(x_dots)
    y_pt = page_h - dots_to_points(y_dots) - size_pt

    renderPDF.draw(drawing, c, x_pt, y_pt)

def gerar_pdf_lote(dados, quantidade, pdf_path):
    if not HAS_REPORTLAB:
        raise RuntimeError("Para gerar PDF, instale o pacote reportlab: pip install reportlab")

    identificador = dados["identificador"].strip()
    codigo = dados["codigo_produto"].strip()
    descricao = dados["descricao"].strip()
    tipo_etiqueta = dados.get("tipo_etiqueta", "injetora").strip().lower()
    qtd_pacote = dados.get("qtd_pacote", "1")
    ordem_invertida = bool(dados.get("ordem_invertida", False))

    total_volumes = int(dados["total_volumes"])
    volume_inicial = int(dados["volume_inicial"])
    volumes = gerar_sequencia_volumes(total_volumes, volume_inicial, quantidade, ordem_invertida)

    try:
        qtd_pacote_int = int(str(qtd_pacote).strip())
        if qtd_pacote_int <= 0:
            qtd_pacote_int = 1
    except Exception:
        qtd_pacote_int = 1

    qtd_pacote_fmt = f"{qtd_pacote_int:04d}"
    page_size = (LARGURA_MM * rl_mm, ALTURA_MM * rl_mm)
    c = pdf_canvas.Canvas(pdf_path, pagesize=page_size)
    page_w, page_h = page_size

    for volume_atual in volumes:
        descricao_layout = fit_description_layout(
            f"{codigo} / {normalizar_espacos(descricao)}" if descricao else codigo,
            CONFIG_LAYOUT
        )

        identificador_limpo = ensure_os_prefix(identificador)

        if tipo_etiqueta == "sopradora":
            txt_identificador = f"Número do Lote: {identificador_limpo}"
        else:
            txt_identificador = f"{identificador_limpo}"

        txt_pacote = f"PACOTE COM {qtd_pacote_fmt} UN"
        txt_vol = f"VOLUME {volume_atual}/{total_volumes}"

        desc_x = int(CONFIG_LAYOUT["descricao_x"])
        desc_y = int(CONFIG_LAYOUT["descricao_y"])

        lote_x = int(CONFIG_LAYOUT["lote_x"])
        lote_y = int(CONFIG_LAYOUT["lote_y"])
        lote_font = int(CONFIG_LAYOUT["lote_font"])

        vol_x = int(CONFIG_LAYOUT["volume_x"])
        vol_y = int(CONFIG_LAYOUT["volume_y"])
        vol_font = int(CONFIG_LAYOUT["volume_font"])

        qr_x = int(CONFIG_LAYOUT["qr_x"])
        qr_y = int(CONFIG_LAYOUT["qr_y"])
        qr_m = int(CONFIG_LAYOUT["qr_magnification"])

        qr_size_dots = max(84, (int(qr_m) * 22) + 34)

        # Borda leve para enxergar a etiqueta em casa
        c.setLineWidth(0.4)
        c.rect(0.6 * rl_mm, 0.6 * rl_mm, page_w - (1.2 * rl_mm), page_h - (1.2 * rl_mm))

        for idx_linha, linha in enumerate(descricao_layout["lines"]):
            font_pt = dots_to_points(descricao_layout["font"])
            y_top_dots = desc_y + (idx_linha * descricao_layout["line_height"])
            x_pt = dots_to_points(desc_x)
            y_pt = page_h - dots_to_points(y_top_dots) - font_pt
            c.setFont("Helvetica-Bold", font_pt)
            c.drawString(x_pt, y_pt, linha)

        lote_font_pt = dots_to_points(lote_font)
        lote_x_pt = dots_to_points(lote_x)
        lote_y_pt = page_h - dots_to_points(lote_y) - lote_font_pt
        c.setFont("Helvetica", lote_font_pt)
        c.drawString(lote_x_pt, lote_y_pt, txt_identificador)

        pacote_font_pt = dots_to_points(lote_font)
        pacote_y_dots = lote_y + max(34, lote_font + 10)
        pacote_y_pt = page_h - dots_to_points(pacote_y_dots) - pacote_font_pt
        c.setFont("Helvetica-Bold", pacote_font_pt)
        c.drawString(lote_x_pt, pacote_y_pt, txt_pacote)

        vol_font_pt = dots_to_points(vol_font)
        vol_x_pt = dots_to_points(vol_x)
        vol_y_pt = page_h - dots_to_points(vol_y) - vol_font_pt
        c.setFont("Helvetica-Bold", vol_font_pt)
        c.drawString(vol_x_pt, vol_y_pt, txt_vol)

        payload = qr_payload_compacto(codigo, identificador_limpo, qtd_pacote_int, volume_atual, total_volumes)
        desenhar_qr_no_pdf(c, payload, qr_x, qr_y, qr_size_dots)

        c.showPage()

    c.save()

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
def gerar_zpl_uma_etiqueta(
    codigo,
    descricao,
    identificador,
    volume_atual,
    volume_total,
    tipo_etiqueta="injetora",
    qtd_pacote="1"
):
    codigo = zpl_escape(codigo)

    descricao_layout = fit_description_layout(
        f"{codigo} / {normalizar_espacos(descricao)}" if descricao else codigo,
        CONFIG_LAYOUT
    )

    identificador_limpo = zpl_escape(ensure_os_prefix(identificador))
    volume_atual = zpl_escape(str(volume_atual))
    volume_total = zpl_escape(str(volume_total))

    try:
        qtd_pacote_int = int(str(qtd_pacote).strip())
        if qtd_pacote_int <= 0:
            qtd_pacote_int = 1
    except Exception:
        qtd_pacote_int = 1

    qtd_pacote_fmt = f"{qtd_pacote_int:04d}"

    qr_payload = qr_payload_compacto(codigo, identificador_limpo, qtd_pacote_int, volume_atual, volume_total)

    if tipo_etiqueta == "sopradora":
        txt_identificador = f"Número do Lote: {identificador_limpo}"
    else:
        txt_identificador = f"{identificador_limpo}"

    txt_pacote = f"PACOTE COM {qtd_pacote_fmt} UN"
    txt_vol = f"VOLUME {volume_atual}/{volume_total}"

    desc_x = int(CONFIG_LAYOUT["descricao_x"])
    desc_y = int(CONFIG_LAYOUT["descricao_y"])

    lote_x = int(CONFIG_LAYOUT["lote_x"])
    lote_y = int(CONFIG_LAYOUT["lote_y"])
    lote_font = int(CONFIG_LAYOUT["lote_font"])

    vol_x = int(CONFIG_LAYOUT["volume_x"])
    vol_y = int(CONFIG_LAYOUT["volume_y"])
    vol_font = int(CONFIG_LAYOUT["volume_font"])

    qr_x = int(CONFIG_LAYOUT["qr_x"])
    qr_y = int(CONFIG_LAYOUT["qr_y"])
    qr_m = int(CONFIG_LAYOUT["qr_magnification"])

    orient = CONFIG_LAYOUT.get("orientacao", "N")

    pacote_x = lote_x
    pacote_y = lote_y + max(34, lote_font + 10)
    pacote_font = lote_font

    zpl = f"""
^XA
^PW{LABEL_WIDTH}
^LL{LABEL_HEIGHT}
^LH0,0
^CI28
^FWN
"""

    for idx, linha in enumerate(descricao_layout["lines"]):
        y = desc_y + (idx * descricao_layout["line_height"])
        zpl += f'^FO{desc_x},{y}^A0{orient},{descricao_layout["font"]},{descricao_layout["font"]}^FD{zpl_escape(linha)}^FS\n'

    zpl += f"""
^FO{lote_x},{lote_y}^A0{orient},{lote_font},{lote_font}^FD{txt_identificador}^FS
^FO{pacote_x},{pacote_y}^A0{orient},{pacote_font},{pacote_font}^FD{txt_pacote}^FS
^FO{vol_x},{vol_y}^A0{orient},{vol_font},{vol_font}^FD{txt_vol}^FS
^FO{qr_x},{qr_y}^BQN,2,{qr_m}
^FDLA,{qr_payload}^FS
^XZ
"""
    return zpl.strip() + "\n"

def gerar_zpl_lote(dados, quantidade):
    identificador = dados["identificador"].strip()
    codigo = dados["codigo_produto"].strip()
    descricao = dados["descricao"].strip()
    tipo_etiqueta = dados.get("tipo_etiqueta", "injetora").strip().lower()
    qtd_pacote = dados.get("qtd_pacote", "1")
    ordem_invertida = bool(dados.get("ordem_invertida", False))

    total_volumes = int(dados["total_volumes"])
    volume_inicial = int(dados["volume_inicial"])
    volumes = gerar_sequencia_volumes(total_volumes, volume_inicial, quantidade, ordem_invertida)

    etiquetas = []
    for volume_atual in volumes:
        etiquetas.append(
            gerar_zpl_uma_etiqueta(
                codigo=codigo,
                descricao=descricao,
                identificador=identificador,
                volume_atual=volume_atual,
                volume_total=total_volumes,
                tipo_etiqueta=tipo_etiqueta,
                qtd_pacote=qtd_pacote,
            )
        )
    return "\n".join(etiquetas)

# ==========================================================
# DADOS / FORMULÁRIOS
# ==========================================================
FORMULARIOS = {}
notebook_modelos = None
ordem_invertida_var = None

def get_tipo_etiqueta_atual():
    try:
        aba_id = notebook_modelos.select()
        return notebook_modelos.tab(aba_id, "text").strip().lower()
    except Exception:
        return "injetora"

def get_formulario_atual():
    return FORMULARIOS.get(get_tipo_etiqueta_atual(), FORMULARIOS.get("injetora", {}))

def get_widget_value(widget):
    if widget is None:
        return ""
    if isinstance(widget, tk.Text):
        return widget.get("1.0", tk.END).strip()
    return widget.get().strip()

def criar_formulario_tipo(parent, tipo):
    titulo = "Dados da Etiqueta - Sopradora" if tipo == "sopradora" else "Dados da Etiqueta - Injetora"

    frm_dados = ttk.LabelFrame(parent, text=titulo, padding=10)
    frm_dados.pack(fill="x", pady=(0, 12))

    label_identificador = "Número do Lote" if tipo == "sopradora" else "OS"
    ttk.Label(frm_dados, text=label_identificador).grid(row=0, column=0, sticky="w", padx=6, pady=6)
    entry_identificador = ttk.Entry(frm_dados, width=28)
    entry_identificador.grid(row=0, column=1, sticky="w", padx=6, pady=6)

    ttk.Label(frm_dados, text="Código do Produto").grid(row=1, column=0, sticky="w", padx=6, pady=6)
    entry_codigo = ttk.Entry(frm_dados, width=28)
    entry_codigo.grid(row=1, column=1, sticky="w", padx=6, pady=6)

    ttk.Label(frm_dados, text="Descrição").grid(row=2, column=0, sticky="nw", padx=6, pady=6)
    text_desc = tk.Text(frm_dados, width=50, height=5)
    text_desc.grid(row=2, column=1, sticky="w", padx=6, pady=6)

    ttk.Label(frm_dados, text="Volume total").grid(row=3, column=0, sticky="w", padx=6, pady=6)
    entry_volume_total = ttk.Entry(frm_dados, width=12)
    entry_volume_total.grid(row=3, column=1, sticky="w", padx=6, pady=6)

    ttk.Label(frm_dados, text="Volume inicial").grid(row=4, column=0, sticky="w", padx=6, pady=6)
    entry_volume_inicial = ttk.Entry(frm_dados, width=12)
    entry_volume_inicial.grid(row=4, column=1, sticky="w", padx=6, pady=6)

    ttk.Label(frm_dados, text="Pacote (UN)").grid(row=5, column=0, sticky="w", padx=6, pady=6)
    entry_qtd_pacote = ttk.Entry(frm_dados, width=12)
    entry_qtd_pacote.grid(row=5, column=1, sticky="w", padx=6, pady=6)

    ttk.Label(frm_dados, text="Quantidade de etiquetas").grid(row=6, column=0, sticky="w", padx=6, pady=6)
    entry_quantidade = ttk.Entry(frm_dados, width=12)
    entry_quantidade.grid(row=6, column=1, sticky="w", padx=6, pady=6)

    widgets_para_bind = [
        entry_identificador,
        entry_codigo,
        entry_volume_total,
        entry_volume_inicial,
        entry_qtd_pacote,
        entry_quantidade
    ]

    for widget in widgets_para_bind:
        widget.bind("<KeyRelease>", lambda e: desenhar_previa())

    text_desc.bind("<KeyRelease>", lambda e: desenhar_previa())

    return {
        "identificador": entry_identificador,
        "codigo": entry_codigo,
        "descricao": text_desc,
        "volume_total": entry_volume_total,
        "volume_inicial": entry_volume_inicial,
        "qtd_pacote": entry_qtd_pacote,
        "quantidade": entry_quantidade,
    }

def coletar_dados():
    form = get_formulario_atual()
    return {
        "tipo_etiqueta": get_tipo_etiqueta_atual(),
        "identificador": get_widget_value(form.get("identificador")),
        "codigo_produto": get_widget_value(form.get("codigo")),
        "descricao": get_widget_value(form.get("descricao")),
        "total_volumes": get_widget_value(form.get("volume_total")),
        "volume_inicial": get_widget_value(form.get("volume_inicial")),
        "qtd_pacote": get_widget_value(form.get("qtd_pacote")),
        "quantidade": get_widget_value(form.get("quantidade")),
        "ordem_invertida": bool(ordem_invertida_var.get()) if ordem_invertida_var else False,
    }

def validar_dados(dados):
    label_id = "Número do Lote" if dados.get("tipo_etiqueta") == "sopradora" else "OS"

    if not dados["identificador"]:
        return f"Preencha o campo {label_id}."
    if not dados["codigo_produto"]:
        return "Preencha o código do produto."
    if not dados["descricao"]:
        return "Preencha a descrição."
    if not dados["total_volumes"]:
        return "Preencha o volume total."
    if not dados["volume_inicial"]:
        return "Preencha o volume inicial."
    if not dados["qtd_pacote"]:
        return "Preencha o Pacote (UN)."
    if not dados["quantidade"]:
        return "Preencha a quantidade de etiquetas."

    try:
        total = int(dados["total_volumes"])
        if total <= 0:
            return "Volume total deve ser maior que zero."
    except Exception:
        return "Volume total inválido."

    try:
        volume_inicial = int(dados["volume_inicial"])
        if volume_inicial <= 0:
            return "Volume inicial deve ser maior que zero."
    except Exception:
        return "Volume inicial inválido."

    if volume_inicial > total:
        return "Volume inicial não pode ser maior que o volume total."

    try:
        qtd_pacote = int(dados["qtd_pacote"])
        if qtd_pacote <= 0:
            return "Pacote (UN) deve ser maior que zero."
    except Exception:
        return "Pacote (UN) inválido."

    try:
        qtd = int(dados["quantidade"])
        if qtd <= 0:
            return "Quantidade deve ser maior que zero."
    except Exception:
        return "Quantidade inválida."

    volume_final = volume_inicial + qtd - 1
    if volume_final > total:
        return f"O intervalo solicitado termina em {volume_final}, mas o volume total é {total}."

    return None

def preencher_formulario_padrao(form, tipo):
    form["identificador"].delete(0, tk.END)
    form["codigo"].delete(0, tk.END)
    form["descricao"].delete("1.0", tk.END)
    form["volume_total"].delete(0, tk.END)
    form["volume_inicial"].delete(0, tk.END)
    form["qtd_pacote"].delete(0, tk.END)
    form["quantidade"].delete(0, tk.END)

    if tipo == "sopradora":
        form["identificador"].insert(0, "OS26008254")
    else:
        form["identificador"].insert(0, "OS25-004855")

    form["codigo"].insert(0, "132483")
    form["descricao"].insert("1.0", "Tbe IPP 200L AZ 10,3 KG RE BJBR SL Tolerancia MIN10,0 KG - ECZLJ")
    form["volume_total"].insert(0, "250")
    form["volume_inicial"].insert(0, "1")
    form["qtd_pacote"].insert(0, "1")
    form["quantidade"].insert(0, "50")

def limpar_campos():
    for tipo, form in FORMULARIOS.items():
        preencher_formulario_padrao(form, tipo)

    if ordem_invertida_var is not None:
        ordem_invertida_var.set(False)

    desenhar_previa()

# ==========================================================
# PREVIEW
# ==========================================================
PREVIEW_SCALE = 0.5

def dots_to_canvas(v):
    return int(v * PREVIEW_SCALE)

def preview_font_px(dots_value):
    return max(7, dots_to_canvas(int(dots_value)))

def desenhar_previa():
    canvas_preview.delete("all")

    largura = dots_to_canvas(LABEL_WIDTH)
    altura = dots_to_canvas(LABEL_HEIGHT)

    x0 = 20
    y0 = 20
    x1 = x0 + largura
    y1 = y0 + altura

    canvas_preview.create_rectangle(x0, y0, x1, y1, fill="white", outline="#222", width=2)

    tipo_atual = get_tipo_etiqueta_atual().capitalize()
    canvas_preview.create_text(
        (x0 + x1)//2,
        8,
        text=f"Prévia da Etiqueta 100x40 - {tipo_atual}",
        font=("Segoe UI", -12, "bold")
    )

    dados = coletar_dados()
    codigo = dados["codigo_produto"].strip() or "132483"
    descricao = dados["descricao"].strip() or "Descrição do produto"
    identificador = ensure_os_prefix(dados["identificador"].strip() or "OS25-000000")

    try:
        total = int(dados["total_volumes"])
    except Exception:
        total = 250

    try:
        volume_inicial = int(dados.get("volume_inicial", "1"))
        if volume_inicial <= 0:
            volume_inicial = 1
    except Exception:
        volume_inicial = 1

    try:
        qtd = int(dados.get("quantidade", "1"))
        if qtd <= 0:
            qtd = 1
    except Exception:
        qtd = 1

    try:
        qtd_pacote = int(dados.get("qtd_pacote", "1"))
        if qtd_pacote <= 0:
            qtd_pacote = 1
    except Exception:
        qtd_pacote = 1

    qtd_pacote_fmt = f"{qtd_pacote:04d}"

    ordem_invertida = bool(dados.get("ordem_invertida", False))
    volume_preview = volume_inicial + qtd - 1 if ordem_invertida else volume_inicial
    if volume_preview > total:
        volume_preview = total

    desc_layout = fit_description_layout(f"{codigo} / {descricao}", CONFIG_LAYOUT)

    desc_x = x0 + dots_to_canvas(int(CONFIG_LAYOUT["descricao_x"]))
    desc_y = y0 + dots_to_canvas(int(CONFIG_LAYOUT["descricao_y"]))

    lote_x = x0 + dots_to_canvas(int(CONFIG_LAYOUT["lote_x"]))
    lote_y = y0 + dots_to_canvas(int(CONFIG_LAYOUT["lote_y"]))
    lote_font_px = preview_font_px(CONFIG_LAYOUT["lote_font"])

    vol_x = x0 + dots_to_canvas(int(CONFIG_LAYOUT["volume_x"]))
    vol_y = y0 + dots_to_canvas(int(CONFIG_LAYOUT["volume_y"]))
    vol_font_px = preview_font_px(CONFIG_LAYOUT["volume_font"])

    qr_x = x0 + dots_to_canvas(int(CONFIG_LAYOUT["qr_x"]))
    qr_y = y0 + dots_to_canvas(int(CONFIG_LAYOUT["qr_y"]))

    qr_size = max(42, dots_to_canvas((int(CONFIG_LAYOUT["qr_magnification"]) * 22) + 34))

    desc_font_px = preview_font_px(desc_layout["font"])
    line_height_preview = max(desc_font_px + 1, dots_to_canvas(desc_layout["line_height"]))

    for idx, linha in enumerate(desc_layout["lines"]):
        y = desc_y + (idx * line_height_preview)
        canvas_preview.create_text(
          desc_x,
          y,
          anchor="nw",
          text=linha,
          font=("Segoe UI", -desc_font_px, "bold")
        )

    if dados.get("tipo_etiqueta") == "sopradora":
        txt_identificador = f"Número do Lote: {identificador}"
    else:
        txt_identificador = f"{identificador}"

    canvas_preview.create_text(
        lote_x,
        lote_y,
        anchor="nw",
        text=txt_identificador,
        font=("Segoe UI", -lote_font_px)
    )

    pacote_y = lote_y + max(18, dots_to_canvas(int(CONFIG_LAYOUT["lote_font"]) + 8))
    canvas_preview.create_text(
        lote_x,
        pacote_y,
        anchor="nw",
        text=f"PACOTE COM {qtd_pacote_fmt} UN",
        font=("Segoe UI", -lote_font_px, "bold")
    )

    canvas_preview.create_text(
        vol_x,
        vol_y,
        anchor="nw",
        text=f"VOLUME {volume_preview}/{total}",
        font=("Segoe UI", -vol_font_px, "bold")
    )

    canvas_preview.create_rectangle(qr_x, qr_y, qr_x + qr_size, qr_y + qr_size, outline="#222", width=2)
    canvas_preview.create_text(
        qr_x + qr_size // 2,
        qr_y + qr_size // 2,
        text="QR",
        font=("Segoe UI", -12, "bold")
    )

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

def gerar_pdf(apenas_uma=False):
    try:
        dados = coletar_dados()
        erro = validar_dados(dados)
        if erro:
            messagebox.showwarning("Atenção", erro)
            return

        quantidade = 1 if apenas_uma else int(dados["quantidade"])
        nome_padrao = nome_pdf_padrao(dados, apenas_uma=apenas_uma)

        pdf_path = filedialog.asksaveasfilename(
            title="Salvar PDF das etiquetas",
            defaultextension=".pdf",
            initialfile=nome_padrao,
            filetypes=[("Arquivo PDF", "*.pdf")]
        )
        if not pdf_path:
            return

        gerar_pdf_lote(dados, quantidade, pdf_path)
        messagebox.showinfo("Sucesso", f"PDF gerado com sucesso:\n{pdf_path}")
    except Exception as e:
        messagebox.showerror("Erro", str(e))

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
root.geometry("980x720")
root.minsize(920, 680)

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

frm_modelos = ttk.LabelFrame(container1, text="Tipo de Etiqueta", padding=8)
frm_modelos.pack(fill="x", pady=(0, 12))

notebook_modelos = ttk.Notebook(frm_modelos)
notebook_modelos.pack(fill="x", expand=True)

aba_injetora = ttk.Frame(notebook_modelos)
aba_sopradora = ttk.Frame(notebook_modelos)

notebook_modelos.add(aba_injetora, text="Injetora")
notebook_modelos.add(aba_sopradora, text="Sopradora")

FORMULARIOS["injetora"] = criar_formulario_tipo(aba_injetora, "injetora")
FORMULARIOS["sopradora"] = criar_formulario_tipo(aba_sopradora, "sopradora")

notebook_modelos.bind("<<NotebookTabChanged>>", lambda e: desenhar_previa())

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

frm_opcoes = ttk.LabelFrame(container1, text="Opções de Impressão", padding=10)
frm_opcoes.pack(fill="x", pady=(0, 12))

ordem_invertida_var = tk.BooleanVar(value=False)
ttk.Checkbutton(
    frm_opcoes,
    text="Imprimir em ordem invertida (último → primeiro)",
    variable=ordem_invertida_var,
    command=desenhar_previa
).pack(anchor="w")

frm_acoes = ttk.Frame(container1)
frm_acoes.pack(fill="x", pady=(4, 0))

ttk.Button(frm_acoes, text="Imprimir", command=lambda: imprimir(False)).pack(side="left", padx=(0, 8))
ttk.Button(frm_acoes, text="Testar 1 Etiqueta", command=lambda: imprimir(True)).pack(side="left", padx=(0, 8))
ttk.Button(frm_acoes, text="Gerar PDF", command=lambda: gerar_pdf(False)).pack(side="left", padx=(0, 8))
ttk.Button(frm_acoes, text="PDF 1 Etiqueta", command=lambda: gerar_pdf(True)).pack(side="left", padx=(0, 8))
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