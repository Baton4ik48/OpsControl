import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QLabel,
    QAbstractItemView, QPushButton, QFileDialog, QMessageBox
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import os
from openpyxl import load_workbook
from functional.database import load_branches, load_servers, load_ports, update_server_name, update_server_ip, update_port_status

from functional.port_checker import check_port, get_label, pluralize_days
from gui.table_menu import TableContextMenu
from gui.console_widget import ConsoleWidget
from functional.auto_refresh_panel import AutoRefreshPanel
from functional.console_commands import ConsoleCommands

class DeviceCheckThread(QThread):
    result_signal = pyqtSignal(object, dict)

    def __init__(self, device_item, ip, ports):
        super().__init__()
        self.device_item = device_item
        self.ip = ip
        self.ports = ports

    def run(self):
        results = {}
        for port_info in self.ports:
            port = port_info["port"]
            ok = check_port(self.ip, port)
            results[port] = ok

        self.result_signal.emit(self.device_item, results)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("PortPass Manager")
        self.resize(1000, 600)

        layout = QVBoxLayout(self)

        # панель автообновления
        self.auto_refresh = AutoRefreshPanel(self)
        layout.addWidget(self.auto_refresh)

        # таблица
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Устройство", "IP", "Порты"])
        self.tree.setColumnWidth(0, 500)
        self.tree.setColumnWidth(1, 100)
        self.tree.setColumnWidth(2, 200)
        self.tree.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        self.tree.itemChanged.connect(self.on_item_changed_safe)


        # контекстное меню
        self.context_menu = TableContextMenu(self)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.open_context_menu)

        layout.addWidget(self.tree)

        # консоль
        self.console = ConsoleWidget(self.process_console_command)
        self.console.setMaximumHeight(200)
        layout.addWidget(self.console)

        self.cmd = ConsoleCommands(self.console_output)

        # статус
        self.status_label = QLabel("Готово.")
        layout.addWidget(self.status_label)

        self.threads = []
        self.load_devices_from_db()


    # ======================================================
    #                     КОНСОЛЬ
    # ======================================================

    def console_output(self, text):
        self.console.add_log(text)

    def process_console_command(self, cmd: str):
        self.cmd.handle(cmd)

    # ======================================================
    #               КОНТЕКСТНОЕ МЕНЮ
    # ======================================================

    def open_context_menu(self, position):
        item = self.tree.itemAt(position)
        if item is None:
            return
        menu = self.context_menu.create_menu(item)
        menu.exec(self.tree.viewport().mapToGlobal(position))

    # ======================================================
    #                ЗАГРУЗКА С БД
    # ======================================================


    def load_devices_from_db(self):
        self.tree.clear()

        # 1. Загружаем филиалы
        for branch_id, branch_name in load_branches():
            branch_item = QTreeWidgetItem([branch_name, "", ""])
            branch_item.row_data = {"type": "branch", "id": branch_id, "name": branch_name}
            self.tree.addTopLevelItem(branch_item)

            # 2. Загружаем устройства
            for server_id, name, ip in load_servers(branch_id):
                ports = load_ports(server_id)

                item = QTreeWidgetItem([name, ip, "нет данных"])
                item.ports = ports
                item.row_data = {
                    "type": "server",
                    "id": server_id,
                    "name": name,
                    "ip": ip,
                    "ports": ports
                }

                for col in (0, 1):
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)

                branch_item.addChild(item)

    # ======================================================
    #                ОБНОВЛЕНИЕ БД
    # ======================================================

    def on_item_changed(self, item, column):
        if not hasattr(item, "row_data"):
            return
        if item.row_data["type"] != "server":
            return

        server_id = item.row_data["id"]

        if column == 0:
            new_name = item.text(0)
            item.row_data["name"] = new_name
            update_server_name(server_id, new_name)

        elif column == 1:
            new_ip = item.text(1)
            item.row_data["ip"] = new_ip
            update_server_ip(server_id, new_ip)


    # ======================================================
    #                     ПРОВЕРКА ПОРТОВ
    # ======================================================

    def update_branch(self, branch_item):
        for i in range(branch_item.childCount()):
            self.update_device(branch_item.child(i))

    def update_device(self, device_item):
        ip = device_item.text(1)
        ports = device_item.ports
        thread = DeviceCheckThread(device_item, ip, ports)
        thread.result_signal.connect(self.apply_result)
        self.threads.append(thread)
        thread.start()

    def apply_result(self, item, results):
        ip = item.text(1)

        server_id = item.row_data["id"]
        now = datetime.datetime.now()

        # ======== ОБНОВЛЯЕМ БД ========
        for port, ok in results.items():
            if not ok:
                self.log(f"[ERROR] {ip}: порт {port} недоступен")

            update_port_status(server_id, port, ok)

        # ======== ОБНОВЛЯЕМ ТЕКСТ В ТАБЛИЦЕ ========
        parts = [
            f"{port} ({get_label(port)}): {'🟢' if ok else '🔴'}"
            for port, ok in results.items()
        ]
        item.setText(2, "    ".join(parts))

        # ======== СТАТУС ========
        if all(not t.isRunning() for t in self.threads):
            self.status_label.setText("Готово.")

        tooltip_lines = []

        # ======== ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ========
        def normalize_dt(value):
            if isinstance(value, datetime.datetime):
                return value
            if isinstance(value, str):
                return datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            return None

        # ======== ОБРАБОТКА ПОРТОВ ========
        for port_info in item.row_data["ports"]:
            port = port_info["port"]
            ok = results.get(port, False)

            prev_state = port_info.get("state")

            # нормализуем даты
            last_success_dt = normalize_dt(port_info.get("last_success"))
            last_failure_dt = normalize_dt(port_info.get("last_failure"))

            # ======== ОБНОВЛЯЕМ СОСТОЯНИЕ ========
            if ok:
                if prev_state != "up":
                    last_success_dt = now
                    port_info["last_success"] = now
                port_info["state"] = "up"
            else:
                if prev_state != "down":
                    last_failure_dt = now
                    port_info["last_failure"] = now
                port_info["state"] = "down"

            # ======== TOOLTIP ========
            label = get_label(port)
            symbol = "🟢" if ok else "🔴"

            if ok:
                text = (
                    f"{symbol} {port} ({label})\n"
                    f"  Доступен\n"
                )
            else:
                if last_success_dt:
                    days = (now - last_success_dt).days
                    days_text = pluralize_days(days)

                    text = (
                        f"{symbol} {port} ({label})\n"
                        f"  Недоступен\n"
                        f"  Был доступен: {days_text} назад\n"
                    )
                else:
                    text = (
                        f"{symbol} {port} ({label})\n"
                        f"  Недоступен\n"
                        f"  Был доступен: нет данных\n"
                    )

            tooltip_lines.append(text)

        item.setToolTip(2, "\n".join(tooltip_lines))

    def log(self, text):
        self.console.add_log(text)



    def on_item_changed_safe(self, item, column):
        # Игнорируем колонку "Порты" — она должна обновляться автоматически
        if column == 2:
            return

        self.on_item_changed(item, column)


    def update_all_servers(self):
        """
        Вызывается автообновлением: обновляет ВСЕ сервера во всех филиалах.
        """
        for i in range(self.tree.topLevelItemCount()):
            branch = self.tree.topLevelItem(i)
            self.update_branch(branch)
