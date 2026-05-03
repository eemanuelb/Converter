import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import re

selected_files = []

def extrair_tempo(s):
    """Extrai tempo em segundos de uma string de tempo (HH:MM:SS.ms)"""
    match = re.search(r'(\d+):(\d+):(\d+)', s)
    if match:
        h, m, s = map(int, match.groups())
        return h * 3600 + m * 60 + s
    return 0

def converter_videos(arquivos):
    if not arquivos:
        messagebox.showwarning("Aviso", "Nenhum arquivo .vob selecionado.")
        return

    btn_converter.config(state=tk.DISABLED)
    btn_selecionar.config(state=tk.DISABLED)
    
    total_arquivos = len(arquivos)
    
    for idx, caminho in enumerate(arquivos):
        vob = Path(caminho)
        mp4 = vob.with_suffix(".mp4")
        
        label_status.config(text=f"Convertendo ({idx+1}/{total_arquivos}): {vob.name}")
        root.update()
        
        comando = [
            "ffmpeg",
            "-y",
            "-i", str(vob),
            "-c", "copy",
            str(mp4)
        ]

        proc = subprocess.Popen(
            comando,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        duracao_total = 0
        
        for linha in proc.stderr:
            if "Duration:" in linha:
                duracao_str = linha.split("Duration:")[1].split(",")[0].strip()
                duracao_total = extrair_tempo(duracao_str)
            
            if "time=" in linha and duracao_total > 0:
                tempo_str = linha.split("time=")[1].split(" ")[0].strip()
                tempo_atual = extrair_tempo(tempo_str)
                
                if duracao_total > 0:
                    porcentagem = min(100, int((tempo_atual / duracao_total) * 100))
                else:
                    porcentagem = 0
                
                progress_bar.config(value=porcentagem)
                label_progresso.config(text=f"{porcentagem}%")
                root.update()
        
        proc.wait()
        progress_bar.config(value=100)
        label_progresso.config(text="100%")
        root.update()
    
    messagebox.showinfo("Pronto", "Conversão concluída!")
    btn_converter.config(state=tk.NORMAL)
    btn_selecionar.config(state=tk.NORMAL)
    label_status.config(text="Conversão finalizada")
    progress_bar.config(value=0)
    label_progresso.config(text="0%")


def selecionar_arquivos():
    global selected_files
    arquivos = filedialog.askopenfilenames(
        title="Selecione arquivos .vob",
        filetypes=[("Arquivos VOB", "*.vob")]
    )
    if arquivos:
        selected_files = list(arquivos)
        listbox_arquivos.delete(0, tk.END)
        for arquivo in selected_files:
            listbox_arquivos.insert(tk.END, Path(arquivo).name)


def iniciar_conversao():
    if selected_files:
        converter_videos(selected_files)
    else:
        messagebox.showwarning("Aviso", "Selecione ao menos um arquivo .vob.")


def main():
    global btn_converter, btn_selecionar, listbox_arquivos, progress_bar, label_progresso, label_status, root
    
    root = tk.Tk()
    root.title("Conversor VOB para MP4")
    root.geometry("500x450")

    tk.Label(root, text="Selecione os arquivos .vob para converter:", font=("Arial", 10, "bold")).pack(pady=10)

    frame_botoes = tk.Frame(root)
    frame_botoes.pack(pady=5)

    btn_selecionar = tk.Button(frame_botoes, text="Selecionar Arquivos", command=selecionar_arquivos, width=20)
    btn_selecionar.pack(side=tk.LEFT, padx=5)

    btn_remover = tk.Button(frame_botoes, text="Remover Selecionado", command=lambda: remover_arquivo())
    btn_remover.pack(side=tk.LEFT, padx=5)

    tk.Label(root, text="Arquivos selecionados:", font=("Arial", 9)).pack(anchor="w", padx=10)

    frame_listbox = tk.Frame(root)
    frame_listbox.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)

    scrollbar = tk.Scrollbar(frame_listbox)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    listbox_arquivos = tk.Listbox(frame_listbox, yscrollcommand=scrollbar.set, height=10)
    listbox_arquivos.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=listbox_arquivos.yview)

    label_status = tk.Label(root, text="Pronto para converter", font=("Arial", 9))
    label_status.pack(pady=5)

    progress_bar = ttk.Progressbar(root, orient=tk.HORIZONTAL, length=400, mode='determinate')
    progress_bar.pack(pady=5, padx=10, fill=tk.X)

    label_progresso = tk.Label(root, text="0%", font=("Arial", 9))
    label_progresso.pack(pady=2)

    btn_converter = tk.Button(root, text="Converter", width=20, command=iniciar_conversao, bg="#4CAF50", fg="white")
    btn_converter.pack(pady=15)

    root.mainloop()


def remover_arquivo():
    global selected_files
    selecionado = listbox_arquivos.curselection()
    if selecionado:
        idx = selecionado[0]
        listbox_arquivos.delete(idx)
        selected_files.pop(idx)


if __name__ == "__main__":
    main()
