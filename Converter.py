import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import re
import json
import os
from datetime import datetime
import threading

selected_files = []
output_format = "mp4"  # padrão
codec_mode = "copy"  # "copy", "padrao", "avancado"
codec_video = "libx264"
codec_audio = "aac"
dark_mode = False
keep_on_top = False
settings_path = Path(os.getenv("APPDATA", Path.home())) / "Conversor" / "settings.json"

video_codec_options = {
    "AV1": "libaom-av1",
    "DNxHD": "dnxhd",
    "H.261": "h261",
    "H.263": "h263",
    "H.264": "libx264",
    "H.265": "libx265",
    "MJPEG": "mjpeg",
    "MPEG-2": "mpeg2video",
    "MPEG-4": "mpeg4",
    "ProRes": "prores_ks",
    "Theora": "libtheora",
    "VP7": "vp7",
    "VP8": "libvpx",
    "VP9": "libvpx-vp9",
    "WMV": "wmv2",
}

audio_codec_options = {
    "AAC": "aac",
    "AC3": "ac3",
    "ALAC": "alac",
    "AMR-NB": "libopencore_amrnb",
    "AMR-WB": "libvo_amrwbenc",
    "DTS": "dts",
    "E-AC3": "eac3",
    "FLAC": "flac",
    "MP2": "mp2",
    "MP3": "libmp3lame",
    "Opus": "libopus",
    "PCM": "pcm_s16le",
    "Vorbis": "libvorbis",
    "WavPack": "wavpack",
    "WMA": "wmav2",
}

formatos_suportados = [
    '.3gp', '.asf', '.avi', '.f4v', '.flv', '.gif', '.m2ts',
    '.m4v', '.mkv', '.mov', '.mp4', '.mpeg', '.mxf', '.ogv',
    '.ts', '.vob', '.webm', '.wmv'
]

formatos_saida = [
    '3gp', 'asf', 'avi', 'f4v', 'flv', 'gif', 'm2ts',
    'm4v', 'mkv', 'mov', 'mp4', 'mpeg', 'mxf', 'ogv',
    'ts', 'vob', 'webm', 'wmv'
]

def encontrar_rotulo_codec(opcoes, encoder, padrao):
    for rotulo, valor in opcoes.items():
        if valor == encoder:
            return rotulo
    return padrao


def carregar_configuracoes():
    global output_format, codec_mode, codec_video, codec_audio, dark_mode, keep_on_top
    if not settings_path.exists():
        return

    try:
        dados = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return

    formato = dados.get("output_format")
    if formato in formatos_saida:
        output_format = formato

    modo = dados.get("codec_mode")
    if modo in {"copy", "padrao", "avancado"}:
        codec_mode = modo

    video = dados.get("codec_video")
    if video in video_codec_options.values():
        codec_video = video

    audio = dados.get("codec_audio")
    if audio in audio_codec_options.values():
        codec_audio = audio

    dark_mode = bool(dados.get("dark_mode", dark_mode))
    keep_on_top = bool(dados.get("keep_on_top", keep_on_top))


def salvar_configuracoes():
    dados = {
        "output_format": output_format,
        "codec_mode": codec_mode,
        "codec_video": codec_video,
        "codec_audio": codec_audio,
        "dark_mode": dark_mode,
        "keep_on_top": keep_on_top,
    }
    try:
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(json.dumps(dados, indent=2), encoding="utf-8")
    except OSError:
        pass


carregar_configuracoes()

def executar_na_ui(func, *args, **kwargs):
    try:
        if threading.current_thread() is threading.main_thread():
            func(*args, **kwargs)
        else:
            root.after(0, lambda: func(*args, **kwargs))
    except NameError:
        func(*args, **kwargs)


def registrar_log(mensagem):
    horario = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linha = f"[{horario}] {mensagem}\n"

    def escrever():
        log_text.config(state=tk.NORMAL)
        log_text.insert(tk.END, linha)
        log_text.see(tk.END)
        log_text.config(state=tk.DISABLED)

    try:
        executar_na_ui(escrever)
    except NameError:
        print(linha, end="")


def atualizar_status(texto):
    executar_na_ui(label_status.config, text=texto)


def atualizar_progresso(valor):
    executar_na_ui(progress_bar.config, value=valor)
    executar_na_ui(label_progresso.config, text=f"{valor}%")


