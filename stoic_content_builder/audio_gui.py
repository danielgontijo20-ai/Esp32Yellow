#!/usr/bin/env python3
"""Diário Estoico — Interface Tkinter do Audio Builder (Kokoro).

Reutiliza o gerador existente (src.audio.builder).
Não altera o fluxo de linha de comando (generate_audio.py).

Uso:
  python audio_gui.py
"""

from __future__ import annotations

import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from src.audio import config
from src.audio.builder import (
    load_lesson,
    peek_json_label,
    resolve_output_stem,
    run_audio_from_json_files,
)
from src.audio.report import format_bytes, format_duration


class FileRow:
    """Uma linha da lista (checkbox + caminho + rótulo)."""

    def __init__(self, path: Path, label: str, checked: bool = True) -> None:
        self.path = path
        self.label = label
        self.var = tk.BooleanVar(value=checked)


class AudioGuiApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Diário Estoico — Audio Builder")
        self.geometry("820x640")
        self.minsize(640, 480)

        self.rows: list[FileRow] = []
        self.output_dir = tk.StringVar(value=str(config.OUTPUT_DIR_GUI))
        self.voices = list(config.AVAILABLE_VOICES)
        if config.VOICE not in self.voices:
            self.voices.insert(0, config.VOICE)
        self.voice_var = tk.StringVar(value=config.VOICE)
        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_text = tk.StringVar(value="Progresso: 0 / 0")
        self.status_text = tk.StringVar(value="Pronto.")
        self._worker: threading.Thread | None = None
        self._queue: queue.Queue = queue.Queue()
        self._generating = False

        self._build_ui()
        self.after(100, self._poll_queue)

    def _build_ui(self) -> None:
        pad = {"padx": 10, "pady": 4}

        header = ttk.Label(
            self,
            text="Diário Estoico — Gerador de Áudio (Kokoro)",
            font=("Segoe UI", 13, "bold"),
        )
        header.pack(anchor=tk.W, padx=10, pady=(10, 2))

        # Arquivos
        files_frame = ttk.LabelFrame(self, text="Arquivos JSON (lesson.json)", padding=8)
        files_frame.pack(fill=tk.BOTH, expand=True, **pad)

        btns = ttk.Frame(files_frame)
        btns.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(btns, text="Selecionar arquivos", command=self._select_files).pack(
            side=tk.LEFT
        )
        ttk.Button(btns, text="Selecionar todos", command=self._select_all).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(btns, text="Desmarcar todos", command=self._deselect_all).pack(
            side=tk.LEFT
        )
        ttk.Button(btns, text="Remover selecionados", command=self._remove_selected).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(btns, text="Limpar lista", command=self._clear_list).pack(side=tk.LEFT)

        list_wrap = ttk.Frame(files_frame)
        list_wrap.pack(fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(list_wrap, highlightthickness=0, height=160)
        scrollbar = ttk.Scrollbar(list_wrap, orient=tk.VERTICAL, command=self.canvas.yview)
        self.list_inner = ttk.Frame(self.canvas)
        self.list_inner.bind(
            "<Configure>",
            lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.create_window((0, 0), window=self.list_inner, anchor=tk.NW)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Opções
        opts = ttk.LabelFrame(self, text="Opções", padding=8)
        opts.pack(fill=tk.X, **pad)

        voice_row = ttk.Frame(opts)
        voice_row.pack(fill=tk.X, pady=2)
        ttk.Label(voice_row, text="Voz:").pack(side=tk.LEFT)
        self.voice_combo = ttk.Combobox(
            voice_row,
            textvariable=self.voice_var,
            values=self.voices,
            state="readonly",
            width=18,
        )
        self.voice_combo.pack(side=tk.LEFT, padx=6)

        dest_row = ttk.Frame(opts)
        dest_row.pack(fill=tk.X, pady=2)
        ttk.Label(dest_row, text="Pasta de destino:").pack(side=tk.LEFT)
        ttk.Entry(dest_row, textvariable=self.output_dir).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=6
        )
        ttk.Button(dest_row, text="Selecionar pasta", command=self._select_output).pack(
            side=tk.LEFT
        )

        # Gerar
        self.btn_generate = ttk.Button(
            self, text="GERAR ÁUDIOS", command=self._start_generation
        )
        self.btn_generate.pack(fill=tk.X, padx=10, pady=8)

        # Progresso
        prog = ttk.Frame(self)
        prog.pack(fill=tk.X, **pad)
        ttk.Label(prog, textvariable=self.progress_text).pack(anchor=tk.W)
        self.progress_bar = ttk.Progressbar(
            prog, variable=self.progress_var, maximum=100
        )
        self.progress_bar.pack(fill=tk.X, pady=4)
        ttk.Label(prog, textvariable=self.status_text).pack(anchor=tk.W)

        # Log
        log_frame = ttk.LabelFrame(self, text="Log", padding=6)
        log_frame.pack(fill=tk.BOTH, expand=True, **pad)
        self.log = tk.Text(log_frame, height=12, wrap=tk.WORD, font=("Consolas", 9))
        self.log.pack(fill=tk.BOTH, expand=True)
        self.log.configure(state=tk.DISABLED)

    # ------------------------------------------------------------------ UI helpers
    def _append_log(self, message: str) -> None:
        self.log.configure(state=tk.NORMAL)
        self.log.insert(tk.END, message + "\n")
        self.log.see(tk.END)
        self.log.configure(state=tk.DISABLED)

    def _refresh_list(self) -> None:
        for child in self.list_inner.winfo_children():
            child.destroy()
        for row in self.rows:
            cb = ttk.Checkbutton(self.list_inner, text=row.label, variable=row.var)
            cb.pack(anchor=tk.W, fill=tk.X, pady=1)

    def _select_files(self) -> None:
        # Pasta inicial: build mais recente, se existir
        initial = APP_DIR / "output"
        builds = sorted(initial.glob("build_*")) if initial.exists() else []
        if builds:
            initial = builds[-1] / "lessons"

        paths = filedialog.askopenfilenames(
            title="Selecionar arquivos JSON (lesson.json)",
            filetypes=[
                ("JSON da lição", "*.json"),
                ("Todos", "*.*"),
            ],
            initialdir=str(initial),
        )
        if not paths:
            return
        existing = {r.path.resolve() for r in self.rows}
        for p in paths:
            path = Path(p)
            if path.resolve() in existing:
                continue
            label = peek_json_label(path)
            self.rows.append(FileRow(path, label, checked=True))
        self._refresh_list()
        self._append_log(f"Arquivos na lista: {len(self.rows)}")

    def _select_output(self) -> None:
        path = filedialog.askdirectory(
            title="Selecionar pasta de destino",
            initialdir=self.output_dir.get() or str(config.OUTPUT_DIR_GUI),
        )
        if path:
            self.output_dir.set(path)

    def _select_all(self) -> None:
        for row in self.rows:
            row.var.set(True)

    def _deselect_all(self) -> None:
        for row in self.rows:
            row.var.set(False)

    def _remove_selected(self) -> None:
        self.rows = [r for r in self.rows if not r.var.get()]
        self._refresh_list()

    def _clear_list(self) -> None:
        self.rows.clear()
        self._refresh_list()

    def _checked_rows(self) -> list[FileRow]:
        return [r for r in self.rows if r.var.get()]

    # ----------------------------------------------------------- overwrite / start
    def _ask_overwrite(self, filename: str) -> str:
        """Retorna: overwrite | skip | overwrite_all | skip_all | cancel."""
        dialog = tk.Toplevel(self)
        dialog.title("Arquivo existente")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)

        result = {"value": "cancel"}

        ttk.Label(
            dialog,
            text=f"O arquivo {filename} já existe.\nDeseja substituir?",
            padding=12,
        ).pack()

        btn_row = ttk.Frame(dialog, padding=8)
        btn_row.pack()

        def set_and_close(value: str) -> None:
            result["value"] = value
            dialog.destroy()

        ttk.Button(btn_row, text="Sim", command=lambda: set_and_close("overwrite")).grid(
            row=0, column=0, padx=4, pady=2
        )
        ttk.Button(btn_row, text="Não", command=lambda: set_and_close("skip")).grid(
            row=0, column=1, padx=4, pady=2
        )
        ttk.Button(
            btn_row, text="Sim para todos", command=lambda: set_and_close("overwrite_all")
        ).grid(row=1, column=0, padx=4, pady=2)
        ttk.Button(
            btn_row, text="Não para todos", command=lambda: set_and_close("skip_all")
        ).grid(row=1, column=1, padx=4, pady=2)

        dialog.wait_window()
        return result["value"]

    def _resolve_jobs(self, rows: list[FileRow], out_dir: Path) -> list[Path] | None:
        """Pergunta sobre sobrescrita e devolve a lista final de JSON a processar."""
        ext = config.OUTPUT_FORMAT.lower()
        apply_all: str | None = None  # overwrite | skip
        selected: list[Path] = []

        for row in rows:
            path = row.path
            if not path.exists():
                messagebox.showerror("Erro", f"Arquivo não encontrado:\n{path}")
                return None
            try:
                lesson = load_lesson(path)
                if not lesson.get("segments"):
                    raise ValueError("JSON sem campo segments")
            except Exception as exc:  # noqa: BLE001
                messagebox.showerror(
                    "JSON inválido",
                    f"Não foi possível ler {path.name}:\n{exc}",
                )
                return None

            stem = resolve_output_stem(path, lesson)
            out_file = out_dir / f"{stem}.{ext}"
            alt_wav = out_dir / f"{stem}.wav"
            exists = out_file.exists() or alt_wav.exists()
            existing_name = out_file.name if out_file.exists() else alt_wav.name

            if not exists:
                selected.append(path)
                continue

            decision = apply_all
            if decision is None:
                decision = self._ask_overwrite(existing_name)
                if decision == "overwrite_all":
                    apply_all = "overwrite"
                    decision = "overwrite"
                elif decision == "skip_all":
                    apply_all = "skip"
                    decision = "skip"
                elif decision == "cancel":
                    return None

            if decision == "overwrite":
                out_file.unlink(missing_ok=True)
                alt_wav.unlink(missing_ok=True)
                selected.append(path)
            else:
                self._append_log(f"Ignorado (já existe): {existing_name}")

        return selected

    def _start_generation(self) -> None:
        if self._generating:
            return

        rows = self._checked_rows()
        if not rows:
            messagebox.showwarning(
                "Nenhum arquivo",
                "Selecione pelo menos um arquivo JSON marcado na lista.",
            )
            return

        out_dir = Path(self.output_dir.get().strip())
        if not self.output_dir.get().strip():
            messagebox.showerror("Erro", "Informe a pasta de destino.")
            return
        out_dir.mkdir(parents=True, exist_ok=True)

        jobs = self._resolve_jobs(rows, out_dir)
        if jobs is None:
            return
        if not jobs:
            messagebox.showinfo("Nada a fazer", "Nenhum arquivo restante para gerar.")
            return

        voice = self.voice_var.get().strip() or config.VOICE
        self._generating = True
        self.btn_generate.configure(state=tk.DISABLED)
        self.progress_var.set(0)
        self.progress_text.set(f"Progresso: 0 / {len(jobs)}")
        self.status_text.set("Iniciando...")
        self._append_log("")
        self._append_log("Iniciando geração...")

        def worker() -> None:
            def log_cb(msg: str) -> None:
                self._queue.put(("log", msg))

            def progress_cb(current: int, total: int, message: str) -> None:
                self._queue.put(("progress", current, total, message))

            try:
                report = run_audio_from_json_files(
                    jobs,
                    out_dir,
                    voice=voice,
                    log_callback=log_cb,
                    progress_callback=progress_cb,
                )
                self._queue.put(("done", report))
            except Exception as exc:  # noqa: BLE001
                self._queue.put(("fatal", str(exc)))

        self._worker = threading.Thread(target=worker, daemon=True)
        self._worker.start()

    def _poll_queue(self) -> None:
        try:
            while True:
                item = self._queue.get_nowait()
                kind = item[0]
                if kind == "log":
                    self._append_log(item[1])
                elif kind == "progress":
                    _k, current, total, message = item
                    pct = (100.0 * current / total) if total else 0.0
                    self.progress_var.set(pct)
                    self.progress_text.set(f"Progresso: {current} / {total}")
                    self.status_text.set(message)
                elif kind == "done":
                    report = item[1]
                    self._generating = False
                    self.btn_generate.configure(state=tk.NORMAL)
                    self.progress_var.set(100)
                    self.status_text.set("Concluído.")
                    summary = (
                        f"Concluído: {report.ok_count} OK, "
                        f"{report.error_count} erro(s), "
                        f"tempo {format_duration(report.elapsed_sec)}, "
                        f"total {format_bytes(report.total_bytes)}"
                    )
                    self._append_log(summary)
                    if report.error_count:
                        messagebox.showwarning("Concluído com erros", summary)
                    else:
                        messagebox.showinfo("Concluído", summary)
                elif kind == "fatal":
                    self._generating = False
                    self.btn_generate.configure(state=tk.NORMAL)
                    self.status_text.set("Erro.")
                    self._append_log(f"ERRO FATAL: {item[1]}")
                    messagebox.showerror("Erro", item[1])
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)


def main() -> None:
    missing: list[str] = []
    for mod in ("soundfile", "numpy", "kokoro"):
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    if missing:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Dependências ausentes",
            "Faltam pacotes no Python atual:\n\n"
            + "\n".join(f"- {m}" for m in missing)
            + "\n\nAtive o venv e instale:\n"
            ".venv\\Scripts\\activate\n"
            "pip install -r requirements-audio.txt",
        )
        raise SystemExit(1)

    app = AudioGuiApp()
    app.mainloop()


if __name__ == "__main__":
    main()
