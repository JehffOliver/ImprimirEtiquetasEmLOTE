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
import textwrap

# ==========================================================
# CONFIGURAÇÕES PADRÃO
# ==========================================================
PADRAO_TAMANHO = {
    "etiqueta_largura": 104.5,
    "etiqueta_altura": 35.0,
    "margem_esquerda": 0.0,
    "margem_superior": 0.0,
    "espacamento_colunas": 2.0,
    "qr_code_x": 80.0,
    "qr_code_y": 11.0,
    "qr_code_tamanho": 22.0
}

PADRAO_MARGENS = {
    "margem_superior_pagina": 0.0,
    "margem_inferior_pagina": 0.0,
    "margem_esquerda_pagina": 0.0,
    "margem_direita_pagina": 0.0
}

PADRAO_POS = {
    "codigo_x": 5.0, "codigo_y": 8.0, "codigo_fonte": 10.0,
    "descricao_x": 5.0, "descricao_y": 14.0, "descricao_fonte": 9.0,
    "lote_x": 5.0, "lote_y": 21.0, "lote_fonte": 9.0,
    "pacote_x": 5.0, "pacote_y": 27.0, "pacote_fonte": 9.0,
    "volume_x": 5.0, "volume_y": 33.0, "volume_fonte": 9.0,
    "qr_code_x": 80.0, "qr_code_y": 11.0, "qr_code_tamanho": 22.0
}

