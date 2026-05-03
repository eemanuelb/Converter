import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import re

selected_files = []
output_format = "mp4"  # padrão
codec_mode = "copy"  # "copy", "padrao", "avancado"
codec_video = "libx264"
codec_audio = "aac"

video_codec_options = {
    "H.264": "libx264",
    "H.265 / HEVC": "libx265",
    "VP8": "libvpx",
    "VP9": "libvpx-vp9",
    "MPEG-2": "mpeg2video",
    "WMV": "wmv2",
}

audio_codec_options = {
    "AAC": "aac",
    "MP3": "libmp3lame",
    "Opus": "libopus",
    "WMA": "wmav2",
    "MP2": "mp2",
    "PCM / WAV": "pcm_s16le",
}

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
    global codec_video, codec_audio, codec_mode_var
    output_ext = output_ext.lower().lstrip('.')
    if not recode:
        return ["-c", "copy"]
    
    if codec_mode_var.get() == "padrao":
        # Codecs fixos por formato
        if output_ext in ["mp4", "mov", "mkv", "flv", "m4v", "asf"]:
            return ["-c:v", "libx264", "-c:a", "aac"]
        if output_ext == "avi":
            return ["-c:v", "libx264", "-c:a", "libmp3lame"]
        if output_ext == "wmv":
            return ["-c:v", "wmv2", "-c:a", "wmav2"]
        if output_ext == "mpeg":
            return ["-c:v", "mpeg2video", "-c:a", "mp2"]
        if output_ext == "webm":
            return ["-c:v", "libvpx-vp9", "-c:a", "libopus"]
        if output_ext == "3gp":
            return ["-c:v", "libx264", "-c:a", "aac"]
        return ["-c:v", "libx264", "-c:a", "aac"]
    
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
        
        modo = "recodificando" if codec_mode_var.get() != "copy" else "copiando"
        label_status.config(text=f"Convertendo ({idx+1}/{total_arquivos}): {vob.name} ({modo})")
        root.update()

        comando = ["ffmpeg", "-y", "-i", str(vob)]
        codec_args = get_ffmpeg_codec_args(output_format, codec_mode_var.get() != "copy")
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
    codec_video = video_codec_options[codec]

def atualizar_codec_audio(codec):
    global codec_audio
    codec_audio = audio_codec_options[codec]

def atualizar_codec_mode(mode):
    global codec_mode_var
    codec_mode_var.set(mode)
    toggle_advanced()

def toggle_advanced():
    if codec_mode_var.get() == "avancado":
        frame_advanced.pack(before=label_arquivos, padx=10, pady=5, fill=tk.X)
    else:
        frame_advanced.pack_forget()

def iniciar_conversao():
    if selected_files:
        converter_videos(selected_files)
    else:
        messagebox.showwarning("Aviso", "Selecione ao menos um arquivo.")


def main():
    global btn_converter, btn_selecionar, listbox_arquivos, progress_bar, label_progresso, label_status, label_arquivos, root
    
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

    # Modo de codecs
    frame_codecs = tk.Frame(root)
    frame_codecs.pack(pady=5)

    global codec_mode_var
    codec_mode_var = tk.StringVar(value=codec_mode)

    tk.Radiobutton(frame_codecs, text="Codec Original", variable=codec_mode_var, value="copy", command=lambda: atualizar_codec_mode("copy")).pack(side=tk.LEFT, padx=10)
    tk.Radiobutton(frame_codecs, text="Codec Padrão", variable=codec_mode_var, value="padrao", command=lambda: atualizar_codec_mode("padrao")).pack(side=tk.LEFT, padx=10)
    tk.Radiobutton(frame_codecs, text="Codec Avançado", variable=codec_mode_var, value="avancado", command=lambda: atualizar_codec_mode("avancado")).pack(side=tk.LEFT, padx=10)

    # Menu Avançado (inicialmente oculto)
    global frame_advanced
    frame_advanced = tk.LabelFrame(root, text="Codec Avançado", font=("Arial", 9), padx=10, pady=5)
    # Não pack inicialmente

    tk.Label(frame_advanced, text="Vídeo:", font=("Arial", 8)).pack(anchor="w")
    codecs_video = list(video_codec_options.keys())
    combo_video = ttk.Combobox(frame_advanced, values=codecs_video, state="readonly", width=20)
    combo_video.set("H.264")
    combo_video.pack(padx=5, pady=2, fill=tk.X)
    combo_video.bind("<<ComboboxSelected>>", lambda e: atualizar_codec_video(combo_video.get()))

    tk.Label(frame_advanced, text="Áudio:", font=("Arial", 8)).pack(anchor="w")
    codecs_audio = list(audio_codec_options.keys())
    combo_audio = ttk.Combobox(frame_advanced, values=codecs_audio, state="readonly", width=20)
    combo_audio.set("AAC")
    combo_audio.pack(padx=5, pady=2, fill=tk.X)
    combo_audio.bind("<<ComboboxSelected>>", lambda e: atualizar_codec_audio(combo_audio.get()))

    label_arquivos = tk.Label(root, text="Arquivos selecionados:", font=("Arial", 9))
    label_arquivos.pack(anchor="w", padx=10)

    # Garantir estado inicial
    toggle_advanced()

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
