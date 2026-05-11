# -*- coding: utf-8 -*-
# Gerador de Etiquetas Zebra 100x40 mm - Seleção de Impressora
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
    return (
        str(texto)
        .replace("^", " ")
        .replace("~", " ")
        .replace("\r", " ")
        .replace("\n", " ")
    )

def quebrar_texto(texto, tamanho_max_linha=34, max_linhas=2):
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

def listar_impressoras():
    if win32print is None:
        return []

    nomes = []
    flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS

    try:
        impressoras = win32print.EnumPrinters(flags)
        for item in impressoras:
            # item pode ter formatos diferentes conforme o ambiente
            if isinstance(item, tuple):
                for valor in item:
                    if isinstance(valor, str) and valor.strip():
                        # normalmente o nome real vem no item[2]
                        pass
                if len(item) >= 3 and isinstance(item[2], str) and item[2].strip():
                    nomes.append(item[2].strip())
    except Exception as e:
        print("Erro ao listar impressoras:", e)

    nomes = sorted(list(set(nomes)))
    return nomes

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

def gerar_zpl_uma_etiqueta(codigo, descricao, lote, pacote, volume_atual, volume_total):
    codigo = zpl_escape(codigo)
    descricao = zpl_escape(descricao)
    lote = zpl_escape(ensure_os_prefix(lote))
    pacote = zpl_escape(str(pacote).zfill(3))
    volume_atual = zpl_escape(str(volume_atual))
    volume_total = zpl_escape(str(volume_total))
    chave = gerar_chave_unica()

    qr_payload = f"{codigo}|{lote}|{pacote}|{descricao}|{volume_atual}|{volume_total}|{chave}"

    texto_topo = f"{codigo} / {descricao}" if descricao else codigo
    linhas_desc = quebrar_texto(texto_topo, tamanho_max_linha=34, max_linhas=2)

    linha1 = linhas_desc[0] if len(linhas_desc) > 0 else ""
    linha2 = linhas_desc[1] if len(linhas_desc) > 1 else ""

    txt_lote = f"Lote: {lote}"
    txt_pac = f"Pacote com {pacote} UN"
    txt_vol = f"Volume {volume_atual}/{volume_total}"

    zpl = f"""
^XA
^PW{LABEL_WIDTH}
^LL{LABEL_HEIGHT}
^LH0,0
^CI28
^FO18,16^A0N,28,28^FD{linha1}^FS
"""

    if linha2:
        zpl += f"^FO18,48^A0N,28,28^FD{linha2}^FS\n"

    zpl += f"""
^FO18,96^A0N,25,25^FD{txt_lote}^FS
^FO18,128^A0N,25,25^FD{txt_pac}^FS
^FO18,160^A0N,28,28^FD{txt_vol}^FS
^FO590,40^BQN,2,5
^FDLA,{qr_payload}^FS
^XZ
"""
    return zpl.strip() + "\n"

def gerar_zpl_lote(dados, apenas_uma=False):
    lote = dados["lote"].strip()
    codigo = dados["codigo_produto"].strip()
    descricao = dados["descricao"].strip()
    pacote = dados["pacote"].strip()

    total_volumes = int(dados["total_volumes"])
    if total_volumes <= 0:
        raise ValueError("Volume total deve ser maior que zero.")

    fim = 1 if apenas_uma else total_volumes

    etiquetas = []
    for contador in range(1, fim + 1):
        etiquetas.append(
            gerar_zpl_uma_etiqueta(
                codigo=codigo,
                descricao=descricao,
                lote=lote,
                pacote=pacote,
                volume_atual=contador,
                volume_total=total_volumes,
            )
        )

    return "\n".join(etiquetas)

def coletar_dados():
    return {
        "lote": entry_lote.get(),
        "codigo_produto": entry_codigo.get(),
        "descricao": text_desc.get("1.0", tk.END).strip(),
        "pacote": entry_pacote.get(),
        "total_volumes": entry_volume.get()
    }

def validar_dados(dados):
    if not dados["lote"]:
        return "Preencha o lote."
    if not dados["codigo_produto"]:
        return "Preencha o código do produto."
    if not dados["descricao"]:
        return "Preencha a descrição."
    if not dados["pacote"]:
        return "Preencha o pacote."
    if not dados["total_volumes"]:
        return "Preencha o volume total."

    try:
        if int(dados["total_volumes"]) <= 0:
            return "Volume total deve ser maior que zero."
    except Exception:
        return "Volume total inválido."

    return None

def abrir_seletor_impressora():
    impressoras = listar_impressoras()

    if not impressoras:
        messagebox.showwarning(
            "Impressoras",
            "Nenhuma impressora foi encontrada.\n\n"
            "Confira se:\n"
            "1. a impressora está instalada no Windows;\n"
            "2. o pywin32 foi instalado no mesmo Python do sistema;\n"
            "3. a Zebra aparece em 'Dispositivos e Impressoras'."
        )
        return

    janela = tk.Toplevel(root)
    janela.title("Selecionar Impressora")
    janela.geometry("520x340")
    janela.transient(root)
    janela.grab_set()

    ttk.Label(janela, text="Selecione a impressora:").pack(anchor="w", padx=12, pady=(12, 6))

    lista = tk.Listbox(janela, height=12)
    lista.pack(fill="both", expand=True, padx=12, pady=6)

    for nome in impressoras:
        lista.insert(tk.END, nome)

    atual = entry_impressora.get().strip()
    if atual and atual in impressoras:
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

    btns = ttk.Frame(janela)
    btns.pack(pady=10)

    ttk.Button(btns, text="Selecionar", command=confirmar).pack(side="left", padx=6)
    ttk.Button(btns, text="Cancelar", command=janela.destroy).pack(side="left", padx=6)