# ==========================================================
# GARANTIR EXISTÊNCIA DOS JSONS
# ==========================================================
def garantir_json(nome, padrao):
    """Cria o JSON se não existir e adiciona chaves ausentes."""
    if not os.path.exists(nome):
        with open(nome, "w", encoding="utf-8") as f:
            json.dump(padrao, f, indent=4, ensure_ascii=False)

    with open(nome, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except:
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
CONFIG_POS = garantir_json("config_posicionamento.json", PADRAO_POS)

def salvar_configuracao(arquivo, dados):
    with open(arquivo, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)
    messagebox.showinfo("Sucesso", f"Configuração salva em {arquivo}")

# ==========================================================
# EDITOR DE CONFIGURAÇÕES (CAIXAS ORGANIZADAS)
# ==========================================================
def abrir_editor_config(titulo, config_dict, arquivo):
    janela = tk.Toplevel(root)
    janela.title(titulo)
    janela.geometry("950x600")

    canvas_frame = tk.Canvas(janela)
    scrollbar = ttk.Scrollbar(janela, orient="vertical", command=canvas_frame.yview)
    scrollable_frame = ttk.Frame(canvas_frame)

    scrollable_frame.bind("<Configure>", lambda e: canvas_frame.configure(scrollregion=canvas_frame.bbox("all")))
    canvas_frame.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas_frame.configure(yscrollcommand=scrollbar.set)
    canvas_frame.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    ttk.Label(scrollable_frame, text="Editar configurações (organizadas por seção):", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, columnspan=3, pady=10)

    # Cria frames lado a lado
    grupos = {
        "Código": ["codigo_x", "codigo_y", "codigo_fonte"],
        "Descrição": ["descricao_x", "descricao_y", "descricao_fonte"],
        "Lote": ["lote_x", "lote_y", "lote_fonte"],
        "Pacote": ["pacote_x", "pacote_y", "pacote_fonte"],
        "Volume": ["volume_x", "volume_y", "volume_fonte"],
        "QR Code": ["qr_code_x", "qr_code_y", "qr_code_tamanho"]
    }

    entradas = {}
    col = 0
    for titulo_grupo, campos in grupos.items():
        frame_grupo = ttk.LabelFrame(scrollable_frame, text=titulo_grupo, padding=10)
        frame_grupo.grid(row=1, column=col, padx=10, pady=10, sticky="n")
        col += 1

        for i, campo in enumerate(campos):
            ttk.Label(frame_grupo, text=campo.replace("_", " ").capitalize()).grid(row=i, column=0, sticky="w", padx=5, pady=3)
            entrada = ttk.Entry(frame_grupo, width=10)
            entrada.insert(0, str(config_dict.get(campo, "")))
            entrada.grid(row=i, column=1, padx=5, pady=3)
            entradas[campo] = entrada

    def salvar():
        for k, v in entradas.items():
            try:
                config_dict[k] = float(v.get())
            except:
                config_dict[k] = v.get()
        salvar_configuracao(arquivo, config_dict)
        janela.destroy()

    ttk.Button(scrollable_frame, text="Salvar", command=salvar).grid(row=2, column=0, pady=20)
    ttk.Button(scrollable_frame, text="Cancelar", command=janela.destroy).grid(row=2, column=1, pady=20)

# ==========================================================
# GERAR ETIQUETAS
# ==========================================================
def gerar_pdf(dados):
    try:
        nome_arquivo = "etiquetas.pdf"
        c = canvas.Canvas(nome_arquivo, pagesize=A4)

        LARGURA = CONFIG_TAMANHO["etiqueta_largura"] * mm
        ALTURA = CONFIG_TAMANHO["etiqueta_altura"] * mm
        MARGEM_ESQ = CONFIG_TAMANHO["margem_esquerda"] * mm
        MARGEM_SUP = CONFIG_TAMANHO["margem_superior"] * mm
        ESPACO_H = CONFIG_TAMANHO["espacamento_colunas"] * mm

        etiquetas_geradas = int(dados["quantidade"])
        linha, coluna = 0, 0

        for i in range(1, etiquetas_geradas + 1):
            x = MARGEM_ESQ + coluna * (LARGURA + ESPACO_H)
            y = A4[1] - MARGEM_SUP - (linha + 1) * ALTURA

            codigo = dados["codigo_produto"]
            descricao = dados["descricao"]
            lote = f"OS{dados['lote']}"
            pacote = f"PACOTE COM {dados['pacote']} UN"
            volume = f"VOLUME {i}/{dados['total_volumes']}"
            primeira_linha = f"{codigo} /"

            # Divide descrição longa em até 2 linhas
            descricao_linhas = textwrap.wrap(descricao, width=50)[:2]

            # QR CODE
            qr_texto = f"|{codigo}|{lote}|{dados['pacote']}|{descricao}"
            qr = qrcode.make(qr_texto)
            buf = BytesIO()
            qr.save(buf, format="PNG")
            buf.seek(0)
            img = ImageReader(buf)

            # Texto principal
            c.setFont("Helvetica-Bold", CONFIG_POS["codigo_fonte"])
            c.drawString(x + CONFIG_POS["codigo_x"] * mm,
                         y + ALTURA - CONFIG_POS["codigo_y"] * mm,
                         primeira_linha)

            c.setFont("Helvetica", CONFIG_POS["descricao_fonte"])
            for j, linha_desc in enumerate(descricao_linhas):
                c.drawString(x + CONFIG_POS["descricao_x"] * mm,
                             y + ALTURA - (CONFIG_POS["descricao_y"] + j * 4) * mm,
                             linha_desc)

            c.setFont("Helvetica", CONFIG_POS["lote_fonte"])
            c.drawString(x + CONFIG_POS["lote_x"] * mm,
                         y + ALTURA - CONFIG_POS["lote_y"] * mm,
                         f"Número do Lote: {lote}")

            c.setFont("Helvetica", CONFIG_POS["pacote_fonte"])
            c.drawString(x + CONFIG_POS["pacote_x"] * mm,
                         y + ALTURA - CONFIG_POS["pacote_y"] * mm,
                         pacote)

            c.setFont("Helvetica", CONFIG_POS["volume_fonte"])
            c.drawString(x + CONFIG_POS["volume_x"] * mm,
                         y + ALTURA - CONFIG_POS["volume_y"] * mm,
                         volume)

            # QR Code alinhado
            c.drawImage(img,
                        x + CONFIG_POS["qr_code_x"] * mm,
                        y + CONFIG_POS["qr_code_y"] * mm,
                        CONFIG_POS["qr_code_tamanho"] * mm,
                        CONFIG_POS["qr_code_tamanho"] * mm)

            coluna += 1
            if coluna >= 2:
                coluna = 0
                linha += 1
            if linha >= 8:
                c.showPage()
                linha = 0

        c.save()
        webbrowser.open_new_tab(nome_arquivo)
        messagebox.showinfo("Sucesso", "Etiquetas geradas e abertas automaticamente!")
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
        "quantidade": entry_pos.get()
    }
    if not all(dados.values()):
        messagebox.showwarning("Campos obrigatórios", "Preencha todos os campos.")
        return
    gerar_pdf(dados)

