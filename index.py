import tkinter as tk
from tkinter import ttk, messagebox
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
import qrcode
import json
from io import BytesIO

# ------------------------------------------
# FUNÇÕES DE CONFIGURAÇÃO
# ------------------------------------------
def carregar_configuracao(arquivo):
    try:
        with open(arquivo, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def salvar_configuracao(arquivo, dados):
    try:
        with open(arquivo, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=4, ensure_ascii=False)
        messagebox.showinfo("Sucesso", f"Configuração salva em {arquivo}.")
    except Exception as e:
        messagebox.showerror("Erro", f"Falha ao salvar {arquivo}: {e}")

# ------------------------------------------
# CARREGAR CONFIGURAÇÕES JSON
# ------------------------------------------
CONFIG_TAMANHO = carregar_configuracao("config_tamanho.json")
CONFIG_MARGENS = carregar_configuracao("config_margens.json")
CONFIG_POS = carregar_configuracao("config_posicionamento.json")

# ------------------------------------------
# FUNÇÃO PARA EDITAR CONFIGURAÇÕES
# ------------------------------------------
def abrir_editor_config(titulo, config_dict, arquivo):
    janela = tk.Toplevel(root)
    janela.title(titulo)
    janela.geometry("500x400")

    entradas = {}
    row = 0
    for chave, valor in config_dict.items():
        ttk.Label(janela, text=f"{chave.replace('_', ' ').capitalize()}").grid(row=row, column=0, padx=10, pady=5, sticky="w")
        entrada = ttk.Entry(janela, width=15)
        entrada.insert(0, valor)
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

# ------------------------------------------
# FUNÇÃO PARA GERAR O PDF
# ------------------------------------------
def gerar_pdf(dados):
    try:
        nome_arquivo = "etiquetas.pdf"
        c = canvas.Canvas(nome_arquivo, pagesize=A4)

        LARGURA_ETIQUETA = CONFIG_TAMANHO.get("etiqueta_largura", 100) * mm
        ALTURA_ETIQUETA = CONFIG_TAMANHO.get("etiqueta_altura", 35) * mm
        MARGEM_ESQ = CONFIG_TAMANHO.get("margem_esquerda", 5) * mm
        MARGEM_SUP = CONFIG_TAMANHO.get("margem_superior", 5) * mm
        ESPACO_H = CONFIG_TAMANHO.get("espacamento_colunas", 3) * mm
        ESPACO_V = CONFIG_TAMANHO.get("espacamento_colunas", 3) * mm

        etiquetas_geradas = int(dados["quantidade"])

        linha = 0
        coluna = 0

        for i in range(1, etiquetas_geradas + 1):
            x = MARGEM_ESQ + coluna * (LARGURA_ETIQUETA + ESPACO_H)
            y = A4[1] - MARGEM_SUP - (linha + 1) * (ALTURA_ETIQUETA + ESPACO_V)

            # --- Texto principal ---
            codigo = dados["codigo_produto"]
            descricao = dados["descricao"]
            lote = f"OS{dados['lote']}"
            pacote = f"PACOTE COM {dados['pacote']} UN"
            volume = f"VOLUME {i}/{dados['total_volumes']}"

            primeira_linha = f"{codigo} / {descricao}"

            # --- QRCode no formato solicitado ---
            qr_texto = f"|{codigo}|{lote}|{dados['pacote']}|{descricao}"
            qr = qrcode.make(qr_texto)
            buffer = BytesIO()
            qr.save(buffer, format="PNG")
            buffer.seek(0)
            img = ImageReader(buffer)

            # --- Posições e fontes ---
            c.setFont("Helvetica-Bold", CONFIG_POS.get("codigo_fonte", 10))
            c.drawString(x + CONFIG_POS.get("codigo_x", 2) * mm,
                         y + ALTURA_ETIQUETA - CONFIG_POS.get("codigo_y", 2) * mm,
                         primeira_linha)

            c.setFont("Helvetica", CONFIG_POS.get("lote_fonte", 9))
            c.drawString(x + CONFIG_POS.get("lote_x", 2) * mm,
                         y + ALTURA_ETIQUETA - CONFIG_POS.get("lote_y", 12) * mm,
                         f"Número do Lote: {lote}")

            c.setFont("Helvetica", CONFIG_POS.get("pacote_fonte", 9))
            c.drawString(x + CONFIG_POS.get("pacote_x", 2) * mm,
                         y + ALTURA_ETIQUETA - CONFIG_POS.get("pacote_y", 16) * mm,
                         pacote)

            c.setFont("Helvetica", CONFIG_POS.get("volume_fonte", 9))
            c.drawString(x + CONFIG_POS.get("volume_x", 2) * mm,
                         y + ALTURA_ETIQUETA - CONFIG_POS.get("volume_y", 20) * mm,
                         volume)

            # --- QRCode ---
            c.drawImage(img,
                        x + CONFIG_POS.get("qr_code_x", 60) * mm,
                        y + CONFIG_POS.get("qr_code_y", 2) * mm,
                        CONFIG_POS.get("qr_code_tamanho", 20) * mm,
                        CONFIG_POS.get("qr_code_tamanho", 20) * mm)

            # Controle de posição
            coluna += 1
            if coluna >= 2:
                coluna = 0
                linha += 1

            if linha >= 7:
                c.showPage()
                linha = 0

        c.save()
        messagebox.showinfo("Sucesso", f"{etiquetas_geradas} etiqueta(s) gerada(s) com sucesso!")

    except Exception as e:
        messagebox.showerror("Erro", f"Falha ao gerar etiquetas:\n{e}")

# ------------------------------------------
# FUNÇÕES AUXILIARES
# ------------------------------------------
def gerar_etiqueta():
    try:
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
    except Exception as e:
        messagebox.showerror("Erro", str(e))

def limpar_campos():
    for entry in [entry_lote, entry_codigo, entry_pacote, entry_volume, entry_pos]:
        entry.delete(0, tk.END)
    text_desc.delete("1.0", tk.END)

# ------------------------------------------
# INTERFACE TKINTER
# ------------------------------------------
root = tk.Tk()
root.title("Gerador de Etiquetas - Versão 4")
root.geometry("820x600")

frame = ttk.LabelFrame(root, text="Dados da Etiqueta")
frame.pack(fill="x", padx=10, pady=10)

# Campos principais
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

# Posição
pos_frame = ttk.Frame(root)
pos_frame.pack(fill="x", padx=10, pady=5)
ttk.Label(pos_frame, text="Posição da Etiqueta (1–14):").pack(side="left", padx=5)
entry_pos = ttk.Entry(pos_frame, width=5)
entry_pos.insert(0, "14")
entry_pos.pack(side="left", padx=5)

# Botões
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
