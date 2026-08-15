#!/usr/bin/env python3
"""Diário Estoico — Content Builder

Aplicação local (Tkinter) para transformar TXT de OCR em JSON estruturado.
Não utiliza APIs externas, nuvem ou serviços de IA.
"""

from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

# Garante que o pacote src seja importável ao executar app.py
APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from src.builder import BuildResult, process_file
from src.models import Lesson


class ResultsViewer(tk.Toplevel):
    """Janela para navegar visualmente pelas lições processadas."""

    def __init__(self, parent: tk.Tk, lessons: list[Lesson]) -> None:
        super().__init__(parent)
        self.title("Visualizar Resultados — Diário Estoico")
        self.geometry("780x640")
        self.minsize(560, 420)

        self.lessons = lessons
        self.index = 0

        self._build_ui()
        self._show_lesson()

    def _build_ui(self) -> None:
        nav = ttk.Frame(self, padding=8)
        nav.pack(fill=tk.X)

        self.btn_prev = ttk.Button(nav, text="← ANTERIOR", command=self._prev)
        self.btn_prev.pack(side=tk.LEFT)

        self.lbl_pos = ttk.Label(nav, text="", font=("Segoe UI", 10, "bold"))
        self.lbl_pos.pack(side=tk.LEFT, expand=True)

        self.btn_next = ttk.Button(nav, text="PRÓXIMA →", command=self._next)
        self.btn_next.pack(side=tk.RIGHT)

        body = ttk.Frame(self, padding=8)
        body.pack(fill=tk.BOTH, expand=True)

        self.txt = scrolledtext.ScrolledText(
            body,
            wrap=tk.WORD,
            font=("Consolas", 10),
            state=tk.DISABLED,
        )
        self.txt.pack(fill=tk.BOTH, expand=True)

    def _show_lesson(self) -> None:
        lesson = self.lessons[self.index]
        total = len(self.lessons)
        self.lbl_pos.config(text=f"Lição {self.index + 1} / {total}")

        segments_block = "\n".join(
            f"  [{s.id}|{s.type}] {s.text}" for s in lesson.segments
        ) or "  (nenhum)"

        content = (
            f"ID: {lesson.id}\n"
            f"Data: {lesson.date}\n"
            f"\n"
            f"Título:\n{lesson.title}\n"
            f"\n"
            f"Citação:\n{lesson.quote.text}\n"
            f"\n"
            f"Fonte:\n{lesson.quote.source}\n"
            f"\n"
            f"Texto da reflexão:\n{lesson.text}\n"
            f"\n"
            f"Segmentos ({len(lesson.segments)}):\n{segments_block}\n"
        )

        self.txt.config(state=tk.NORMAL)
        self.txt.delete("1.0", tk.END)
        self.txt.insert(tk.END, content)
        self.txt.config(state=tk.DISABLED)

        self.btn_prev.config(state=tk.NORMAL if self.index > 0 else tk.DISABLED)
        self.btn_next.config(
            state=tk.NORMAL if self.index < total - 1 else tk.DISABLED
        )

    def _prev(self) -> None:
        if self.index > 0:
            self.index -= 1
            self._show_lesson()

    def _next(self) -> None:
        if self.index < len(self.lessons) - 1:
            self.index += 1
            self._show_lesson()


