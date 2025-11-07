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

# ----------------------------
# Função: carregar arquivo JSON
# ----------------------------
def carregar_configuracao(arquivo):
    try:
        with open(arquivo, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        messagebox.showerror("Erro", f"Falha ao carregar {arquivo}: {e}")
        return {}

# ----------------------------
# Carregar configurações
# ----------------------------
CONFIG_TAMANHO = carregar_configuracao("config_tamanho.json")
CONFIG_MARGENS = carregar_configuracao("config_margens.json")
CONFIG_POS = carregar_configuracao("config_posicionamento.json")

# Valores padrão (caso JSON esteja vazio)
LARGURA_ETIQUETA = CONFIG_TAMANHO.get("etiqueta_largura", 100) * mm
ALTURA_ETIQUETA = CONFIG_TAMANHO.get("etiqueta_altura", 35) * mm
MARGEM_ESQ = CONFIG_TAMANHO.get("margem_esquerda", 5) * mm
MARGEM_SUP = CONFIG_TAMANHO.get("margem_superior", 5) * mm
ESPACO_H = CONFIG_TAMANHO.get("espacamento_colunas", 3) * mm
ESPACO_V = CONFIG_TAMANHO.get("espacamento_colunas", 3) * mm

# ----------------------------
# Funções principais
# ----------------------------
def gerar_pdf(dados):
    try:
        nome_arquivo = "etiquetas.pdf"
        c = canvas.Canvas(nome_arquivo, pagesize=A4)

        linha = 0
        coluna = 0

        for i in range(1, 15):
            x = MARGEM_ESQ + coluna * (LARGURA_ETIQUETA + ESPACO_H)
            y = A4[1] - MARGEM_SUP - (linha + 1) * (ALTURA_ETIQUETA + ESPACO_V)

            # Textos conforme configuração
            c.setFont("Helvetica-Bold", CONFIG_POS.get("codigo_fonte", 10))
            c.drawString(x + CONFIG_POS.get("codigo_x", 2) * mm,
                         y + ALTURA_ETIQUETA - CONFIG_POS.get("codigo_y", 2) * mm,
                         dados["codigo_produto"])

            c.setFont("Helvetica", CONFIG_POS.get("descricao_fonte", 9))
            c.drawString(x + CONFIG_POS.get("descricao_x", 2) * mm,
                         y + ALTURA_ETIQUETA - CONFIG_POS.get("descricao_y", 8) * mm,
                         dados["descricao"])

            c.setFont("Helvetica", CONFIG_POS.get("lote_fonte", 9))
            c.drawString(x + CONFIG_POS.get("lote_x", 2) * mm,
                         y + ALTURA_ETIQUETA - CONFIG_POS.get("lote_y", 12) * mm,
                         f"Lote: {dados['lote']}")

            c.setFont("Helvetica", CONFIG_POS.get("pacote_fonte", 9))
            c.drawString(x + CONFIG_POS.get("pacote_x", 2) * mm,
                         y + ALTURA_ETIQUETA - CONFIG_POS.get("pacote_y", 16) * mm,
                         f"Pacote: {dados['pacote']}")

            c.setFont("Helvetica", CONFIG_POS.get("volume_fonte", 9))
            c.drawString(x + CONFIG_POS.get("volume_x", 2) * mm,
                         y + ALTURA_ETIQUETA - CONFIG_POS.get("volume_y", 20) * mm,
                         f"Volume {i}/{dados['total_volumes']}")

            # QR Code
            qr_data = f"{dados['codigo_produto']} | Lote: {dados['lote']} | Vol {i}/{dados['total_volumes']}"
            qr = qrcode.make(qr_data)
            buffer = BytesIO()
            qr.save(buffer, format="PNG")
            buffer.seek(0)
            img = ImageReader(buffer)
            c.drawImage(img,
                        x + CONFIG_POS.get("qr_code_x", 60) * mm,
                        y + CONFIG_POS.get("qr_code_y", 2) * mm,
                        CONFIG_POS.get("qr_code_tamanho", 20) * mm,
                        CONFIG_POS.get("qr_code_tamanho", 20) * mm)

            # Atualizar posição
            coluna += 1
            if coluna >= 2:
                coluna = 0
                linha += 1

            if linha >= 7:
                c.showPage()
                linha = 0

        c.save()
        messagebox.showinfo("Sucesso", f"Arquivo '{nome_arquivo}' gerado com sucesso!")

    except Exception as e:
        messagebox.showerror("Erro", f"Falha ao gerar etiquetas:\n{e}")

def gerar_etiqueta():
    dados = {
        "lote": entry_lote.get(),
        "codigo_produto": entry_codigo.get(),
        "descricao": text_desc.get("1.0", tk.END).strip(),
        "pacote": entry_pacote.get(),
        "total_volumes": entry_volume.get(),
    }

    if not all(dados.values()):
        messagebox.showwarning("Campos obrigatórios", "Preencha todos os campos antes de gerar a etiqueta.")
        return

    gerar_pdf(dados)

def limpar_campos():
    for entry in [entry_lote, entry_codigo, entry_pacote, entry_volume]:
        entry.delete(0, tk.END)
    text_desc.delete("1.0", tk.END)

# ----------------------------
# Funções dos botões de configuração
# ----------------------------
def configurar_tamanho():
    messagebox.showinfo("Configuração de Tamanho",
                        json.dumps(CONFIG_TAMANHO, indent=4, ensure_ascii=False))

def configurar_posicao():
    messagebox.showinfo("Configuração de Posição",
                        json.dumps(CONFIG_POS, indent=4, ensure_ascii=False))

def configurar_margens():
    messagebox.showinfo("Configuração de Margens",
                        json.dumps(CONFIG_MARGENS, indent=4, ensure_ascii=False))

def imprimir():
    messagebox.showinfo("Imprimir", "Esta função enviará o PDF direto para a impressora (a ser implementada).")

# ----------------------------
# Interface Tkinter
# ----------------------------
root = tk.Tk()
root.title("Gerador de Etiquetas - Versão 3")
root.geometry("820x600")

frame = ttk.LabelFrame(root, text="Dados da Etiqueta")
frame.pack(fill="x", padx=10, pady=10)

# Campos de entrada
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

# Campo da posição
pos_frame = ttk.Frame(root)
pos_frame.pack(fill="x", padx=10, pady=5)
ttk.Label(pos_frame, text="Posição da Etiqueta (1–14):").pack(side="left", padx=5)
entry_pos = ttk.Entry(pos_frame, width=5)
entry_pos.insert(0, "1")
entry_pos.pack(side="left", padx=5)

# Botões
btn_frame = ttk.Frame(root)
btn_frame.pack(fill="x", padx=10, pady=10)

ttk.Button(btn_frame, text="Configurar Tamanho", command=configurar_tamanho).pack(side="left", padx=5)
ttk.Button(btn_frame, text="Configurar Posição", command=configurar_posicao).pack(side="left", padx=5)
ttk.Button(btn_frame, text="Configurar Margens", command=configurar_margens).pack(side="left", padx=5)
ttk.Button(btn_frame, text="Gerar Etiqueta", command=gerar_etiqueta).pack(side="left", padx=5)
ttk.Button(btn_frame, text="Imprimir", command=imprimir).pack(side="left", padx=5)
ttk.Button(btn_frame, text="Limpar", command=limpar_campos).pack(side="left", padx=5)

root.mainloop()
