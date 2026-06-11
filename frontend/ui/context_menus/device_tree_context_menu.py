from PyQt6.QtWidgets import QMenu

class DeviceTreeContextMenu:
    def __init__(self, tree):
        self.tree = tree

    def open(self, pos):
        item = self.tree.itemAt(pos)
        menu = QMenu(self.tree)

        if not item:
            expand_all = menu.addAction("Развернуть всё")
            collapse_all = menu.addAction("Свернуть всё")
            expand_all.triggered.connect(self.tree.expandAll)
            collapse_all.triggered.connect(self.tree.collapseAll)
            menu.exec(self.tree.viewport().mapToGlobal(pos))
            return

        item_type = item.data(0, self.tree.ROLE_TYPE)

        if item_type is None:
            branch_name = item.text(0)
            refresh_branch = menu.addAction(self.tree.icon_update, "Опросить филиал")
            refresh_branch.triggered.connect(
                lambda: self.tree.refresh_branch_requested.emit(branch_name)
            )
            menu.addSeparator()
            menu.addSeparator()
            expand_all = menu.addAction("Развернуть всё")
            collapse_all = menu.addAction("Свернуть всё")
            expand_all.triggered.connect(self.tree.expandAll)
            collapse_all.triggered.connect(self.tree.collapseAll)
            menu.exec(self.tree.viewport().mapToGlobal(pos))
            return

        if item_type not in ("server", "port"):
            return

        server_id = item.data(0, self.tree.ROLE_SERVER_ID)
        ip = item.data(0, self.tree.ROLE_IP)

        if item_type == "server":
            device_type = item.data(0, self.tree.ROLE_DEVICE_TYPE) or "linux"

            for i in range(item.childCount()):
                child = item.child(i)
                port = child.data(0, self.tree.ROLE_PORT)

                if not port:
                    continue

                self._add_connect_action(menu, server_id, ip, port, device_type)

            menu.addSeparator()

            refresh_action = menu.addAction(self.tree.icon_update, "Обновить сервер")
            refresh_action.triggered.connect(
                lambda: self.tree.refresh_server_requested.emit(server_id, ip)
            )

        elif item_type == "port":
            port = item.data(0, self.tree.ROLE_PORT)
            # device_type хранится на родительском узле сервера, не на порту
            device_type = item.parent().data(0, self.tree.ROLE_DEVICE_TYPE) or "linux"

            self._add_connect_action(menu, server_id, ip, port, device_type)

            show_action = menu.addAction(self.tree.icon_show, "Показать учётные данные")
            show_action.triggered.connect(
                lambda checked=False, p=port: self.tree.show_credentials_requested.emit(
                    server_id, p, ip
                )
            )

            if port == 22 and device_type not in ("windows", "xclarity"):
                rotate_action = menu.addAction(self.tree.icon_key, "Сменить пароль")
                rotate_action.triggered.connect(
                    lambda checked=False, dt=device_type: self.tree.rotate_password_requested.emit(
                        server_id, ip, dt
                    )
                )

            menu.addSeparator()

            refresh_action = menu.addAction(self.tree.icon_update, "Обновить порт")
            refresh_action.triggered.connect(
                lambda: self.tree.refresh_port_requested.emit(server_id, port, ip)
            )

        menu.exec(self.tree.viewport().mapToGlobal(pos))

    def _expand_branch(self, branch_item):
        # Разворачивает филиал и все серверы внутри него.
        branch_item.setExpanded(True)
        for i in range(branch_item.childCount()):
            branch_item.child(i).setExpanded(True)

    def _add_connect_action(self, menu, server_id, ip, port, device_type="linux"):

        icon = None
        text = None

        # SSH (не показываем для xClarity — у них 22 не используется)
        if port == 22 and device_type != "xclarity":
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
            lambda checked=False, p=port: self.tree.open_protocol_requested.emit(
                server_id, p, ip, ""
            )
        )