class ContentBuilderApp(tk.Tk):
    """Janela principal do Content Builder."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Diário Estoico — Content Builder")
        self.geometry("720x520")
        self.minsize(560, 400)

        self.input_var = tk.StringVar()
        self.output_var = tk.StringVar(
            value=str(APP_DIR / "output")
        )
        self.last_result: BuildResult | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        pad = {"padx": 12, "pady": 6}

        header = ttk.Label(
            self,
            text="Diário Estoico — Content Builder",
            font=("Segoe UI", 14, "bold"),
        )
        header.pack(anchor=tk.W, padx=12, pady=(12, 4))

        subtitle = ttk.Label(
            self,
            text="Converte TXT (OCR) em pastas JSON estruturadas — 100% local",
            font=("Segoe UI", 9),
        )
        subtitle.pack(anchor=tk.W, padx=12, pady=(0, 8))

        # Arquivo TXT
        row1 = ttk.Frame(self)
        row1.pack(fill=tk.X, **pad)
        ttk.Label(row1, text="Arquivo TXT:", width=16).pack(side=tk.LEFT)
        ttk.Entry(row1, textvariable=self.input_var).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6)
        )
        ttk.Button(row1, text="Selecionar", command=self._select_input).pack(
            side=tk.LEFT
        )

        # Pasta de saída
        row2 = ttk.Frame(self)
        row2.pack(fill=tk.X, **pad)
        ttk.Label(row2, text="Pasta de saída:", width=16).pack(side=tk.LEFT)
        ttk.Entry(row2, textvariable=self.output_var).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6)
        )
        ttk.Button(row2, text="Selecionar", command=self._select_output).pack(
            side=tk.LEFT
        )

        # Botão processar
        actions = ttk.Frame(self)
        actions.pack(fill=tk.X, **pad)
        self.btn_process = ttk.Button(
            actions, text="PROCESSAR", command=self._process
        )
        self.btn_process.pack(side=tk.LEFT)

        self.btn_view = ttk.Button(
            actions,
            text="VISUALIZAR RESULTADOS",
            command=self._view_results,
            state=tk.DISABLED,
        )
        self.btn_view.pack(side=tk.LEFT, padx=8)

        self.btn_open = ttk.Button(
            actions,
            text="ABRIR PASTA DE RESULTADOS",
            command=self._open_results_folder,
            state=tk.DISABLED,
        )
        self.btn_open.pack(side=tk.LEFT)

        # Log
        ttk.Label(self, text="Status / log:").pack(anchor=tk.W, padx=12)
        self.log = scrolledtext.ScrolledText(
            self,
            height=16,
            wrap=tk.WORD,
            font=("Consolas", 9),
            state=tk.DISABLED,
        )
        self.log.pack(fill=tk.BOTH, expand=True, padx=12, pady=(4, 12))

    def _append_log(self, message: str) -> None:
        self.log.config(state=tk.NORMAL)
        self.log.insert(tk.END, message + "\n")
        self.log.see(tk.END)
        self.log.config(state=tk.DISABLED)
        self.update_idletasks()

    def _clear_log(self) -> None:
        self.log.config(state=tk.NORMAL)
        self.log.delete("1.0", tk.END)
        self.log.config(state=tk.DISABLED)

    def _select_input(self) -> None:
        path = filedialog.askopenfilename(
            title="Selecionar arquivo TXT",
            filetypes=[("Arquivos de texto", "*.txt"), ("Todos", "*.*")],
            initialdir=str(APP_DIR / "input"),
        )
        if path:
            self.input_var.set(path)

    def _select_output(self) -> None:
        path = filedialog.askdirectory(
            title="Selecionar pasta de saída",
            initialdir=self.output_var.get() or str(APP_DIR / "output"),
        )
        if path:
            self.output_var.set(path)

    def _process(self) -> None:
        input_path = Path(self.input_var.get().strip())
        output_root = Path(self.output_var.get().strip())

        if not self.input_var.get().strip():
            messagebox.showerror("Erro", "Selecione um arquivo TXT de entrada.")
            return
        if not self.output_var.get().strip():
            messagebox.showerror("Erro", "Selecione a pasta de saída.")
            return

        self._clear_log()
        self.btn_process.config(state=tk.DISABLED)
        self.btn_view.config(state=tk.DISABLED)
        self.btn_open.config(state=tk.DISABLED)
        self.last_result = None

        try:
            result = process_file(
                input_path=input_path,
                output_root=output_root,
                log_callback=self._append_log,
            )
            self.last_result = result
            self.btn_view.config(state=tk.NORMAL)
            self.btn_open.config(state=tk.NORMAL)

            report = result.report
            self._append_log("")
            self._append_log(
                f"Concluído: {report.lessons_found} lições | "
                f"erros={report.error_count()} | avisos={report.warning_count()}"
            )
            self._append_log(f"Relatório: {result.report_path}")

            if report.error_count() > 0:
                messagebox.showwarning(
                    "Concluído com erros",
                    f"Processamento finalizado com {report.error_count()} erro(s).\n"
                    f"Consulte o relatório em:\n{result.report_path}",
                )
            else:
                messagebox.showinfo(
                    "Sucesso",
                    f"{report.lessons_found} lições geradas em:\n{result.build_dir}",
                )
        except Exception as exc:  # noqa: BLE001 — exibir na UI
            self._append_log(f"ERRO: {exc}")
            messagebox.showerror("Erro", str(exc))
        finally:
            self.btn_process.config(state=tk.NORMAL)

    def _view_results(self) -> None:
        if not self.last_result or not self.last_result.lessons:
            messagebox.showinfo(
                "Sem resultados",
                "Processe um arquivo TXT antes de visualizar.",
            )
            return
        ResultsViewer(self, self.last_result.lessons)

    def _open_results_folder(self) -> None:
        if not self.last_result:
            messagebox.showinfo(
                "Sem resultados",
                "Processe um arquivo TXT antes de abrir a pasta.",
            )
            return
        folder = self.last_result.build_dir
        try:
            if sys.platform.startswith("win"):
                import os

                os.startfile(folder)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                import subprocess

                subprocess.run(["open", str(folder)], check=False)
            else:
                import subprocess

                subprocess.run(["xdg-open", str(folder)], check=False)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(
                "Erro",
                f"Não foi possível abrir a pasta:\n{folder}\n\n{exc}",
            )


def main() -> None:
    app = ContentBuilderApp()
    app.mainloop()


if __name__ == "__main__":
    main()
