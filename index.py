# -*- coding: utf-8 -*-
# Gerador de Etiquetas - Versão 13 (QR novo)
# Requisitos: reportlab, qrcode, pillow
# pip install reportlab qrcode[pil] pillow

import tkinter as tk
from tkinter import ttk, messagebox
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
import qrcode
import json
from io import BytesIO
import os
import webbrowser
import math
import random
import string
from datetime import datetime

# ==========================================================
# CONFIG PADRÃO
# ==========================================================
PADRAO_TAMANHO = {
    "etiqueta_largura": 104.5,   # mm (usado como limite; é ajustado automaticamente para 2 colunas)
    "etiqueta_altura": 33.0,     # mm (é ajustado automaticamente para caber as linhas)
    "margem_esquerda": 0.0,      # mm margem interna do grid
    "margem_superior": 0.0,      # mm margem interna do grid
    "espacamento_colunas": 2.0   # mm entre colunas
}

PADRAO_MARGENS = {
    "margem_superior_pagina": 0.0,   # mm
    "margem_inferior_pagina": 0.0,   # mm
    "margem_esquerda_pagina": 0.0,   # mm
    "margem_direita_pagina": 0.0     # mm
}

PADRAO_POS = {
    "codigo_x": 5.0, "codigo_y": 8.0, "codigo_fonte": 9.0,

    "descricao_x": 5.0, "descricao_y": 12.0, "descricao_fonte": 9.0,
    "lote_x": 5.0,      "lote_y": 19.0, "lote_fonte": 9.0,
    "pacote_x": 5.0,    "pacote_y": 25.0, "pacote_fonte": 9.0,
    "volume_x": 5.0,    "volume_y": 31.0, "volume_fonte": 9.0,

    "qr_code_x": 80.0, "qr_code_y": 10.5, "qr_code_tamanho": 22.0
}

# ==========================================================
# LEITURA/GRAVAÇÃO DE JSON
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

CONFIG_TAMANHO = garantir_json("config_tamanho.json", PADRAO_TAMANHO)
CONFIG_MARGENS = garantir_json("config_margens.json", PADRAO_MARGENS)
CONFIG_POS     = garantir_json("config_posicionamento.json", PADRAO_POS)

def salvar_configuracao(arquivo, dados):
    with open(arquivo, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)
    messagebox.showinfo("Sucesso", f"Configuração salva em {arquivo}")

# ==========================================================
# UTILS
# ==========================================================
def ensure_os_prefix(lote_str: str) -> str:
    s = lote_str.strip().upper()
    if s.startswith("OS"):
        return s
    return "OS" + s

def gerar_chave_unica():
    # YYYYMMDD + 6 caracteres aleatórios
    dt = datetime.now().strftime("%Y%m%d")
    rand = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"{dt}{rand}"

def wrap_text_to_lines(cnv, text, max_width_pts, font_name, font_size, max_lines=2):
    words = text.replace("\r", " ").split()
    lines, current = [], ""
    for w in words:
        test = (current + " " + w).strip()
        if cnv.stringWidth(test, font_name, font_size) <= max_width_pts:
            current = test
        else:
            if current:
                lines.append(current)
            current = w
            if len(lines) >= max_lines:
                break
    if current and len(lines) < max_lines:
        lines.append(current)

    if lines:
        last = lines[-1]
        while cnv.stringWidth(last, font_name, font_size) > max_width_pts and len(last) > 0:
            last = last[:-1]
        if last != lines[-1]:
            while cnv.stringWidth(last + "...", font_name, font_size) > max_width_pts and len(last) > 0:
                last = last[:-1]
            lines[-1] = last.rstrip() + "..."
    return lines[:max_lines]

def make_qr_image(data, size_px=300):
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    img = img.resize((size_px, size_px))
    return img