def configurar_botoes_conversao(ativo):
    estado = tk.NORMAL if ativo else tk.DISABLED
    executar_na_ui(btn_converter.config, state=estado)
    executar_na_ui(btn_selecionar.config, state=estado)


def remover_arquivo_convertido(caminho):
    try:
        idx_remover = selected_files.index(caminho)
        selected_files.pop(idx_remover)
        listbox_arquivos.delete(idx_remover)
    except (ValueError, tk.TclError):
        pass


def extrair_tempo(s):
    """Extrai tempo em segundos de uma string de tempo (HH:MM:SS.ms)"""
    match = re.search(r'(\d+):(\d+):(\d+)', s)
    if match:
        h, m, s = map(int, match.groups())
        return h * 3600 + m * 60 + s
    return 0


def get_ffmpeg_codec_args(output_ext, recode, mode=None, video_encoder=None, audio_encoder=None):
    global codec_video, codec_audio
    output_ext = output_ext.lower().lstrip('.')
    mode = mode or codec_mode
    video_encoder = video_encoder or codec_video
    audio_encoder = audio_encoder or codec_audio

    if not recode:
        return ["-c", "copy"]
    
    if mode == "padrao":
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
    
    return ["-c:v", video_encoder, "-c:a", audio_encoder]


def converter_videos(arquivos):
    global output_format
    if not arquivos:
        executar_na_ui(messagebox.showwarning, "Aviso", "Nenhum arquivo selecionado.")
        registrar_log("Aviso: tentativa de conversao sem arquivos selecionados.")
        return

    configurar_botoes_conversao(False)
    
    total_arquivos = len(arquivos)
    formato_saida = output_format
    modo_codec = codec_mode
    video_encoder = codec_video
    audio_encoder = codec_audio
    registrar_log(f"Iniciando conversao de {total_arquivos} arquivo(s).")
    
    for idx, caminho in enumerate(arquivos):
        vob = Path(caminho)
        saida = vob.with_suffix(f".{formato_saida}")
        
        modo = "recodificando" if modo_codec != "copy" else "copiando"
        atualizar_status(f"Convertendo ({idx+1}/{total_arquivos}): {vob.name} ({modo})")

        comando = ["ffmpeg", "-y", "-i", str(vob)]
        codec_args = get_ffmpeg_codec_args(
            formato_saida,
            modo_codec != "copy",
            modo_codec,
            video_encoder,
            audio_encoder,
        )
        comando.extend(codec_args)
        comando.append(str(saida))
        registrar_log(f"Convertendo arquivo: {vob.name}")
        registrar_log(f"Comando: {subprocess.list2cmdline(comando)}")

        try:
            proc = subprocess.Popen(
                comando,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
        except FileNotFoundError:
            registrar_log("Erro: ffmpeg nao foi encontrado no PATH do sistema.")
            atualizar_status("Erro: ffmpeg não encontrado")
            executar_na_ui(messagebox.showerror, "Erro", "FFmpeg não foi encontrado. Verifique se ele está instalado e no PATH.")
            configurar_botoes_conversao(True)
            return
        
        duracao_total = 0
        linhas_erro = []
        
        for linha in proc.stderr:
            linhas_erro.append(linha.rstrip())
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
                
                atualizar_progresso(porcentagem)
        
        proc.wait()
        if proc.returncode != 0:
            atualizar_status(f"Erro ao converter: {vob.name}")
            registrar_log(f"Erro ao converter {vob.name}. Codigo de saida: {proc.returncode}")
            if linhas_erro:
                registrar_log("Saida de erro do ffmpeg:")
                for linha in linhas_erro[-25:]:
                    registrar_log(f"  {linha}")
            executar_na_ui(messagebox.showerror, "Erro", f"Falha ao converter {vob.name}. Verifique o formato e tente novamente.")
            configurar_botoes_conversao(True)
            return

        atualizar_progresso(100)
        registrar_log(f"Conversao concluida: {saida.name}")
        
        executar_na_ui(remover_arquivo_convertido, caminho)
    
    executar_na_ui(messagebox.showinfo, "Pronto", "Conversão concluída!")
    registrar_log("Conversao finalizada com sucesso.")
    configurar_botoes_conversao(True)
    atualizar_status("Conversão finalizada")
    atualizar_progresso(0)


def selecionar_arquivos():
    global selected_files
    todos_formatos = " ".join(f"*{formato}" for formato in formatos_suportados)
    filtros_formatos = [
        (f"Arquivos {formato.lstrip('.').upper()}", f"*{formato}")
        for formato in formatos_suportados
    ]
    arquivos = filedialog.askopenfilenames(
        title="Selecione arquivos de vídeo",
        filetypes=[
            ("Todos os arquivos de vídeo", todos_formatos),
            *filtros_formatos,
            ("Todos os arquivos", "*.*")
        ]
    )
    if arquivos:
        arquivos_validos = []
        for arq in arquivos:
            if Path(arq).suffix.lower() in formatos_suportados:
                arquivos_validos.append(arq)
            else:
                registrar_log(f"Arquivo ignorado por formato nao suportado: {Path(arq).name}")
                messagebox.showwarning("Formato não suportado", f"O arquivo {Path(arq).name} não é suportado.")
        
        selected_files = arquivos_validos
        listbox_arquivos.delete(0, tk.END)
        for arquivo in selected_files:
            listbox_arquivos.insert(tk.END, Path(arquivo).name)


def atualizar_formato(formato):
    global output_format
    output_format = formato
    salvar_configuracoes()

def atualizar_codec_video(codec):
    global codec_video
    codec_video = video_codec_options[codec]
    salvar_configuracoes()

def atualizar_codec_audio(codec):
    global codec_audio
    codec_audio = audio_codec_options[codec]
    salvar_configuracoes()

def atualizar_codec_mode(mode):
    global codec_mode, codec_mode_var
    codec_mode = mode
    codec_mode_var.set(mode)
    toggle_advanced()
    salvar_configuracoes()

def toggle_advanced():
    if codec_mode_var.get() == "avancado":
        frame_advanced.pack(before=label_arquivos, padx=18, pady=(0, 10), fill=tk.X)
    else:
        frame_advanced.pack_forget()

def iniciar_conversao():
    if selected_files:
        arquivos = list(selected_files)
        configurar_botoes_conversao(False)
        threading.Thread(target=converter_videos, args=(arquivos,), daemon=True).start()
    else:
        messagebox.showwarning("Aviso", "Selecione ao menos um arquivo.")


def aplicar_tema(janela, modo_escuro):
    cores = {
        "bg": "#15171a" if modo_escuro else "#f4f6f8",
        "fg": "#f4f7fb" if modo_escuro else "#1f2933",
        "muted": "#aeb7c2" if modo_escuro else "#5f6b7a",
        "field": "#20242a" if modo_escuro else "#ffffff",
        "button": "#2a3038" if modo_escuro else "#e8edf3",
        "button_hover": "#363e49" if modo_escuro else "#dce4ee",
        "border": "#333b46" if modo_escuro else "#d7dee8",
        "select": "#345174" if modo_escuro else "#cfe3ff",
        "accent": "#3b82f6",
        "accent_hover": "#2563eb",
        "success": "#22a55f",
        "success_hover": "#16834b",
    }

    style = ttk.Style(janela)
    style.theme_use("clam")
    style.configure("TFrame", background=cores["bg"])
    style.configure("Card.TFrame", background=cores["field"], relief=tk.FLAT)
    style.configure("TLabel", background=cores["bg"], foreground=cores["fg"])
    style.configure("Title.TLabel", background=cores["bg"], foreground=cores["fg"], font=("Segoe UI", 14, "bold"))
    style.configure("Muted.TLabel", background=cores["bg"], foreground=cores["muted"], font=("Segoe UI", 9))
    style.configure("Card.TLabel", background=cores["field"], foreground=cores["fg"])
    style.configure("TNotebook", background=cores["bg"], borderwidth=0, tabmargins=(12, 8, 12, 0))
    style.configure("TNotebook.Tab", background=cores["button"], foreground=cores["fg"], padding=(16, 8), font=("Segoe UI", 9))
    style.map(
        "TNotebook.Tab",
        background=[("selected", cores["field"]), ("active", cores["button_hover"])],
        foreground=[("selected", cores["fg"])],
    )
    style.configure("TButton", background=cores["button"], foreground=cores["fg"], borderwidth=0, padding=(12, 7), font=("Segoe UI", 9))
    style.map("TButton", background=[("active", cores["button_hover"]), ("disabled", cores["border"])])
    style.configure("Accent.TButton", background=cores["accent"], foreground="#ffffff")
    style.map("Accent.TButton", background=[("active", cores["accent_hover"]), ("disabled", cores["border"])])
    style.configure("Success.TButton", background=cores["success"], foreground="#ffffff", padding=(18, 9), font=("Segoe UI", 10, "bold"))
    style.map("Success.TButton", background=[("active", cores["success_hover"]), ("disabled", cores["border"])])
    style.configure("TCheckbutton", background=cores["bg"], foreground=cores["fg"], font=("Segoe UI", 9))
    style.configure("TRadiobutton", background=cores["bg"], foreground=cores["fg"], font=("Segoe UI", 9))
    style.map("TCheckbutton", background=[("active", cores["bg"])], foreground=[("active", cores["fg"])])
    style.map("TRadiobutton", background=[("active", cores["bg"])], foreground=[("active", cores["fg"])])
    style.configure("TLabelframe", background=cores["field"], bordercolor=cores["border"], relief=tk.SOLID)
    style.configure("TLabelframe.Label", background=cores["field"], foreground=cores["fg"], font=("Segoe UI", 9, "bold"))
    style.configure("TCombobox", fieldbackground=cores["field"], background=cores["button"], foreground=cores["fg"], arrowcolor=cores["fg"], padding=5)
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", cores["field"])],
        foreground=[("readonly", cores["fg"])],
        selectbackground=[("readonly", cores["select"])],
        selectforeground=[("readonly", cores["fg"])],
    )
    style.configure("Horizontal.TProgressbar", background="#4CAF50", troughcolor=cores["field"])
    janela.option_add("*TCombobox*Listbox.background", cores["field"])
    janela.option_add("*TCombobox*Listbox.foreground", cores["fg"])
    janela.option_add("*TCombobox*Listbox.selectBackground", cores["select"])
    janela.option_add("*TCombobox*Listbox.selectForeground", cores["fg"])
    janela.option_add("*Font", "Segoe UI 9")

    def aplicar_widget(widget):
        classe = widget.winfo_class()
        if classe == "Frame":
            widget.configure(bg=cores["bg"])
        elif classe == "Label":
            widget.configure(bg=cores["bg"], fg=cores["fg"])
        elif classe == "Labelframe":
            widget.configure(bg=cores["field"], fg=cores["fg"], highlightbackground=cores["border"], highlightcolor=cores["border"])
        elif classe in {"Radiobutton", "Checkbutton"}:
            widget.configure(
                bg=cores["bg"],
                fg=cores["fg"],
                activebackground=cores["bg"],
                activeforeground=cores["fg"],
                selectcolor=cores["field"],
            )
        elif classe == "Button" and widget.cget("text") != "Converter":
            widget.configure(bg=cores["button"], fg=cores["fg"], activebackground=cores["field"], activeforeground=cores["fg"])
        elif classe in {"Listbox", "Text"}:
            widget.configure(
                bg=cores["field"],
                fg=cores["fg"],
                selectbackground=cores["select"],
                selectforeground=cores["fg"],
                highlightthickness=1,
                highlightbackground=cores["border"],
                relief=tk.FLAT,
                borderwidth=0,
            )

        for filho in widget.winfo_children():
            aplicar_widget(filho)

    janela.configure(bg=cores["bg"])
    aplicar_widget(janela)


