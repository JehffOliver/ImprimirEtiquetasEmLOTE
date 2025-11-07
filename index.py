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

# ============================================
# ARQUIVOS DE CONFIGURAÇÃO PADRÃO
# ============================================
PADRAO_TAMANHO = {
    "etiqueta_largura": 104.5,
    "etiqueta_altura": 34.0,
    "margem_esquerda": 6.0,
    "margem_superior": 12.0,
    "espacamento_colunas": 3.0,
    "qr_code_x": 80.0,
    "qr_code_y": 6.0,
    "qr_code_tamanho": 22.0
}

PADRAO_MARGENS = {
    "margem_superior_pagina": 0.0,
    "margem_inferior_pagina": 0.0,
    "margem_esquerda_pagina": 0.0,
    "margem_direita_pagina": 0.0
}

PADRAO_POS = {
    "codigo_x": 5.0,
    "codigo_y": 8.0,
    "codigo_fonte": 10.0,
    "descricao_x": 5.0,
    "descricao_y": 14.0,
    "descricao_fonte": 9.0,
    "lote_x": 5.0,
    "lote_y": 21.0,
    "lote_fonte": 9.0,
    "pacote_x": 5.0,
    "pacote_y": 27.0,
    "pacote_fonte": 9.0,
    "volume_x": 5.0,
    "volume_y": 33.0,
    "volume_fonte": 9.0
}

