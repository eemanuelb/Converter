import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import re
import json
import os
import ctypes
from ctypes import wintypes
from datetime import datetime
import threading

selected_files = []
file_settings = {}
codecs_visiveis = True
output_format = "mp4"  # padrão
codec_video = "libx264"
codec_audio = "aac"
dark_mode = False
keep_on_top = False
current_process = None
conversion_stop_requested = False
conversion_paused = False
conversion_lock = threading.Lock()
selection_menus = []
settings_path = Path(os.getenv("APPDATA", Path.home())) / "Conversor" / "settings.json"

video_codec_options = {
    "AV1": "libaom-av1",
    "DNxHD": "dnxhd",
    "GIF": "gif",
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

codec_presets_por_formato = {
    "3gp": ("H.264", "AAC"),
    "asf": ("H.264", "AAC"),
    "avi": ("H.264", "MP3"),
    "f4v": ("H.264", "AAC"),
    "flv": ("H.264", "AAC"),
    "gif": ("GIF", None),
    "m2ts": ("H.264", "AAC"),
    "m4v": ("H.264", "AAC"),
    "mkv": ("H.264", "AAC"),
    "mov": ("H.264", "AAC"),
    "mp4": ("H.264", "AAC"),
    "mpeg": ("MPEG-2", "MP2"),
    "mxf": ("MPEG-2", "PCM"),
    "ogv": ("Theora", "Vorbis"),
    "ts": ("H.264", "AAC"),
    "vob": ("MPEG-2", "AC3"),
    "webm": ("VP9", "Opus"),
    "wmv": ("WMV", "WMA"),
}


def encontrar_rotulo_codec(opcoes, encoder, padrao):
    for rotulo, valor in opcoes.items():
        if valor == encoder:
            return rotulo
    return padrao


def carregar_configuracoes():
    global output_format, codec_video, codec_audio, dark_mode, keep_on_top
    if not settings_path.exists():
        return

    try:
        dados = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return

    formato = dados.get("output_format")
    if formato in formatos_saida:
        output_format = formato

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
    executar_na_ui(btn_pausar.config, state=tk.DISABLED if ativo else tk.NORMAL, text="Pausar")
    executar_na_ui(btn_parar.config, state=tk.DISABLED if ativo else tk.NORMAL)


class THREADENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ThreadID", wintypes.DWORD),
        ("th32OwnerProcessID", wintypes.DWORD),
        ("tpBasePri", wintypes.LONG),
        ("tpDeltaPri", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
    ]


def iterar_threads_processo(pid):
    if os.name != "nt":
        return

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel32.Thread32First.argtypes = [wintypes.HANDLE, ctypes.POINTER(THREADENTRY32)]
    kernel32.Thread32First.restype = wintypes.BOOL
    kernel32.Thread32Next.argtypes = [wintypes.HANDLE, ctypes.POINTER(THREADENTRY32)]
    kernel32.Thread32Next.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    snapshot = kernel32.CreateToolhelp32Snapshot(0x00000004, 0)
    if snapshot == wintypes.HANDLE(-1).value:
        return

    entrada = THREADENTRY32()
    entrada.dwSize = ctypes.sizeof(THREADENTRY32)
    try:
        tem_thread = kernel32.Thread32First(snapshot, ctypes.byref(entrada))
        while tem_thread:
            if entrada.th32OwnerProcessID == pid:
                yield entrada.th32ThreadID
            tem_thread = kernel32.Thread32Next(snapshot, ctypes.byref(entrada))
    finally:
        kernel32.CloseHandle(snapshot)


def alterar_pausa_processo(proc, pausar):
    if proc is None or proc.poll() is not None or os.name != "nt":
        return False

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenThread.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenThread.restype = wintypes.HANDLE
    kernel32.SuspendThread.argtypes = [wintypes.HANDLE]
    kernel32.SuspendThread.restype = wintypes.DWORD
    kernel32.ResumeThread.argtypes = [wintypes.HANDLE]
    kernel32.ResumeThread.restype = wintypes.DWORD
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    alterou = False
    for thread_id in iterar_threads_processo(proc.pid):
        handle = kernel32.OpenThread(0x0002, False, thread_id)
        if not handle:
            continue

        try:
            if pausar:
                alterou = kernel32.SuspendThread(handle) != 0xFFFFFFFF or alterou
            else:
                while kernel32.ResumeThread(handle) > 0:
                    alterou = True
        finally:
            kernel32.CloseHandle(handle)

    return alterou



def criar_configuracao_padrao():
    return {
        "format": output_format,
        "video": codec_video,
        "audio": codec_audio,
    }


def obter_configuracao_arquivo(caminho):
    if caminho not in file_settings:
        file_settings[caminho] = criar_configuracao_padrao()
    return file_settings[caminho]


def formatar_item_arquivo(caminho):
    cfg = obter_configuracao_arquivo(caminho)
    video = encontrar_rotulo_codec(video_codec_options, cfg.get("video"), cfg.get("video", ""))
    audio_encoder = cfg.get("audio")
    audio = "sem audio" if cfg.get("format") == "gif" else encontrar_rotulo_codec(audio_codec_options, audio_encoder, audio_encoder or "")
    return f"{Path(caminho).name}  ->  .{cfg.get('format', output_format)} | {video} + {audio}"


def atualizar_lista_arquivos():
    listbox_arquivos.delete(0, tk.END)
    for arquivo in selected_files:
        listbox_arquivos.insert(tk.END, formatar_item_arquivo(arquivo))

def remover_arquivo_convertido(caminho):
    try:
        idx_remover = selected_files.index(caminho)
        selected_files.pop(idx_remover)
        file_settings.pop(caminho, None)
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


def get_ffmpeg_output_args(output_ext, video_encoder=None, audio_encoder=None):
    global codec_video, codec_audio
    output_ext = output_ext.lower().lstrip('.')
    video_encoder = video_encoder or codec_video
    audio_encoder = audio_encoder or codec_audio

    if output_ext == "gif":
        return [
            "-map", "0:v:0",
            "-an",
            "-vf", "fps=12,scale=trunc(iw/2)*2:-1:flags=lanczos",
            "-c:v", video_encoder,
            "-loop", "0",
        ]

    if output_ext == "mxf":
        return [
            "-map", "0:v:0",
            "-map", "0:a?",
            "-c:v", video_encoder,
            "-pix_fmt", "yuv422p",
            "-b:v", "50M",
            "-c:a", audio_encoder,
            "-ar", "48000",
            "-f", "mxf",
        ]

    if output_ext == "ogv":
        return ["-map", "0:v:0", "-map", "0:a?", "-c:v", video_encoder, "-c:a", audio_encoder, "-f", "ogg"]

    if output_ext == "vob":
        return ["-map", "0:v:0", "-map", "0:a?", "-c:v", video_encoder, "-c:a", audio_encoder, "-f", "vob"]

    return ["-map", "0:v:0", "-map", "0:a?", "-c:v", video_encoder, "-c:a", audio_encoder]


def converter_videos(arquivos):
    global current_process, conversion_stop_requested, conversion_paused
    if not arquivos:
        executar_na_ui(messagebox.showwarning, "Aviso", "Nenhum arquivo selecionado.")
        registrar_log("Aviso: tentativa de conversao sem arquivos selecionados.")
        return

    configurar_botoes_conversao(False)
    
    total_arquivos = len(arquivos)
    registrar_log(f"Iniciando conversao de {total_arquivos} arquivo(s).")
    
    for idx, caminho in enumerate(arquivos):
        with conversion_lock:
            if conversion_stop_requested:
                break

        vob = Path(caminho)
        cfg_arquivo = obter_configuracao_arquivo(caminho)
        formato_saida = cfg_arquivo.get("format", output_format)
        video_encoder = cfg_arquivo.get("video", codec_video)
        audio_encoder = cfg_arquivo.get("audio", codec_audio)
        saida = vob.with_suffix(f".{formato_saida}")
        
        atualizar_status(f"Convertendo ({idx+1}/{total_arquivos}): {vob.name} -> .{formato_saida}")

        comando = ["ffmpeg", "-y", "-i", str(vob)]
        codec_args = get_ffmpeg_output_args(
            formato_saida,
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
            with conversion_lock:
                current_process = proc
        except FileNotFoundError:
            registrar_log("Erro: ffmpeg nao foi encontrado no PATH do sistema.")
            atualizar_status("Erro: ffmpeg não encontrado")
            executar_na_ui(messagebox.showerror, "Erro", "FFmpeg não foi encontrado. Verifique se ele está instalado e no PATH.")
            configurar_botoes_conversao(True)
            return
        
        duracao_total = 0
        linhas_erro = []
        
        for linha in proc.stderr:
            with conversion_lock:
                if conversion_stop_requested:
                    break

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
        
        with conversion_lock:
            parada_solicitada = conversion_stop_requested

        if parada_solicitada and proc.poll() is None:
            proc.terminate()

        proc.wait()

        with conversion_lock:
            if current_process is proc:
                current_process = None
            conversion_paused = False
            parada_solicitada = conversion_stop_requested

        if parada_solicitada:
            conversion_stop_requested = False
            atualizar_status("Conversao interrompida")
            atualizar_progresso(0)
            registrar_log(f"Conversao interrompida durante: {vob.name}")
            configurar_botoes_conversao(True)
            return

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
    
    with conversion_lock:
        parada_solicitada = conversion_stop_requested
        conversion_stop_requested = False
        current_process = None
        conversion_paused = False

    if parada_solicitada:
        atualizar_status("Conversao interrompida")
        atualizar_progresso(0)
        registrar_log("Conversao interrompida pelo usuario.")
        configurar_botoes_conversao(True)
        return

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
        file_settings.clear()
        for arquivo in selected_files:
            file_settings[arquivo] = criar_configuracao_padrao()
        atualizar_lista_arquivos()


def obter_preset_codec(formato=None):
    return codec_presets_por_formato.get((formato or output_format).lower(), ("H.264", "AAC"))


def atualizar_recomendacao_codec():
    if "label_recomendacao_codec" not in globals():
        return

    video_recomendado, audio_recomendado = obter_preset_codec()
    if audio_recomendado:
        texto = f"Recomendado para .{output_format}: {video_recomendado} + {audio_recomendado}"
        executar_na_ui(menu_audio.config, state=tk.NORMAL)
    else:
        texto = f"Recomendado para .{output_format}: {video_recomendado}, sem audio"
        if "menu_audio_var" in globals():
            menu_audio_var.set("Sem audio")
        executar_na_ui(menu_audio.config, state=tk.DISABLED)

    executar_na_ui(label_recomendacao_codec.config, text=texto)


def aplicar_preset_codec(formato=None):
    global codec_video, codec_audio
    video_recomendado, audio_recomendado = obter_preset_codec(formato)
    codec_video = video_codec_options[video_recomendado]

    if "menu_video_var" in globals():
        menu_video_var.set(video_recomendado)

    if audio_recomendado:
        codec_audio = audio_codec_options[audio_recomendado]
        if "menu_audio_var" in globals():
            menu_audio_var.set(audio_recomendado)


def atualizar_formato(formato):
    global output_format
    output_format = formato
    aplicar_preset_codec(formato)
    atualizar_recomendacao_codec()
    salvar_configuracoes()

def atualizar_codec_video(codec):
    global codec_video
    codec_video = video_codec_options[codec]
    salvar_configuracoes()

def atualizar_codec_audio(codec):
    global codec_audio
    codec_audio = audio_codec_options[codec]
    salvar_configuracoes()



def alternar_painel_codecs():
    global codecs_visiveis
    codecs_visiveis = not codecs_visiveis
    if codecs_visiveis:
        frame_codecs.pack(before=label_arquivos, fill=tk.X, padx=18, pady=(0, 10))
        btn_toggle_codecs.config(text="Recolher codecs")
    else:
        frame_codecs.pack_forget()
        btn_toggle_codecs.config(text="Mostrar codecs")


def configurar_arquivo_selecionado():
    selecionado = listbox_arquivos.curselection()
    if not selecionado:
        messagebox.showwarning("Aviso", "Selecione um arquivo para configurar.")
        return
    abrir_painel_config_arquivo(selected_files[selecionado[0]])


def abrir_painel_config_arquivo(caminho):
    cfg = dict(obter_configuracao_arquivo(caminho))
    janela = tk.Toplevel(root)
    janela.title(f"Configurar: {Path(caminho).name}")
    janela.transient(root)
    janela.grab_set()
    janela.resizable(False, False)
    janela.configure(bg=root.cget("bg"))

    ttk.Label(janela, text=Path(caminho).name, style="Title.TLabel").pack(anchor="w", padx=16, pady=(14, 4))
    label_recomendacao = ttk.Label(janela, text="", style="Muted.TLabel")
    label_recomendacao.pack(anchor="w", padx=16, pady=(0, 10))

    frame = ttk.LabelFrame(janela, text="Saida", padding=(12, 10))
    frame.pack(fill=tk.X, padx=16, pady=(0, 12))

    ttk.Label(frame, text="Formato", style="Card.TLabel").pack(anchor="w")

    vars_painel = {}

    def atualizar_recomendacao_local():
        video_rec, audio_rec = obter_preset_codec(cfg["format"])
        if audio_rec:
            label_recomendacao.config(text=f"Recomendado para .{cfg['format']}: {video_rec} + {audio_rec}")
            menu_audio_local.config(state=tk.NORMAL)
        else:
            label_recomendacao.config(text=f"Recomendado para .{cfg['format']}: {video_rec}, sem audio")
            vars_painel["audio"].set("Sem audio")
            menu_audio_local.config(state=tk.DISABLED)

    def aplicar_preset_local(formato):
        video_rec, audio_rec = obter_preset_codec(formato)
        cfg["video"] = video_codec_options[video_rec]
        vars_painel["video"].set(video_rec)
        if audio_rec:
            cfg["audio"] = audio_codec_options[audio_rec]
            vars_painel["audio"].set(audio_rec)

    def selecionar_formato_local(formato):
        cfg["format"] = formato
        aplicar_preset_local(formato)
        atualizar_recomendacao_local()

    menu_formato_local, vars_painel["format"] = criar_menu_selecao(frame, formatos_saida, cfg.get("format", output_format), selecionar_formato_local, width=12)
    menu_formato_local.pack(anchor="w", pady=(2, 10))

    frame_codecs_local = tk.Frame(frame)
    frame_codecs_local.pack(fill=tk.X)

    frame_video = tk.Frame(frame_codecs_local)
    frame_video.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
    ttk.Label(frame_video, text="Video", style="Card.TLabel").pack(anchor="w")

    def selecionar_video_local(codec):
        cfg["video"] = video_codec_options[codec]

    menu_video_local, vars_painel["video"] = criar_menu_selecao(
        frame_video,
        list(video_codec_options.keys()),
        encontrar_rotulo_codec(video_codec_options, cfg.get("video"), "H.264"),
        selecionar_video_local,
        width=18,
    )
    menu_video_local.pack(fill=tk.X, pady=(2, 0))

    frame_audio = tk.Frame(frame_codecs_local)
    frame_audio.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0))
    ttk.Label(frame_audio, text="Audio", style="Card.TLabel").pack(anchor="w")

    def selecionar_audio_local(codec):
        cfg["audio"] = audio_codec_options[codec]

    menu_audio_local, vars_painel["audio"] = criar_menu_selecao(
        frame_audio,
        list(audio_codec_options.keys()),
        encontrar_rotulo_codec(audio_codec_options, cfg.get("audio"), "AAC"),
        selecionar_audio_local,
        width=18,
    )
    menu_audio_local.pack(fill=tk.X, pady=(2, 0))

    def salvar_arquivo():
        file_settings[caminho] = cfg
        atualizar_lista_arquivos()
        janela.destroy()

    frame_acoes = tk.Frame(janela)
    frame_acoes.pack(fill=tk.X, padx=16, pady=(0, 14))
    ttk.Button(frame_acoes, text="Aplicar", command=salvar_arquivo, style="Success.TButton").pack(side=tk.RIGHT, padx=(6, 0))
    ttk.Button(frame_acoes, text="Cancelar", command=janela.destroy).pack(side=tk.RIGHT)

    atualizar_recomendacao_local()
    aplicar_tema(janela, dark_mode)