def configurar_combobox(combo):
    def suspender_topmost(_event=None):
        janela = combo.winfo_toplevel()
        if keep_on_top:
            janela.attributes("-topmost", False)

    def restaurar_topmost(_event=None):
        janela = combo.winfo_toplevel()
        if keep_on_top:
            combo.after_idle(lambda: janela.attributes("-topmost", True))

    combo.bind("<ButtonPress-1>", suspender_topmost, add="+")
    combo.bind("<<ComboboxSelected>>", restaurar_topmost, add="+")
    combo.bind("<FocusOut>", restaurar_topmost, add="+")
    combo.bind("<Escape>", restaurar_topmost, add="+")


def main():
    global btn_converter, btn_selecionar, listbox_arquivos, progress_bar, label_progresso, label_status, label_arquivos, root, log_text
    
    root = tk.Tk()
    root.title("Conversor de Vídeo")
    root.geometry("720x680")
    root.minsize(640, 620)

    notebook = ttk.Notebook(root)
    notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

    aba_video = tk.Frame(notebook)
    aba_configuracoes = tk.Frame(notebook)
    aba_logs = tk.Frame(notebook)
    notebook.add(aba_video, text="Vídeo")
    notebook.add(aba_configuracoes, text="Configurações")
    notebook.add(aba_logs, text="Logs")

    ttk.Label(aba_video, text="Conversão de vídeo", style="Title.TLabel").pack(anchor="w", padx=18, pady=(16, 2))
    ttk.Label(aba_video, text="Selecione arquivos, escolha o formato e acompanhe o progresso.", style="Muted.TLabel").pack(anchor="w", padx=18, pady=(0, 12))

    frame_botoes = tk.Frame(aba_video)
    frame_botoes.pack(fill=tk.X, padx=18, pady=(0, 10))

    btn_selecionar = ttk.Button(frame_botoes, text="Selecionar Arquivos", command=selecionar_arquivos, width=20, style="Accent.TButton")
    btn_selecionar.pack(side=tk.LEFT, padx=5)

    btn_remover = ttk.Button(frame_botoes, text="Remover Selecionado", command=lambda: remover_arquivo())
    btn_remover.pack(side=tk.LEFT, padx=5)

    ttk.Label(aba_video, text="Formato de saída").pack(anchor="w", padx=24, pady=(2, 4))

    combo_formato = ttk.Combobox(aba_video, values=formatos_saida, state="readonly", width=10)
    combo_formato.set(output_format)
    configurar_combobox(combo_formato)
    combo_formato.pack(anchor="w", padx=24, pady=(0, 10))
    combo_formato.bind("<<ComboboxSelected>>", lambda e: atualizar_formato(combo_formato.get()), add="+")

    # Modo de codecs
    frame_codecs = tk.Frame(aba_video)
    frame_codecs.pack(fill=tk.X, padx=18, pady=(0, 10))

    global codec_mode_var
    codec_mode_var = tk.StringVar(value=codec_mode)

    ttk.Radiobutton(frame_codecs, text="Codec Original", variable=codec_mode_var, value="copy", command=lambda: atualizar_codec_mode("copy")).pack(side=tk.LEFT, padx=8)
    ttk.Radiobutton(frame_codecs, text="Codec Padrão", variable=codec_mode_var, value="padrao", command=lambda: atualizar_codec_mode("padrao")).pack(side=tk.LEFT, padx=8)
    ttk.Radiobutton(frame_codecs, text="Codec Avançado", variable=codec_mode_var, value="avancado", command=lambda: atualizar_codec_mode("avancado")).pack(side=tk.LEFT, padx=8)

    # Menu Avançado (inicialmente oculto)
    global frame_advanced
    frame_advanced = ttk.LabelFrame(aba_video, text="Codec Avançado", padding=(12, 8))
    # Não pack inicialmente

    ttk.Label(frame_advanced, text="Vídeo:", style="Card.TLabel").pack(anchor="w")
    codecs_video = list(video_codec_options.keys())
    combo_video = ttk.Combobox(frame_advanced, values=codecs_video, state="readonly", width=20)
    combo_video.set(encontrar_rotulo_codec(video_codec_options, codec_video, "H.264"))
    configurar_combobox(combo_video)
    combo_video.pack(pady=(2, 8), fill=tk.X)
    combo_video.bind("<<ComboboxSelected>>", lambda e: atualizar_codec_video(combo_video.get()), add="+")

    ttk.Label(frame_advanced, text="Áudio:", style="Card.TLabel").pack(anchor="w")
    codecs_audio = list(audio_codec_options.keys())
    combo_audio = ttk.Combobox(frame_advanced, values=codecs_audio, state="readonly", width=20)
    combo_audio.set(encontrar_rotulo_codec(audio_codec_options, codec_audio, "AAC"))
    configurar_combobox(combo_audio)
    combo_audio.pack(pady=(2, 0), fill=tk.X)
    combo_audio.bind("<<ComboboxSelected>>", lambda e: atualizar_codec_audio(combo_audio.get()), add="+")

    label_arquivos = ttk.Label(aba_video, text="Arquivos selecionados")
    label_arquivos.pack(anchor="w", padx=24, pady=(4, 4))

    # Garantir estado inicial
    toggle_advanced()

    frame_listbox = tk.Frame(aba_video)
    frame_listbox.pack(padx=18, pady=(0, 10), fill=tk.BOTH, expand=True)

    scrollbar = tk.Scrollbar(frame_listbox)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    listbox_arquivos = tk.Listbox(frame_listbox, yscrollcommand=scrollbar.set, height=10)
    listbox_arquivos.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=listbox_arquivos.yview)

    label_status = ttk.Label(aba_video, text="Pronto para converter", style="Muted.TLabel")
    label_status.pack(anchor="w", padx=24, pady=(0, 4))

    progress_bar = ttk.Progressbar(aba_video, orient=tk.HORIZONTAL, length=400, mode='determinate')
    progress_bar.pack(pady=(0, 2), padx=18, fill=tk.X)

    label_progresso = ttk.Label(aba_video, text="0%", style="Muted.TLabel")
    label_progresso.pack(anchor="e", padx=24, pady=(0, 8))

    btn_converter = ttk.Button(aba_video, text="Converter", width=20, command=iniciar_conversao, style="Success.TButton")
    btn_converter.pack(pady=(0, 18))

    ttk.Label(aba_configuracoes, text="Configurações", style="Title.TLabel").pack(anchor="w", padx=18, pady=(16, 2))
    ttk.Label(aba_configuracoes, text="Preferências salvas automaticamente.", style="Muted.TLabel").pack(anchor="w", padx=18, pady=(0, 12))

    frame_config_geral = ttk.LabelFrame(aba_configuracoes, text="Geral", padding=(14, 12))
    frame_config_geral.pack(padx=18, pady=(0, 12), fill=tk.X)

    manter_no_topo_var = tk.BooleanVar(value=keep_on_top)
    modo_escuro_var = tk.BooleanVar(value=dark_mode)

    def atualizar_manter_no_topo():
        global keep_on_top
        keep_on_top = manter_no_topo_var.get()
        root.attributes("-topmost", manter_no_topo_var.get())
        salvar_configuracoes()

    def atualizar_modo_escuro():
        global dark_mode
        dark_mode = modo_escuro_var.get()
        aplicar_tema(root, dark_mode)
        salvar_configuracoes()

    ttk.Checkbutton(
        frame_config_geral,
        text="Manter janela sempre no topo",
        variable=manter_no_topo_var,
        command=atualizar_manter_no_topo
    ).pack(anchor="w")

    ttk.Checkbutton(
        frame_config_geral,
        text="Modo escuro",
        variable=modo_escuro_var,
        command=atualizar_modo_escuro
    ).pack(anchor="w", pady=(6, 0))

    ttk.Label(aba_logs, text="Logs", style="Title.TLabel").pack(anchor="w", padx=18, pady=(16, 2))
    ttk.Label(aba_logs, text="Erros e eventos importantes aparecem aqui.", style="Muted.TLabel").pack(anchor="w", padx=18, pady=(0, 12))

    frame_logs = tk.Frame(aba_logs)
    frame_logs.pack(fill=tk.BOTH, expand=True, padx=18, pady=(0, 10))

    scrollbar_logs = tk.Scrollbar(frame_logs)
    scrollbar_logs.pack(side=tk.RIGHT, fill=tk.Y)

    log_text = tk.Text(frame_logs, wrap=tk.WORD, yscrollcommand=scrollbar_logs.set, state=tk.DISABLED, height=18)
    log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar_logs.config(command=log_text.yview)

    def limpar_logs():
        log_text.config(state=tk.NORMAL)
        log_text.delete("1.0", tk.END)
        log_text.config(state=tk.DISABLED)

    ttk.Button(aba_logs, text="Limpar Logs", command=limpar_logs, width=16).pack(anchor="e", padx=18, pady=(0, 14))

    root.attributes("-topmost", keep_on_top)
    aplicar_tema(root, dark_mode)
    registrar_log("Aplicativo iniciado.")

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