# ==========================================================
# FORMULÁRIOS
# ==========================================================
def _form_duas_colunas(parent, campos, config_dict, labels_pt=None):
    entradas = {}
    for idx, campo in enumerate(campos):
        linha = idx // 2
        colpar = (idx % 2) * 2
        rotulo = labels_pt.get(campo, campo.replace("_", " ").capitalize()) if labels_pt else campo

        ttk.Label(parent, text=rotulo).grid(row=linha, column=colpar, sticky="w", padx=6, pady=4)
        e = ttk.Entry(parent, width=10)
        e.insert(0, str(config_dict.get(campo, "")))
        e.grid(row=linha, column=colpar + 1, sticky="w", padx=6, pady=4)
        entradas[campo] = e
    parent.grid_columnconfigure(1, weight=1)
    parent.grid_columnconfigure(3, weight=1)
    return entradas

def abrir_editor_tamanho():
    janela = tk.Toplevel(root)
    janela.title("Configurações de Tamanho")
    janela.geometry("760x360")
    janela.minsize(720, 340)

    lf = ttk.LabelFrame(janela, text="Tamanho da Etiqueta e Espaçamentos")
    lf.pack(fill="both", expand=True, padx=10, pady=10)

    campos = [
        "etiqueta_largura", "etiqueta_altura",
        "margem_esquerda",  "margem_superior",
        "espacamento_colunas"
    ]
    labels = {
        "etiqueta_largura": "Largura (mm)",
        "etiqueta_altura": "Altura (mm)",
        "margem_esquerda": "Margem Esquerda (mm)",
        "margem_superior": "Margem Superior (mm)",
        "espacamento_colunas": "Espaço entre Colunas (mm)"
    }
    entradas = _form_duas_colunas(lf, campos, CONFIG_TAMANHO, labels)

    lf_qr = ttk.LabelFrame(janela, text="QR Code (dentro da etiqueta)")
    lf_qr.pack(fill="both", expand=True, padx=10, pady=(0,10))
    campos_qr = ["qr_code_x", "qr_code_y", "qr_code_tamanho"]
    labels_qr = {"qr_code_x": "QR X (mm)", "qr_code_y": "QR Y (mm)", "qr_code_tamanho": "QR Tamanho (mm)"}
    entradas_qr = _form_duas_colunas(lf_qr, campos_qr, CONFIG_POS, labels_qr)

    def salvar():
        for k, e in entradas.items():
            try:
                CONFIG_TAMANHO[k] = float(e.get())
            except Exception:
                pass
        salvar_configuracao("config_tamanho.json", CONFIG_TAMANHO)

        for k, e in entradas_qr.items():
            try:
                CONFIG_POS[k] = float(e.get())
            except Exception:
                pass
        salvar_configuracao("config_posicionamento.json", CONFIG_POS)
        janela.destroy()

    btns = ttk.Frame(janela)
    btns.pack(pady=8)
    ttk.Button(btns, text="Salvar", command=salvar).pack(side="left", padx=6)
    ttk.Button(btns, text="Cancelar", command=janela.destroy).pack(side="left", padx=6)

def abrir_editor_margens():
    janela = tk.Toplevel(root)
    janela.title("Configurações de Margens da Página")
    janela.geometry("760x240")
    janela.minsize(720, 220)

    lf = ttk.LabelFrame(janela, text="Margens da Página (A4)")
    lf.pack(fill="both", expand=True, padx=10, pady=10)

    campos = ["margem_superior_pagina", "margem_inferior_pagina",
              "margem_esquerda_pagina", "margem_direita_pagina"]
    labels = {
        "margem_superior_pagina": "Superior (mm)",
        "margem_inferior_pagina": "Inferior (mm)",
        "margem_esquerda_pagina": "Esquerda (mm)",
        "margem_direita_pagina": "Direita (mm)"
    }
    entradas = _form_duas_colunas(lf, campos, CONFIG_MARGENS, labels)

    def salvar():
        for k, e in entradas.items():
            try:
                CONFIG_MARGENS[k] = float(e.get())
            except Exception:
                pass
        salvar_configuracao("config_margens.json", CONFIG_MARGENS)
        janela.destroy()

    btns = ttk.Frame(janela)
    btns.pack(pady=8)
    ttk.Button(btns, text="Salvar", command=salvar).pack(side="left", padx=6)
    ttk.Button(btns, text="Cancelar", command=janela.destroy).pack(side="left", padx=6)