def alternar_pausa():
    global conversion_paused
    with conversion_lock:
        proc = current_process
        pausar = not conversion_paused

    if proc is None or proc.poll() is not None:
        return

    if not alterar_pausa_processo(proc, pausar):
        registrar_log("Nao foi possivel alterar a pausa do processo atual.")
        return

    with conversion_lock:
        conversion_paused = pausar

    if pausar:
        executar_na_ui(btn_pausar.config, text="Continuar")
        atualizar_status("Conversao pausada")
        registrar_log("Conversao pausada.")
    else:
        executar_na_ui(btn_pausar.config, text="Pausar")
        atualizar_status("Conversao retomada")
        registrar_log("Conversao retomada.")


def parar_conversao():
    global conversion_stop_requested, conversion_paused
    with conversion_lock:
        conversion_stop_requested = True
        conversion_paused = False
        proc = current_process

    executar_na_ui(btn_parar.config, state=tk.DISABLED)
    executar_na_ui(btn_pausar.config, state=tk.DISABLED, text="Pausar")
    atualizar_status("Parando conversao...")
    registrar_log("Parada solicitada pelo usuario.")

    if proc is not None and proc.poll() is None:
        alterar_pausa_processo(proc, False)
        proc.terminate()


def iniciar_conversao():
    global conversion_stop_requested, conversion_paused
    if selected_files:
        arquivos = list(selected_files)
        with conversion_lock:
            conversion_stop_requested = False
            conversion_paused = False
        configurar_botoes_conversao(False)
        threading.Thread(target=converter_videos, args=(arquivos,), daemon=True).start()
    else:
        messagebox.showwarning("Aviso", "Selecione ao menos um arquivo.")


