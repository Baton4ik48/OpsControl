from PyQt6.QtWidgets import QMenu


class DeviceTreeContextMenu:
    def __init__(self, tree):
        self.tree = tree

    def open(self, pos):
        item = self.tree.itemAt(pos)
        if not item:
            return

        item_type = item.data(0, self.tree.ROLE_TYPE)

        if item_type not in ("server", "port"):
            return

        server_id = item.data(0, self.tree.ROLE_SERVER_ID)
        ip = item.data(0, self.tree.ROLE_IP)

        menu = QMenu(self.tree)

        # =========================
        # SERVER
        # =========================
        if item_type == "server":

            for i in range(item.childCount()):
                child = item.child(i)
                port = child.data(0, self.tree.ROLE_PORT)

                if not port:
                    continue

                self._add_connect_action(menu, server_id, ip, port)

            menu.addSeparator()

            refresh_action = menu.addAction(
                self.tree.icon_update,
                "Обновить сервер"
            )
            refresh_action.triggered.connect(
                lambda: self.tree.refresh_server_requested.emit(server_id, ip)
            )

        # =========================
        # PORT
        # =========================
        elif item_type == "port":

            port = item.data(0, self.tree.ROLE_PORT)

            self._add_connect_action(menu, server_id, ip, port)

            show_action = menu.addAction(
                self.tree.icon_show,
                "Показать учётные данные"
            )
            show_action.triggered.connect(
                lambda checked=False, p=port:
                    self.tree.show_credentials_requested.emit(server_id, p, ip)
            )

            menu.addSeparator()

            refresh_action = menu.addAction(
                self.tree.icon_update,
                "Обновить порт"
            )
            refresh_action.triggered.connect(
                lambda: self.tree.refresh_port_requested.emit(server_id, port, ip)
            )

        menu.exec(self.tree.viewport().mapToGlobal(pos))

    # ==================================================
    # CONNECT ACTIONS
    # ==================================================

    def _add_connect_action(self, menu, server_id, ip, port):

        icon = None
        text = None

        # SSH
        if port == 22:
            icon = self.tree.icon_ssh
            text = "Подключиться по SSH"

        # RDP
        elif port == 3389:
            icon = self.tree.icon_rdp
            text = "Подключиться по RDP"

        else:
            external_apps = []
            web_ports = []

            if hasattr(self.tree, "user_settings") and self.tree.user_settings:
                external_apps = self.tree.user_settings.get("external_apps") or []
                web_ports = self.tree.user_settings.get("web_ports") or []

            # EXTERNAL
            for app in external_apps:
                if app.get("port") == port:
                    icon = self.tree.icon_external
                    text = f"Открыть {app.get('name')}"
                    break

            # WEB
            if not text:
                for entry in web_ports:
                    if entry.get("port") == port:
                        icon = self.tree.icon_web
                        scheme = entry.get("scheme")
                        text = f"Открыть Web ({scheme.upper()})"
                        break

        if not text:
            return

        action = menu.addAction(icon, text)
        action.triggered.connect(
            lambda checked=False, p=port:
                self.tree.open_protocol_requested.emit(server_id, p, ip, "")
        )