def usar_padrao_windows():
    nome = obter_impressora_padrao_windows()
    if not nome:
        messagebox.showwarning("Atenção", "O Windows não possui impressora padrão configurada.")
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

def acao_imprimir(apenas_uma=False):
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

        zpl = gerar_zpl_lote(dados, apenas_uma=apenas_uma)
        imprimir_zpl_na_impressora(impressora, zpl)

        if apenas_uma:
            msg = f"1 etiqueta de teste enviada para:\n{impressora}"
        else:
            msg = f"Etiquetas enviadas para:\n{impressora}"

        messagebox.showinfo("Sucesso", msg)

    except Exception as e:
        messagebox.showerror("Erro", str(e))

def limpar_campos():
    entry_lote.delete(0, tk.END)
    entry_codigo.delete(0, tk.END)
    text_desc.delete("1.0", tk.END)
    entry_pacote.delete(0, tk.END)
    entry_volume.delete(0, tk.END)

    entry_lote.insert(0, "25-004855")
    entry_codigo.insert(0, "132483")
    text_desc.insert("1.0", "Tbe IPP 200L AZ 10,3 KG RE BJBR SL Tolerancia MIN10,0 KG - ECZLJ")
    entry_pacote.insert(0, "008")
    entry_volume.insert(0, "10")

root = tk.Tk()
root.title("Gerador de Etiquetas Zebra 100x40")
root.geometry("940x640")
root.minsize(920, 620)

frm = ttk.LabelFrame(root, text="Dados da Etiqueta")
frm.pack(fill="x", padx=12, pady=12)

ttk.Label(frm, text="Número do Lote (OS)").grid(row=0, column=0, sticky="w", padx=6, pady=6)
entry_lote = ttk.Entry(frm, width=25)
entry_lote.grid(row=0, column=1, sticky="w", padx=6, pady=6)

ttk.Label(frm, text="Código do Produto").grid(row=1, column=0, sticky="w", padx=6, pady=6)
entry_codigo = ttk.Entry(frm, width=25)
entry_codigo.grid(row=1, column=1, sticky="w", padx=6, pady=6)

ttk.Label(frm, text="Descrição").grid(row=2, column=0, sticky="nw", padx=6, pady=6)
text_desc = tk.Text(frm, width=60, height=5)
text_desc.grid(row=2, column=1, sticky="w", padx=6, pady=6)

ttk.Label(frm, text="Pacote").grid(row=3, column=0, sticky="w", padx=6, pady=6)
entry_pacote = ttk.Entry(frm, width=10)
entry_pacote.grid(row=3, column=1, sticky="w", padx=6, pady=6)

ttk.Label(frm, text="Volume total").grid(row=4, column=0, sticky="w", padx=6, pady=6)
entry_volume = ttk.Entry(frm, width=10)
entry_volume.grid(row=4, column=1, sticky="w", padx=6, pady=6)

frm_imp = ttk.LabelFrame(root, text="Impressão")
frm_imp.pack(fill="x", padx=12, pady=(0, 12))

ttk.Label(frm_imp, text="Impressora").grid(row=0, column=0, sticky="w", padx=6, pady=8)
entry_impressora = ttk.Entry(frm_imp, width=55)
entry_impressora.grid(row=0, column=1, sticky="w", padx=6, pady=8)

ttk.Button(frm_imp, text="Selecionar...", command=abrir_seletor_impressora).grid(row=0, column=2, padx=6, pady=8)
ttk.Button(frm_imp, text="Usar padrão do Windows", command=usar_padrao_windows).grid(row=0, column=3, padx=6, pady=8)
ttk.Button(frm_imp, text="Salvar como padrão", command=salvar_impressora_padrao).grid(row=0, column=4, padx=6, pady=8)

obs = ttk.LabelFrame(root, text="Observações")
obs.pack(fill="x", padx=12, pady=(0, 12))

ttk.Label(
    obs,
    text=(
        "• Clique em 'Selecionar...' para escolher uma impressora instalada no Windows.\n"
        "• Se preferir, use a impressora padrão do Windows.\n"
        "• O envio é direto em ZPL, sem salvar PDF.\n"
        "• Se nenhuma impressora aparecer, verifique a instalação da impressora e do pywin32."
    ),
    justify="left"
).pack(anchor="w", padx=10, pady=10)

btns = ttk.Frame(root)
btns.pack(fill="x", padx=12, pady=8)

ttk.Button(btns, text="Imprimir", command=lambda: acao_imprimir(False)).pack(side="left", padx=6)
ttk.Button(btns, text="Testar 1 Etiqueta", command=lambda: acao_imprimir(True)).pack(side="left", padx=6)
ttk.Button(btns, text="Limpar", command=limpar_campos).pack(side="left", padx=6)

limpar_campos()
carregar_impressora_salva()

root.mainloop()