def aplicar_tema(janela, modo_escuro):
    cores = {
        "bg": "#0f172a" if modo_escuro else "#f8fafc",
        "fg": "#f1f5f9" if modo_escuro else "#0f172a",
        "muted": "#94a3b8" if modo_escuro else "#64748b",
        "field": "#1e293b" if modo_escuro else "#ffffff",
        "button": "#334155" if modo_escuro else "#e2e8f0",
        "button_hover": "#475569" if modo_escuro else "#cbd5e1",
        "border": "#334155" if modo_escuro else "#e2e8f0",
        "select": "#2563eb" if modo_escuro else "#bfdbfe",
        "accent": "#3b82f6",          # Blue 500
        "accent_hover": "#2563eb",    # Blue 600
        "success": "#10b981",         # Emerald 500
        "success_hover": "#059669",   # Emerald 600
        "warning": "#f59e0b",         # Amber 500
        "warning_hover": "#d97706",   # Amber 600
        "danger": "#ef4444",          # Red 500
        "danger_hover": "#dc2626",    # Red 600
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
    style.configure("TButton", background=cores["button"], foreground=cores["fg"], borderwidth=0, padding=(16, 8), font=("Segoe UI", 9, "bold"))
    style.map("TButton", background=[("active", cores["button_hover"]), ("disabled", cores["border"])])
    style.configure("Accent.TButton", background=cores["accent"], foreground="#ffffff")
    style.map("Accent.TButton", background=[("active", cores["accent_hover"]), ("disabled", cores["border"])])
    style.configure("Success.TButton", background=cores["success"], foreground="#ffffff", padding=(18, 9), font=("Segoe UI", 10, "bold"))
    style.map("Success.TButton", background=[("active", cores["success_hover"]), ("disabled", cores["border"])])
    style.configure("Warning.TButton", background=cores["warning"], foreground="#ffffff", padding=(14, 9), font=("Segoe UI", 10, "bold"))
    style.map("Warning.TButton", background=[("active", cores["warning_hover"]), ("disabled", cores["border"])])
    style.configure("Danger.TButton", background=cores["danger"], foreground="#ffffff", padding=(14, 9), font=("Segoe UI", 10, "bold"))
    style.map("Danger.TButton", background=[("active", cores["danger_hover"]), ("disabled", cores["border"])])
    style.configure("TMenubutton", background=cores["field"], foreground=cores["fg"], bordercolor=cores["border"], padding=(12, 8), font=("Segoe UI", 9))
    style.map("TMenubutton", background=[("active", cores["button_hover"])], foreground=[("active", cores["fg"])])
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
    style.configure("Horizontal.TProgressbar", background=cores["success"], troughcolor=cores["field"], borderwidth=0, thickness=10)
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
                font=("Segoe UI", 10),
                relief=tk.FLAT,
                borderwidth=0,
            )

        for filho in widget.winfo_children():
            aplicar_widget(filho)

    janela.configure(bg=cores["bg"])
    aplicar_widget(janela)
    for menu in selection_menus:
        try:
            menu.configure(
                background=cores["field"],
                foreground=cores["fg"],
                activebackground=cores["select"],
                activeforeground=cores["fg"],
                selectcolor=cores["field"],
                borderwidth=0,
                relief=tk.FLAT,
            )
        except tk.TclError:
            pass


