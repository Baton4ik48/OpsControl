from PyQt6.QtCore import QThreadPool
from controllers.port_check_task import PortCheckTask


class PortCheckManager:
    def __init__(self, max_threads=5):
        self.pool = QThreadPool.globalInstance()
        self.pool.setMaxThreadCount(max_threads)

    def check_ports(self, servers, on_result, api):
        for server in servers:
            sid = server["id"]
            ip = server["ip"]

            for p in server["ports"]:
                task = PortCheckTask(sid, ip, p["port"], api)
                task.signals.result.connect(on_result)
                self.pool.start(task)