def limpar_campos():
    for e in [entry_lote, entry_codigo, entry_pacote, entry_volume, entry_pos]:
        e.delete(0, tk.END)
    text_desc.delete("1.0", tk.END)

# ==========================================================
# TKINTER PRINCIPAL
# ==========================================================
root = tk.Tk()
root.title("Gerador de Etiquetas - Versão 9")
root.geometry("850x620")

frame = ttk.LabelFrame(root, text="Dados da Etiqueta")
frame.pack(fill="x", padx=10, pady=10)

ttk.Label(frame, text="Número do Lote (OS)").grid(row=0, column=0, sticky="w", padx=5, pady=5)
entry_lote = ttk.Entry(frame, width=25)
entry_lote.grid(row=0, column=1, padx=5, pady=5)

ttk.Label(frame, text="Código do Produto").grid(row=1, column=0, sticky="w", padx=5, pady=5)
entry_codigo = ttk.Entry(frame, width=25)
entry_codigo.grid(row=1, column=1, padx=5, pady=5)

ttk.Label(frame, text="Descrição").grid(row=2, column=0, sticky="nw", padx=5, pady=5)
text_desc = tk.Text(frame, width=40, height=4)
text_desc.grid(row=2, column=1, padx=5, pady=5)

ttk.Label(frame, text="Pacote").grid(row=3, column=0, sticky="w", padx=5, pady=5)
entry_pacote = ttk.Entry(frame, width=10)
entry_pacote.grid(row=3, column=1, sticky="w", padx=5, pady=5)

ttk.Label(frame, text="Volume total").grid(row=4, column=0, sticky="w", padx=5, pady=5)
entry_volume = ttk.Entry(frame, width=10)
entry_volume.grid(row=4, column=1, sticky="w", padx=5, pady=5)

pos_frame = ttk.Frame(root)
pos_frame.pack(fill="x", padx=10, pady=5)
ttk.Label(pos_frame, text="Quantidade por Página (1–16):").pack(side="left", padx=5)
entry_pos = ttk.Entry(pos_frame, width=5)
entry_pos.insert(0, "16")
entry_pos.pack(side="left", padx=5)

btn_frame = ttk.Frame(root)
btn_frame.pack(fill="x", padx=10, pady=10)

ttk.Button(btn_frame, text="Configurar Tamanho",
           command=lambda: abrir_editor_config("Configurações de Tamanho", CONFIG_TAMANHO, "config_tamanho.json")).pack(side="left", padx=5)
ttk.Button(btn_frame, text="Configurar Posição",
           command=lambda: abrir_editor_config("Configurações de Posição", CONFIG_POS, "config_posicionamento.json")).pack(side="left", padx=5)
ttk.Button(btn_frame, text="Configurar Margens",
           command=lambda: abrir_editor_config("Configurações de Margens", CONFIG_MARGENS, "config_margens.json")).pack(side="left", padx=5)
ttk.Button(btn_frame, text="Gerar Etiqueta", command=gerar_etiqueta).pack(side="left", padx=5)
ttk.Button(btn_frame, text="Limpar", command=limpar_campos).pack(side="left", padx=5)

root.mainloop()
