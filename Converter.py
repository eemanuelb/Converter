import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import re

selected_files = []
output_format = "mp4"  # padrão
recode_var = None
codec_video = "libx264"
codec_audio = "aac"

formatos_suportados = [
    '.vob', '.mov', '.avi', '.mkv', '.wmv', '.mpeg', '.webm',
    '.mp4', '.flv', '.m4v', '.3gp', '.asf'
]

formatos_saida = [
    'mp4', 'avi', 'mov', 'mkv', 'wmv', 'mpeg', 'webm',
    'flv', 'm4v', '3gp', 'asf', 'vob'
]

def extrair_tempo(s):
    """Extrai tempo em segundos de uma string de tempo (HH:MM:SS.ms)"""
    match = re.search(r'(\d+):(\d+):(\d+)', s)
    if match:
        h, m, s = map(int, match.groups())
        return h * 3600 + m * 60 + s
    return 0


def get_ffmpeg_codec_args(output_ext, recode):
    global codec_video, codec_audio
    output_ext = output_ext.lower().lstrip('.')
    if not recode:
        return ["-c", "copy"]
    
    return ["-c:v", codec_video, "-c:a", codec_audio]


def converter_videos(arquivos):
    global output_format
    if not arquivos:
        messagebox.showwarning("Aviso", "Nenhum arquivo selecionado.")
        return

    btn_converter.config(state=tk.DISABLED)
    btn_selecionar.config(state=tk.DISABLED)
    
    total_arquivos = len(arquivos)
    
    for idx, caminho in enumerate(arquivos):
        vob = Path(caminho)
        saida = vob.with_suffix(f".{output_format}")
        
        modo = "recodificando" if recode_var.get() else "copiando"
        label_status.config(text=f"Convertendo ({idx+1}/{total_arquivos}): {vob.name} ({modo})")
        root.update()

        comando = ["ffmpeg", "-y", "-i", str(vob)]
        codec_args = get_ffmpeg_codec_args(output_format, recode_var.get())
        comando.extend(codec_args)
        comando.append(str(saida))

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
        if proc.returncode != 0:
            label_status.config(text=f"Erro ao converter: {vob.name}")
            messagebox.showerror("Erro", f"Falha ao converter {vob.name}. Verifique o formato e tente novamente.")
            btn_converter.config(state=tk.NORMAL)
            btn_selecionar.config(state=tk.NORMAL)
            return

        progress_bar.config(value=100)
        label_progresso.config(text="100%")
        root.update()
        
        # Remover arquivo da lista após conversão bem-sucedida
        try:
            idx_remover = selected_files.index(caminho)
            selected_files.pop(idx_remover)
            listbox_arquivos.delete(idx_remover)
        except (ValueError, tk.TclError):
            pass
    
    messagebox.showinfo("Pronto", "Conversão concluída!")
    btn_converter.config(state=tk.NORMAL)
    btn_selecionar.config(state=tk.NORMAL)
    label_status.config(text="Conversão finalizada")
    progress_bar.config(value=0)
    label_progresso.config(text="0%")


def selecionar_arquivos():
    global selected_files
    arquivos = filedialog.askopenfilenames(
        title="Selecione arquivos de vídeo",
        filetypes=[
            ("Todos os arquivos de vídeo", "*.vob *.mov *.avi *.mkv *.wmv *.mpeg *.webm *.mp4 *.flv *.m4v *.3gp *.asf"),
            ("Arquivos VOB", "*.vob"),
            ("Arquivos MOV", "*.mov"),
            ("Arquivos AVI", "*.avi"),
            ("Arquivos MKV", "*.mkv"),
            ("Arquivos WMV", "*.wmv"),
            ("Arquivos MPEG", "*.mpeg"),
            ("Arquivos WebM", "*.webm"),
            ("Arquivos MP4", "*.mp4"),
            ("Arquivos FLV", "*.flv"),
            ("Arquivos M4V", "*.m4v"),
            ("Arquivos 3GP", "*.3gp"),
            ("Arquivos ASF", "*.asf"),
            ("Todos os arquivos", "*.*")
        ]
    )
    if arquivos:
        arquivos_validos = []
        for arq in arquivos:
            if Path(arq).suffix.lower() in formatos_suportados:
                arquivos_validos.append(arq)
            else:
                messagebox.showwarning("Formato não suportado", f"O arquivo {Path(arq).name} não é suportado.")
        
        selected_files = arquivos_validos
        listbox_arquivos.delete(0, tk.END)
        for arquivo in selected_files:
            listbox_arquivos.insert(tk.END, Path(arquivo).name)


