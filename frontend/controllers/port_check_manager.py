from PyQt6.QtCore import QThreadPool
from controllers.workers import PortCheckTask


class PortCheckManager:
    def __init__(self, max_threads=10):
        self.pool = QThreadPool.globalInstance()
        self.pool.setMaxThreadCount(max_threads)

    def check_ports(self, servers, on_result):
        for server in servers:
            sid = server["id"]
            ip = server["ip"]

            for p in server["ports"]:
                task = PortCheckTask(sid, ip, p["port"])
                task.signals.result.connect(on_result)
                self.pool.start(task)
