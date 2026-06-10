from PyQt6.QtCore import QThreadPool, QObject, pyqtSlot
from core.workers.port_check_worker import PortCheckWorker

class _ResultReceiver(QObject):
    """
    Мост между рабочими потоками и главным потоком.

    Создаётся в главном потоке. Когда воркер эмитирует сигнал result
    из своего потока, Qt видит, что слот receive() принадлежит объекту
    из другого потока, и автоматически использует QueuedConnection —
    receive() всегда выполняется в главном потоке через event loop.

    Это гарантирует:
      - отсутствие гонок на _pending_ports (серийный доступ)
      - отсутствие гонок на self._data (серийный доступ)
      - все вызовы tree.update_port_item() — только из главного потока
    """

    def __init__(self, callback):
        super().__init__()
        self._callback = callback

    @pyqtSlot(int, int, bool)
    def receive(self, server_id: int, port: int, ok: bool) -> None:
        self._callback(server_id, port, ok)

class PortCheckManager:
    def __init__(self, max_threads: int = 10):
        # Выделенный пул — не трогаем globalInstance(), чтобы не влиять
        # на остальные части приложения
        self.pool = QThreadPool()
        self.pool.setMaxThreadCount(max_threads)
        # Храним ссылку, чтобы receiver не уничтожил GC раньше времени.
        # Пока живы соединения task.signals → receiver, PyQt6 держит ссылку
        # сам; self._receiver нужен как страховка.
        self._receiver: _ResultReceiver | None = None

    def check_ports(self, servers, on_result, api) -> None:
        # Создаём receiver здесь — в главном потоке.
        # Предыдущий receiver уничтожается только после того, как Qt
        # обработает все уже стоящие в очереди события для него.
        self._receiver = _ResultReceiver(on_result)

        for server in servers:
            sid = server["id"]
            ip = server["ip"]

            for p in server["ports"]:
                task = PortCheckWorker(sid, ip, p["port"], api)
                task.signals.result.connect(self._receiver.receive)
                self.pool.start(task)
