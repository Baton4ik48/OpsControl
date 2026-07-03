from datetime import datetime

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QTextDocument
from PyQt6.QtPrintSupport import QPrintPreviewDialog, QPrinter
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
    QProgressBar,
    QVBoxLayout,
)

from core.api.base import ApiError
from core.utils.secure import wipe


class _ExportWorker(QThread):
    success = pyqtSignal(list)
    error = pyqtSignal(Exception)

    def __init__(self, api, username: str, master_password: str):
        super().__init__()
        self._api = api
        self._username = username
        self._master_password = master_password

    def run(self):
        try:
            data = self._api.export_all(self._username, self._master_password)
            self.success.emit(data or [])
        except Exception as exc:
            self.error.emit(exc)
        finally:
            wipe(self._master_password)
            self._master_password = ""


class EnvelopePrintDialog(QDialog):
    """Загружает все пароли с бекенда и открывает окно предпросмотра печати."""

    def __init__(
        self, username: str, master_password: str, credentials_api, parent=None
    ):
        super().__init__(parent)
        self.setWindowTitle("Формирование конверта с паролями")
        self.setMinimumWidth(360)
        self.setModal(True)

        layout = QVBoxLayout(self)

        self._label = QLabel("Запрашиваем учётные данные из Vault…")
        layout.addWidget(self._label)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        layout.addWidget(self._progress)

        self._buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

        self._worker = _ExportWorker(credentials_api, username, master_password)
        self._worker.success.connect(self._on_success)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_success(self, entries: list):
        self._progress.setRange(0, 1)
        self._progress.setValue(1)
        self._label.setText(f"Получено записей: {len(entries)}")

        if not entries:
            QMessageBox.information(
                self,
                "Нет данных",
                "В базе не найдено ни одной записи с учётными данными.",
            )
            self.accept()
            return

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.NativeFormat)

        preview = QPrintPreviewDialog(printer, self)
        preview.setWindowTitle("Предпросмотр конверта с паролями")
        preview.paintRequested.connect(lambda p: self._render(p, entries))
        preview.exec()
        self.accept()

    def _on_error(self, exc: Exception):
        self._progress.setRange(0, 1)
        self._progress.setValue(0)

        if isinstance(exc, ApiError):
            if exc.status_code == 403:
                QMessageBox.warning(self, "Доступ запрещён", "Неверный мастер-пароль.")
            elif exc.status_code == 429:
                QMessageBox.warning(
                    self,
                    "Слишком много попыток",
                    f"Попробуйте через {exc.retry_after} сек.",
                )
            else:
                QMessageBox.critical(self, "Ошибка", exc.message)
        else:
            QMessageBox.critical(self, "Ошибка", str(exc))

        self.reject()

    @staticmethod
    def _render(printer: QPrinter, entries: list):
        doc = QTextDocument()
        doc.setDefaultStyleSheet("""
            body  { font-family: Arial, sans-serif; font-size: 9pt; }
            h1    { font-size: 13pt; text-align: center; margin-bottom: 4px; }
            .meta { font-size: 8pt; text-align: center; color: #555; margin-bottom: 12px; }
            table { border-collapse: collapse; width: 100%; font-size: 8pt; }
            th    { background: #2c3e50; color: #fff; padding: 5px 7px;
                    text-align: left; border: 1px solid #bbb; }
            td    { padding: 4px 7px; border: 1px solid #ccc; vertical-align: top; }
            tr:nth-child(even) td { background: #f5f5f5; }
            .warn { font-size: 7pt; color: #b00; margin-top: 14px; text-align: center; }
            """)

        now = datetime.now().strftime("%d.%m.%Y %H:%M")
        rows_html = ""
        for i, e in enumerate(entries, 1):
            rows_html += (
                f"<tr>"
                f"<td>{i}</td>"
                f"<td>{_esc(e.get('branch', ''))}</td>"
                f"<td>{_esc(e.get('server_name', ''))}</td>"
                f"<td>{_esc(e.get('ip', ''))}</td>"
                f"<td>{e.get('port', '')}</td>"
                f"<td>{_esc(e.get('username', ''))}</td>"
                f"<td>{_esc(e.get('password', ''))}</td>"
                f"<td>{_esc(e.get('mnemonic', ''))}</td>"
                f"</tr>"
            )

        html = f"""
        <html><body>
        <h1>Конверт с паролями серверов</h1>
        <div class="meta">Сформировано: {now} &nbsp;|&nbsp; Записей: {len(entries)}</div>
        <table>
          <tr>
            <th>#</th>
            <th>Площадка</th>
            <th>Сервер</th>
            <th>IP</th>
            <th>Порт</th>
            <th>Логин</th>
            <th>Пароль</th>
            <th>Мнемоника</th>
          </tr>
          {rows_html}
        </table>
        <div class="warn">
          КОНФИДЕНЦИАЛЬНО — хранить в опечатанном конверте в сейфе.
          Запрещено копировать и передавать третьим лицам.
        </div>
        </body></html>
        """

        doc.setHtml(html)
        doc.print(printer)


def _esc(text: str) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
