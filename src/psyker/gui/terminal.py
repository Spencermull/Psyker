"""Embedded terminal widget for Psyker REPL. Drives CLI via IOAdapter."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Qt, QStringListModel, QThread, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QCompleter,
    QHBoxLayout,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..cli import PROMPT_TEXT, create_default_cli
from ..io_layer import strip_ansi

if TYPE_CHECKING:
    from ..cli import PsykerCLI


class AsyncGUIAdapter(QObject):
    """I/O adapter that emits signals for thread-safe UI updates from background execution."""

    write_signal = Signal(str)
    write_error_signal = Signal(str)

    def __init__(self, output: QPlainTextEdit) -> None:
        super().__init__()
        self._output = output
        self.write_signal.connect(self._on_write)
        self.write_error_signal.connect(self._on_write_error)

    def _on_write(self, text: str) -> None:
        plain = strip_ansi(text)
        self._output.appendPlainText(plain)

    def _on_write_error(self, text: str) -> None:
        plain = strip_ansi(text)
        self._output.appendPlainText(plain)

    def write(self, text: str) -> None:
        self.write_signal.emit(text)

    def write_error(self, text: str) -> None:
        self.write_error_signal.emit(text)

    def read_line(self, prompt: str = "") -> str | None:
        return None

    @property
    def supports_colors(self) -> bool:
        return False


class CommandWorker(QObject):
    """Runs execute_line in a background thread."""

    run_requested = Signal(str)
    finished = Signal(int)

    def __init__(self, cli: "PsykerCLI") -> None:
        super().__init__()
        self._cli = cli
        self.run_requested.connect(self._run)

    def _run(self, line: str) -> None:
        code = self._cli.execute_line(line)
        self._cli.last_exit_code = code
        self.finished.emit(code)


class ReplLineEdit(QLineEdit):
    """Input line with command history (up/down) and suggestions."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._history: list[str] = []
        self._history_index = -1
        self._current_draft = ""

    def keyPressEvent(self, event) -> None:  # noqa: ANN001 - Qt event
        from PySide6.QtCore import Qt

        key = event.key()
        if key == Qt.Key.Key_Up or key == Qt.Key.Key_Down:
            comp = self.completer()
            if comp and comp.popup() and comp.popup().isVisible():
                super().keyPressEvent(event)  # Let completer handle
            else:
                self._navigate_history(key == Qt.Key.Key_Up)
                event.accept()
            return
        self._history_index = -1
        self._current_draft = ""
        super().keyPressEvent(event)

    def _navigate_history(self, up: bool) -> None:
        if not self._history:
            return
        if self._history_index < 0:
            self._current_draft = self.text()
            self._history_index = len(self._history) - 1 if up else -1
        if up:
            self._history_index = max(0, self._history_index - 1)
        else:
            self._history_index = min(len(self._history), self._history_index + 1)
        if self._history_index >= len(self._history):
            self._history_index = -1
            self.setText(self._current_draft)
        else:
            self.setText(self._history[self._history_index])

    def push_history(self, line: str) -> None:
        if not line.strip():
            return
        if self._history and self._history[-1] == line:
            return
        self._history.append(line)
        if len(self._history) > 200:
            self._history.pop(0)