def criar_menu_selecao(parent, opcoes, valor_inicial, ao_selecionar, width=20):
    variavel = tk.StringVar(value=valor_inicial)
    botao = ttk.Menubutton(parent, textvariable=variavel, width=width)
    menu = tk.Menu(botao, tearoff=False)

    def selecionar(opcao):
        variavel.set(opcao)
        ao_selecionar(opcao)

    for opcao in opcoes:
        menu.add_command(label=opcao, command=lambda item=opcao: selecionar(item))

    botao.configure(menu=menu)
    botao.menu = menu
    selection_menus.append(menu)
    return botao, variavel


def main():
    global btn_converter, btn_pausar, btn_parar, btn_selecionar, btn_toggle_codecs, frame_codecs, menu_video, menu_video_var, menu_audio, menu_audio_var, label_recomendacao_codec, listbox_arquivos, progress_bar, label_progresso, label_status, label_arquivos, root, log_text
    
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

    # --- ABA VÍDEO ---
    header_frame = tk.Frame(aba_video)
    header_frame.pack(fill=tk.X, padx=24, pady=(24, 16))
    
    ttk.Label(header_frame, text="Conversão de Vídeo", style="Title.TLabel").pack(anchor="w")
    ttk.Label(header_frame, text="Selecione arquivos para converter em massa.", style="Muted.TLabel").pack(anchor="w")

    # Card Superior: Ações e Formato
    top_card = ttk.Frame(aba_video, style="Card.TFrame")
    top_card.pack(fill=tk.X, padx=18, pady=(0, 12))
    
    frame_botoes = ttk.Frame(top_card, style="Card.TFrame") # Usar estilo do card
    frame_botoes.pack(fill=tk.X, padx=12, pady=12)

    btn_selecionar = ttk.Button(frame_botoes, text="Adicionar Arquivos", command=selecionar_arquivos, style="Accent.TButton")
    btn_selecionar.pack(side=tk.LEFT, padx=(0, 8))

    btn_remover = ttk.Button(frame_botoes, text="Remover", command=lambda: remover_arquivo())
    btn_remover.pack(side=tk.LEFT, padx=8)

    btn_configurar_arquivo = ttk.Button(frame_botoes, text="Ajustar Individual", command=configurar_arquivo_selecionado)
    btn_configurar_arquivo.pack(side=tk.LEFT, padx=8)
    
    # Separador visual
    tk.Frame(frame_botoes, width=2, bg="#cbd5e1").pack(side=tk.LEFT, fill=tk.Y, padx=12)

    ttk.Label(frame_botoes, text="Saída Global:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(4, 8))
    menu_formato, _ = criar_menu_selecao(frame_botoes, formatos_saida, output_format, atualizar_formato, width=8)
    menu_formato.pack(side=tk.LEFT)

    # Card de Codecs
    btn_toggle_codecs = ttk.Button(aba_video, text="Recolher codecs", command=alternar_painel_codecs, style="TButton")
    btn_toggle_codecs.pack(anchor="e", padx=24, pady=(0, 6))

    frame_codecs = ttk.LabelFrame(aba_video, text=" Configurações de Codec (Padrão) ", padding=(16, 12))
    frame_codecs.pack(fill=tk.X, padx=18, pady=(0, 10))

    label_recomendacao_codec = ttk.Label(frame_codecs, text="", font=("Segoe UI", 9, "italic"))
    label_recomendacao_codec.pack(anchor="w", pady=(0, 12))

    frame_menus_codec = ttk.Frame(frame_codecs, style="Card.TFrame")
    frame_menus_codec.pack(fill=tk.X)

    frame_codec_video = ttk.Frame(frame_menus_codec, style="Card.TFrame")
    frame_codec_video.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
    ttk.Label(frame_codec_video, text="Vídeo:", style="Card.TLabel").pack(anchor="w")
    codecs_video = list(video_codec_options.keys())
    menu_video, menu_video_var = criar_menu_selecao(
        frame_codec_video,
        codecs_video,
        encontrar_rotulo_codec(video_codec_options, codec_video, "H.264"),
        atualizar_codec_video,
        width=20,
    )
    menu_video.pack(pady=(2, 0), fill=tk.X)

    frame_codec_audio = ttk.Frame(frame_menus_codec, style="Card.TFrame")
    frame_codec_audio.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0))
    ttk.Label(frame_codec_audio, text="Áudio:", style="Card.TLabel").pack(anchor="w")
    codecs_audio = list(audio_codec_options.keys())
    menu_audio, menu_audio_var = criar_menu_selecao(
        frame_codec_audio,
        codecs_audio,
        encontrar_rotulo_codec(audio_codec_options, codec_audio, "AAC"),
        atualizar_codec_audio,
        width=20,
    )
    menu_audio.pack(pady=(2, 0), fill=tk.X)

    # Listagem de Arquivos
    label_arquivos = ttk.Label(aba_video, text="Fila de Conversão", font=("Segoe UI", 10, "bold"))
    label_arquivos.pack(anchor="w", padx=24, pady=(10, 5))
    
    frame_listbox = tk.Frame(aba_video)
    frame_listbox.pack(padx=18, pady=(0, 10), fill=tk.BOTH, expand=True)
    scrollbar = tk.Scrollbar(frame_listbox)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    listbox_arquivos = tk.Listbox(frame_listbox, yscrollcommand=scrollbar.set, height=8)
    listbox_arquivos.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    listbox_arquivos.bind("<Double-Button-1>", lambda _event: configurar_arquivo_selecionado())
    scrollbar.config(command=listbox_arquivos.yview)
    
    # Footer: Status e Progresso
    footer_frame = tk.Frame(aba_video)
    footer_frame.pack(fill=tk.X, padx=24, pady=(10, 24))

    status_line = tk.Frame(footer_frame)
    status_line.pack(fill=tk.X)
    label_status = ttk.Label(status_line, text="Aguardando início", style="Muted.TLabel")
    label_status.pack(side=tk.LEFT)
    label_progresso = ttk.Label(status_line, text="0%", font=("Segoe UI", 9, "bold"))
    label_progresso.pack(side=tk.RIGHT)

    progress_bar = ttk.Progressbar(footer_frame, orient=tk.HORIZONTAL, mode='determinate', style="Horizontal.TProgressbar")
    progress_bar.pack(fill=tk.X, pady=(5, 15))

    frame_acoes = tk.Frame(footer_frame)
    frame_acoes.pack(anchor="center")

    btn_converter = ttk.Button(frame_acoes, text="INICIAR CONVERSÃO", width=25, command=iniciar_conversao, style="Success.TButton")
    btn_converter.pack(side=tk.LEFT, padx=10)

    btn_pausar = ttk.Button(frame_acoes, text="Pausar", width=12, command=alternar_pausa, style="Warning.TButton", state=tk.DISABLED)
    btn_pausar.pack(side=tk.LEFT, padx=10)

    btn_parar = ttk.Button(frame_acoes, text="Parar", width=12, command=parar_conversao, style="Danger.TButton", state=tk.DISABLED)
    btn_parar.pack(side=tk.LEFT, padx=10)

    atualizar_recomendacao_codec()

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
        caminho = selected_files.pop(idx)
        file_settings.pop(caminho, None)
        atualizar_lista_arquivos()


if __name__ == "__main__":
    main()