def abrir_editor_posicao():
    janela = tk.Toplevel(root)
    janela.title("Configurações de Posição e Fonte")
    janela.geometry("960x520")
    janela.minsize(920, 480)

    frame = ttk.Frame(janela)
    frame.pack(fill="both", expand=True, padx=10, pady=10)

    grupos = [
        ("Descrição (inclui 'código / descrição')",
         ["descricao_x", "descricao_y", "descricao_fonte"], {
            "descricao_x": "Desc X (mm)",
            "descricao_y": "Desc Y (mm)",
            "descricao_fonte": "Desc Fonte (pt)"
         }),

        ("Lote", ["lote_x", "lote_y", "lote_fonte"], {
            "lote_x": "Lote X (mm)", "lote_y": "Lote Y (mm)", "lote_fonte": "Lote Fonte (pt)"
        }),

        ("Pacote", ["pacote_x", "pacote_y", "pacote_fonte"], {
            "pacote_x": "Pacote X (mm)", "pacote_y": "Pacote Y (mm)", "pacote_fonte": "Pacote Fonte (pt)"
        }),

        ("Volume", ["volume_x", "volume_y", "volume_fonte"], {
            "volume_x": "Volume X (mm)", "volume_y": "Volume Y (mm)", "volume_fonte": "Volume Fonte (pt)"
        }),

        ("QR Code", ["qr_code_x", "qr_code_y", "qr_code_tamanho"], {
            "qr_code_x": "QR X (mm)", "qr_code_y": "QR Y (mm)", "qr_code_tamanho": "QR Tamanho (mm)"
        })
    ]

    entradas = {}
    for i, (titulo, campos, labels) in enumerate(grupos):
        lf = ttk.LabelFrame(frame, text=titulo)
        lf.grid(row=i // 2, column=i % 2, sticky="nsew", padx=8, pady=8)
        ent = _form_duas_colunas(lf, campos, CONFIG_POS, labels)
        entradas.update(ent)

    for c in range(2):
        frame.grid_columnconfigure(c, weight=1)

    def salvar():
        for k, e in entradas.items():
            try:
                CONFIG_POS[k] = float(e.get())
            except Exception:
                pass
        salvar_configuracao("config_posicionamento.json", CONFIG_POS)
        janela.destroy()

    btns = ttk.Frame(janela)
    btns.pack(pady=8)
    ttk.Button(btns, text="Salvar", command=salvar).pack(side="left", padx=6)
    ttk.Button(btns, text="Cancelar", command=janela.destroy).pack(side="left", padx=6)

# ==========================================================
# GERAÇÃO DO PDF
# ==========================================================
def gerar_pdf(dados):
    try:
        lote = ensure_os_prefix(dados["lote"])
        codigo = dados["codigo_produto"].strip()
        descricao = dados["descricao"].strip()
        pacote = str(dados["pacote"]).strip()
        try:
            total_volumes = int(dados["total_volumes"])
        except Exception:
            messagebox.showerror("Erro", "Volume total inválido (use número inteiro).")
            return

        try:
            per_page = max(1, int(dados["quantidade"]))
        except Exception:
            messagebox.showerror("Erro", "Quantidade por página inválida (use número inteiro).")
            return

        if per_page > 18:
            per_page = 18

        COLS = 2
        ROWS = math.ceil(per_page / COLS)

        nome_arquivo = "etiquetas.pdf"
        c = canvas.Canvas(nome_arquivo, pagesize=A4)

        page_w, page_h = A4

        m_top  = CONFIG_MARGENS["margem_superior_pagina"] * mm
        m_bot  = CONFIG_MARGENS["margem_inferior_pagina"] * mm
        m_left = CONFIG_MARGENS["margem_esquerda_pagina"] * mm
        m_right= CONFIG_MARGENS["margem_direita_pagina"] * mm

        usable_w = page_w  - (m_left + m_right)
        usable_h = page_h  - (m_top + m_bot)

        ESPACO_H = CONFIG_TAMANHO["espacamento_colunas"] * mm

        LARGURA = (usable_w - (COLS - 1) * ESPACO_H) / COLS

        ALTURA_cfg = CONFIG_TAMANHO["etiqueta_altura"] * mm
        ALTURA = min(ALTURA_cfg, usable_h / ROWS)
        if ROWS * ALTURA_cfg > usable_h:
            ALTURA = usable_h / ROWS

        pos = CONFIG_POS

        fonte_desc = pos.get("descricao_fonte", 9)
        fonte_lote = pos.get("lote_fonte", 9)
        fonte_pac  = pos.get("pacote_fonte", 9)
        fonte_vol  = pos.get("volume_fonte", 9)

        qr_x_mm = pos.get("qr_code_x", 80.0)
        qr_y_mm = pos.get("qr_code_y", 10.5)
        qr_sz_mm= pos.get("qr_code_tamanho", 22.0)

        paginas = math.ceil(total_volumes / per_page) if total_volumes > 0 else 1
        contador = 1

        for p in range(paginas):
            for idx in range(per_page):
                if contador > total_volumes:
                    break

                col = idx % COLS
                row = idx // COLS

                x0 = m_left + col * (LARGURA + ESPACO_H)
                y0 = page_h - m_top - (row + 1) * ALTURA

                texto_full = f"{codigo} / {descricao}" if descricao else f"{codigo}"
                qr_w = qr_sz_mm * mm
                text_left = x0 + pos.get("descricao_x", 5.0) * mm
                text_right_lim = x0 + LARGURA - 6 * mm - qr_w
                max_width = max(10, text_right_lim - text_left)

                c.setFont("Helvetica", fonte_desc)
                linhas_desc = wrap_text_to_lines(c, texto_full, max_width, "Helvetica", fonte_desc, max_lines=2)

                txt_lote = f"Número do Lote: {lote}"
                txt_pac = f"PACOTE COM {str(pacote).zfill(3)} UN"
                txt_vol = f"VOLUME {contador}/{total_volumes}"

                base_top = y0 + ALTURA
                for j, linha in enumerate(linhas_desc):
                    y_text = base_top - (pos.get("descricao_y", 12.0) + j * 4.0) * mm
                    c.drawString(text_left, y_text, linha)

                c.setFont("Helvetica", fonte_lote)
                c.drawString(x0 + pos.get("lote_x", 5.0) * mm,
                             base_top - pos.get("lote_y", 19.0) * mm,
                             txt_lote)

                c.setFont("Helvetica", fonte_pac)
                c.drawString(x0 + pos.get("pacote_x", 5.0) * mm,
                             base_top - pos.get("pacote_y", 25.0) * mm,
                             txt_pac)

                c.setFont("Helvetica", fonte_vol)
                c.drawString(x0 + pos.get("volume_x", 5.0) * mm,
                             base_top - pos.get("volume_y", 31.0) * mm,
                             txt_vol)

                # ===== QR Code NOVO =====
                chave = gerar_chave_unica()
                vol_atual = str(contador)
                vol_total = str(total_volumes)
                qtd_pacote = str(pacote).zfill(3)

                qr_payload = f"{codigo}|{lote}|{qtd_pacote}|{descricao}|{vol_atual}|{vol_total}|{chave}"

                qr_img = make_qr_image(qr_payload, size_px=600)
                buf = BytesIO()
                qr_img.save(buf, format="PNG")
                buf.seek(0)

                c.drawImage(
                    ImageReader(buf),
                    x0 + qr_x_mm * mm,
                    y0 + qr_y_mm * mm,
                    qr_sz_mm * mm,
                    qr_sz_mm * mm,
                    preserveAspectRatio=True,
                    mask='auto'
                )

                contador += 1

            if p < paginas - 1:
                c.showPage()

        c.save()
        webbrowser.open_new_tab(os.path.abspath(nome_arquivo))
        messagebox.showinfo("Sucesso", f"{total_volumes} etiquetas geradas em {paginas} página(s).")
    except Exception as e:
        messagebox.showerror("Erro", str(e))

# ==========================================================
# INTERFACE PRINCIPAL
# ==========================================================
def gerar_etiqueta():
    dados = {
        "lote": entry_lote.get(),
        "codigo_produto": entry_codigo.get(),
        "descricao": text_desc.get("1.0", tk.END).strip(),
        "pacote": entry_pacote.get(),
        "total_volumes": entry_volume.get(),
        "quantidade": entry_qtd_pag.get()
    }
    if not dados["lote"] or not dados["codigo_produto"] or not dados["descricao"] \
       or not dados["pacote"] or not dados["total_volumes"] or not dados["quantidade"]:
        messagebox.showwarning("Atenção", "Preencha todos os campos.")
        return
    gerar_pdf(dados)

def limpar_campos():
    entry_lote.delete(0, tk.END)
    entry_codigo.delete(0, tk.END)
    text_desc.delete("1.0", tk.END)
    entry_pacote.delete(0, tk.END)
    entry_volume.delete(0, tk.END)
    entry_qtd_pag.delete(0, tk.END)

    entry_lote.insert(0, "25-004855")
    entry_codigo.insert(0, "132483")
    text_desc.insert("1.0", "Tbe IPP 200L AZ 10,3 KG RE BJBR SL Tolerancia MIN10,0 KG - ECZLJ")
    entry_pacote.insert(0, "008")
    entry_volume.insert(0, "480")
    entry_qtd_pag.insert(0, "18")

# ---- Janela
root = tk.Tk()
root.title("Gerador de Etiquetas - Versão 13")
root.geometry("880x640")
root.minsize(860, 620)

try:
    style = ttk.Style()
    if "vista" in style.theme_names():
        style.theme_use("vista")
    else:
        style.theme_use("clam")
    style.configure("TLabel", padding=2)
    style.configure("TButton", padding=6)
except Exception:
    pass

frm = ttk.LabelFrame(root, text="Dados da Etiqueta")
frm.pack(fill="x", padx=12, pady=12)

ttk.Label(frm, text="Número do Lote (OS)").grid(row=0, column=0, sticky="w", padx=6, pady=6)
entry_lote = ttk.Entry(frm, width=22)
entry_lote.grid(row=0, column=1, sticky="w", padx=6, pady=6)

ttk.Label(frm, text="Código do Produto").grid(row=1, column=0, sticky="w", padx=6, pady=6)
entry_codigo = ttk.Entry(frm, width=22)
entry_codigo.grid(row=1, column=1, sticky="w", padx=6, pady=6)

ttk.Label(frm, text="Descrição").grid(row=2, column=0, sticky="nw", padx=6, pady=6)
text_desc = tk.Text(frm, width=50, height=4)
text_desc.grid(row=2, column=1, sticky="w", padx=6, pady=6)

ttk.Label(frm, text="Pacote").grid(row=3, column=0, sticky="w", padx=6, pady=6)
entry_pacote = ttk.Entry(frm, width=10)
entry_pacote.grid(row=3, column=1, sticky="w", padx=6, pady=6)

ttk.Label(frm, text="Volume total").grid(row=4, column=0, sticky="w", padx=6, pady=6)
entry_volume = ttk.Entry(frm, width=10)
entry_volume.grid(row=4, column=1, sticky="w", padx=6, pady=6)

frm2 = ttk.Frame(root)
frm2.pack(fill="x", padx=12, pady=(0,12))
ttk.Label(frm2, text="Quantidade por Página (1–18):").pack(side="left", padx=6)
entry_qtd_pag = ttk.Entry(frm2, width=5)
entry_qtd_pag.pack(side="left", padx=6)

btns = ttk.Frame(root)
btns.pack(fill="x", padx=12, pady=8)
ttk.Button(btns, text="Configurar Tamanho", command=abrir_editor_tamanho).pack(side="left", padx=6)
ttk.Button(btns, text="Configurar Posição", command=abrir_editor_posicao).pack(side="left", padx=6)
ttk.Button(btns, text="Configurar Margens", command=abrir_editor_margens).pack(side="left", padx=6)
ttk.Button(btns, text="Gerar Etiqueta", command=gerar_etiqueta).pack(side="left", padx=6)
ttk.Button(btns, text="Limpar", command=limpar_campos).pack(side="left", padx=6)

limpar_campos()
root.mainloop()