class EmbeddedTerminal(QWidget):
    """Terminal-style REPL: output area + input line. Runs Psyker CLI inside the GUI."""

    commandExecuted = Signal(str, int)

    def __init__(self, cli: "PsykerCLI" | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("EmbeddedTerminal")
        self._cli = cli or create_default_cli()
        self._output = self._build_output()
        self._io = AsyncGUIAdapter(self._output)
        self._cli._io = self._io
        self._worker = CommandWorker(self._cli)
        self._thread = QThread()
        self._worker.moveToThread(self._thread)
        self._thread.start()
        self._worker.finished.connect(self._on_command_finished)
        self._pending_line: str = ""
        self._setup_ui()
        self._print_banner()

    def _build_output(self) -> QPlainTextEdit:
        out = QPlainTextEdit()
        out.setReadOnly(True)
        out.setFont(QFont("Consolas", 12))
        out.setObjectName("TerminalOutput")
        out.setStyleSheet(
            "QPlainTextEdit { "
            "background-color: #0d1117; color: #dbe7ff; "
            "border: 1px solid #8b5cf6; border-radius: 8px; "
            "padding: 12px; line-height: 1.3; "
            "}"
        )
        return out

    def _build_completions(self) -> list[str]:
        """Build completion list: commands + agents/workers/tasks for run."""
        completions: list[str] = []
        completions.extend(self._cli.commands.keys())
        completions.extend(f"run {a} {t}" for a in self._cli.runtime.agents for t in self._cli.runtime.tasks)
        completions.extend(f"stx agent {a}" for a in self._cli.runtime.agents)
        completions.extend(f"stx worker {w}" for w in self._cli.runtime.workers)
        completions.extend(f"stx task {t}" for t in self._cli.runtime.tasks)
        return sorted(set(completions))

    def _setup_ui(self) -> None:
        input_line = ReplLineEdit()
        input_line.setPlaceholderText("Type a command and press Enter... (↑↓ history)")
        input_line.setFont(QFont("Consolas", 12))
        input_line.setObjectName("TerminalInput")
        input_line.setStyleSheet(
            "QLineEdit { "
            "background-color: #0d1117; color: #dbe7ff; "
            "border: 1px solid #8b5cf6; border-radius: 8px; "
            "padding: 10px; "
            "}"
            "QLineEdit:focus { border: 1px solid #79c0ff; }"
        )
        input_line.returnPressed.connect(self._on_enter)

        completer = QCompleter(self._build_completions())
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        completer.popup().setStyleSheet(
            "QListView { background-color: #0d1117; color: #dbe7ff; "
            "border: 1px solid #8b5cf6; }"
            "QListView::item:selected { background-color: #1b2538; color: #79c0ff; }"
        )
        input_line.setCompleter(completer)

        controls_row = QHBoxLayout()
        controls_row.setContentsMargins(0, 0, 0, 0)
        controls_row.setSpacing(8)
        controls_row.addStretch(1)

        copy_button = QPushButton("Copy Output")
        copy_button.setObjectName("TerminalCopyButton")
        copy_button.clicked.connect(self.copy_output_to_clipboard)
        controls_row.addWidget(copy_button)

        clear_button = QPushButton("Clear Output")
        clear_button.setObjectName("TerminalClearButton")
        clear_button.clicked.connect(self.clear_output)
        controls_row.addWidget(clear_button)

        controls_style = (
            "QPushButton { "
            "background-color: #0d1117; color: #79c0ff; "
            "border: 1px solid #8b5cf6; border-radius: 6px; "
            "padding: 6px 10px; "
            "}"
            "QPushButton:hover { border: 1px solid #79c0ff; }"
            "QPushButton:pressed { background-color: #131c2a; }"
        )
        copy_button.setStyleSheet(controls_style)
        clear_button.setStyleSheet(controls_style)

        vlayout = QVBoxLayout(self)
        vlayout.setContentsMargins(12, 12, 12, 12)
        vlayout.setSpacing(10)
        vlayout.addWidget(self._output)
        vlayout.addLayout(controls_row)
        vlayout.addWidget(input_line)
        self._input_line = input_line
        self._completer = completer

    def _update_completer(self) -> None:
        self._completer.setModel(QStringListModel(self._build_completions()))

    def copy_output_to_clipboard(self) -> None:
        clipboard = QApplication.clipboard()
        clipboard.setText(self._output.toPlainText())

    def clear_output(self) -> None:
        self._output.clear()

    def _print_banner(self) -> None:
        self._cli._print_startup_banner()

    def _on_enter(self) -> None:
        line = self._input_line.text().strip()
        self._input_line.clear()
        if not line:
            return
        self._input_line.push_history(line)
        self.execute_command(line)

    def _on_command_finished(self, code: int) -> None:
        self.commandExecuted.emit(self._pending_line, code)
        self._update_completer()

    def execute_command(self, line: str) -> int:
        text = line.strip()
        if not text:
            return 0
        self._io.write(f"{PROMPT_TEXT}{text}")
        self._pending_line = text
        self._worker.run_requested.emit(text)
        return 0  # Actual code comes via _on_command_finished