def atualizar_formato(formato):
    global output_format
    output_format = formato

def atualizar_codec_video(codec):
    global codec_video
    codec_video = codec

def atualizar_codec_audio(codec):
    global codec_audio
    codec_audio = codec

def iniciar_conversao():
    if selected_files:
        converter_videos(selected_files)
    else:
        messagebox.showwarning("Aviso", "Selecione ao menos um arquivo.")


def main():
    global btn_converter, btn_selecionar, listbox_arquivos, progress_bar, label_progresso, label_status, root
    
    root = tk.Tk()
    root.title("Conversor de Vídeo")
    root.geometry("550x600")

    tk.Label(root, text="Selecione os arquivos de vídeo para converter:", font=("Arial", 10, "bold")).pack(pady=10)

    frame_botoes = tk.Frame(root)
    frame_botoes.pack(pady=5)

    btn_selecionar = tk.Button(frame_botoes, text="Selecionar Arquivos", command=selecionar_arquivos, width=20)
    btn_selecionar.pack(side=tk.LEFT, padx=5)

    btn_remover = tk.Button(frame_botoes, text="Remover Selecionado", command=lambda: remover_arquivo())
    btn_remover.pack(side=tk.LEFT, padx=5)

    tk.Label(root, text="Formato de saída:", font=("Arial", 9)).pack(pady=5)

    combo_formato = ttk.Combobox(root, values=formatos_saida, state="readonly", width=10)
    combo_formato.set("mp4")
    combo_formato.pack(pady=5)
    combo_formato.bind("<<ComboboxSelected>>", lambda e: atualizar_formato(combo_formato.get()))

    global recode_var
    recode_var = tk.BooleanVar(value=False)
    recode_check = tk.Checkbutton(root, text="Modo recodificação", variable=recode_var)
    recode_check.pack(pady=3)

    # Menu Avançado
    frame_advanced = tk.LabelFrame(root, text="Avançado (recodificação)", font=("Arial", 9), padx=10, pady=5)
    frame_advanced.pack(padx=10, pady=5, fill=tk.X)

    tk.Label(frame_advanced, text="Vídeo:", font=("Arial", 8)).pack(anchor="w")
    codecs_video = ["libx264", "libx265", "libvpx", "libvpx-vp9", "mpeg2video", "wmv2"]
    combo_video = ttk.Combobox(frame_advanced, values=codecs_video, state="readonly", width=20)
    combo_video.set("libx264")
    combo_video.pack(padx=5, pady=2, fill=tk.X)
    combo_video.bind("<<ComboboxSelected>>", lambda e: atualizar_codec_video(combo_video.get()))

    tk.Label(frame_advanced, text="Áudio:", font=("Arial", 8)).pack(anchor="w")
    codecs_audio = ["aac", "libmp3lame", "libopus", "wmav2", "mp2", "pcm_s16le"]
    combo_audio = ttk.Combobox(frame_advanced, values=codecs_audio, state="readonly", width=20)
    combo_audio.set("aac")
    combo_audio.pack(padx=5, pady=2, fill=tk.X)
    combo_audio.bind("<<ComboboxSelected>>", lambda e: atualizar_codec_audio(combo_audio.get()))

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