# ============================================
# FUNÇÕES DE CONFIGURAÇÃO E SALVAMENTO
# ============================================
def garantir_json(nome, padrao):
    if not os.path.exists(nome):
        with open(nome, "w", encoding="utf-8") as f:
            json.dump(padrao, f, indent=4, ensure_ascii=False)
    with open(nome, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return padrao

CONFIG_TAMANHO = garantir_json("config_tamanho.json", PADRAO_TAMANHO)
CONFIG_MARGENS = garantir_json("config_margens.json", PADRAO_MARGENS)
CONFIG_POS = garantir_json("config_posicionamento.json", PADRAO_POS)

def salvar_configuracao(arquivo, dados):
    with open(arquivo, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)
    messagebox.showinfo("Sucesso", f"Configuração salva em {arquivo}")

def abrir_editor_config(titulo, config_dict, arquivo):
    janela = tk.Toplevel(root)
    janela.title(titulo)
    janela.geometry("450x450")
    entradas = {}

    ttk.Label(janela, text="Editar configurações:").grid(row=0, column=0, columnspan=2, pady=10)
    row = 1
    for chave, valor in config_dict.items():
        ttk.Label(janela, text=chave.replace("_", " ").capitalize()).grid(row=row, column=0, sticky="w", padx=10, pady=5)
        entrada = ttk.Entry(janela, width=15)
        entrada.insert(0, str(valor))
        entrada.grid(row=row, column=1, padx=10, pady=5)
        entradas[chave] = entrada
        row += 1

    def salvar():
        for k, v in entradas.items():
            try:
                config_dict[k] = float(v.get())
            except:
                config_dict[k] = v.get()
        salvar_configuracao(arquivo, config_dict)
        janela.destroy()

    ttk.Button(janela, text="Salvar", command=salvar).grid(row=row, column=0, pady=15)
    ttk.Button(janela, text="Cancelar", command=janela.destroy).grid(row=row, column=1, pady=15)

# ============================================
# FUNÇÃO PRINCIPAL DE GERAÇÃO DO PDF
# ============================================
def gerar_pdf(dados):
    try:
        nome_arquivo = "etiquetas.pdf"
        c = canvas.Canvas(nome_arquivo, pagesize=A4)

        LARGURA = CONFIG_TAMANHO.get("etiqueta_largura", 104.5) * mm
        ALTURA = CONFIG_TAMANHO.get("etiqueta_altura", 34.0) * mm
        MARGEM_ESQ = CONFIG_TAMANHO.get("margem_esquerda", 6.0) * mm
        MARGEM_SUP = CONFIG_TAMANHO.get("margem_superior", 12.0) * mm
        ESPACO_H = CONFIG_TAMANHO.get("espacamento_colunas", 3.0) * mm

        etiquetas_geradas = int(dados["quantidade"])
        linha, coluna = 0, 0

        for i in range(1, etiquetas_geradas + 1):
            x = MARGEM_ESQ + coluna * (LARGURA + ESPACO_H)
            y = A4[1] - MARGEM_SUP - (linha + 1) * ALTURA

            # Dados
            codigo = dados["codigo_produto"]
            descricao = dados["descricao"]
            lote = f"OS{dados['lote']}"
            pacote = f"PACOTE COM {dados['pacote']} UN"
            volume = f"VOLUME {i}/{dados['total_volumes']}"

            primeira_linha = f"{codigo} / {descricao}"

            # QR CODE
            qr_texto = f"|{codigo}|{lote}|{dados['pacote']}|{descricao}"
            qr = qrcode.make(qr_texto)
            buf = BytesIO()
            qr.save(buf, format="PNG")
            buf.seek(0)
            img = ImageReader(buf)

            # Texto alinhado
            c.setFont("Helvetica-Bold", CONFIG_POS.get("codigo_fonte", 10))
            c.drawString(x + CONFIG_POS.get("codigo_x", 5) * mm,
                         y + ALTURA - CONFIG_POS.get("codigo_y", 8) * mm,
                         primeira_linha)

            c.setFont("Helvetica", CONFIG_POS.get("lote_fonte", 9))
            c.drawString(x + CONFIG_POS.get("lote_x", 5) * mm,
                         y + ALTURA - CONFIG_POS.get("lote_y", 21) * mm,
                         f"Número do Lote: {lote}")

            c.setFont("Helvetica", CONFIG_POS.get("pacote_fonte", 9))
            c.drawString(x + CONFIG_POS.get("pacote_x", 5) * mm,
                         y + ALTURA - CONFIG_POS.get("pacote_y", 27) * mm,
                         pacote)

            c.setFont("Helvetica", CONFIG_POS.get("volume_fonte", 9))
            c.drawString(x + CONFIG_POS.get("volume_x", 5) * mm,
                         y + ALTURA - CONFIG_POS.get("volume_y", 33) * mm,
                         volume)

            # QR code posicionado à direita
            c.drawImage(img,
                        x + CONFIG_TAMANHO.get("qr_code_x", 80) * mm,
                        y + CONFIG_TAMANHO.get("qr_code_y", 6) * mm,
                        CONFIG_TAMANHO.get("qr_code_tamanho", 22) * mm,
                        CONFIG_TAMANHO.get("qr_code_tamanho", 22) * mm)

            coluna += 1
            if coluna >= 2:
                coluna = 0
                linha += 1
            if linha >= 7:
                c.showPage()
                linha = 0

        c.save()
        webbrowser.open_new_tab(nome_arquivo)
        messagebox.showinfo("Sucesso", f"{etiquetas_geradas} etiqueta(s) gerada(s) e aberta(s) com sucesso!")
    except Exception as e:
        messagebox.showerror("Erro", f"Falha ao gerar etiquetas:\n{e}")

# ============================================
# FUNÇÕES AUXILIARES
# ============================================
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
        messagebox.showwarning("Campos obrigatórios", "Preencha todos os campos antes de gerar.")
        return
    gerar_pdf(dados)

def limpar_campos():
    for entry in [entry_lote, entry_codigo, entry_pacote, entry_volume, entry_pos]:
        entry.delete(0, tk.END)
    text_desc.delete("1.0", tk.END)

# ============================================
# INTERFACE TKINTER
# ============================================
root = tk.Tk()
root.title("Gerador de Etiquetas - Versão 5")
root.geometry("820x600")

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
ttk.Label(pos_frame, text="Posição da Etiqueta (1–14):").pack(side="left", padx=5)
entry_pos = ttk.Entry(pos_frame, width=5)
entry_pos.insert(0, "14")
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
