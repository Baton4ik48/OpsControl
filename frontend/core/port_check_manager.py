from PyQt6.QtCore import QThreadPool
from core.workers.port_check_worker import PortCheckWorker


class PortCheckManager:
    def __init__(self, max_threads=5):
        self.pool = QThreadPool.globalInstance()
        self.pool.setMaxThreadCount(max_threads)

    def check_ports(self, servers, on_result, api):
        for server in servers:
            sid = server["id"]
            ip = server["ip"]

            for p in server["ports"]:
                task = PortCheckWorker(sid, ip, p["port"], api)
                task.signals.result.connect(on_result)
                self.pool.start(task)
