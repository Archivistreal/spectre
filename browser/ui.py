import sys
import asyncio
import threading
import logging
from typing import Optional, List, Tuple
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTextBrowser,
    QStatusBar,
    QLabel,
    QMessageBox,
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from core.node import SpectreNode, SpectreClientCircuit

logger = logging.getLogger("spectre.browser")


class SpectreNetworkWorker(QThread):
    """Worker thread running asyncio loop for circuit building & HTML page requests."""
    page_loaded = pyqtSignal(str, str)  # (url, html_content)
    status_updated = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, target_url: str, guard_addr: Tuple[str, int], relay_addr: Tuple[str, int], exit_addr: Tuple[str, int], server_addr: Tuple[str, int]):
        super().__init__()
        self.target_url = target_url
        self.guard_addr = guard_addr
        self.relay_addr = relay_addr
        self.exit_addr = exit_addr
        self.server_addr = server_addr

    def run(self):
        asyncio.run(self._execute_request())

    async def _execute_request(self):
        try:
            circuit = SpectreClientCircuit(self.guard_addr, self.relay_addr, self.exit_addr)
            try:
                self.status_updated.emit("Establishing 3-Hop Padded Circuit (Guard -> Relay -> Exit)...")
                await circuit.build_circuit()

                self.status_updated.emit(f"Circuit active. Fetching {self.target_url} via Exit node...")
                srv_host, srv_port = self.server_addr
                response = await circuit.send_request(srv_host, srv_port, f"GET {self.target_url}")

                if "\r\n\r\n" in response:
                    _, body = response.split("\r\n\r\n", 1)
                else:
                    body = response

                self.status_updated.emit(f"Successfully retrieved {self.target_url} over Spectre Onion Network.")
                self.page_loaded.emit(self.target_url, body)
            finally:
                await circuit.close()

        except ConnectionRefusedError:
            self.error_occurred.emit("Could not connect to Spectre Guard Node at 127.0.0.1:19001.\n\nPlease start the daemon network first by running:\npython main.py --demo")
        except Exception as e:
            self.error_occurred.emit(f"Network error: {str(e)}")


class SpectreBrowserWindow(QMainWindow):
    """PyQt6 Desktop HTML Browser with embedded P2P Relay Node participation."""

    def __init__(
        self,
        guard_addr: Tuple[str, int] = ("127.0.0.1", 19001),
        relay_addr: Tuple[str, int] = ("127.0.0.1", 19002),
        exit_addr: Tuple[str, int] = ("127.0.0.1", 19003),
        server_addr: Tuple[str, int] = ("127.0.0.1", 19080),
        node_port: int = 0,  # 0 picks available random port for embedded relay node
        enable_embedded_node: bool = True,
    ):
        super().__init__()
        self.guard_addr = guard_addr
        self.relay_addr = relay_addr
        self.exit_addr = exit_addr
        self.server_addr = server_addr
        self.node_port = node_port
        self.enable_embedded_node = enable_embedded_node

        self.history: List[str] = []
        self.history_index: int = -1

        self.embedded_node: Optional[SpectreNode] = None
        self.node_loop: Optional[asyncio.AbstractEventLoop] = None
        self.node_thread: Optional[threading.Thread] = None

        self.init_ui()

        if self.enable_embedded_node:
            self.start_embedded_node()

    def start_embedded_node(self):
        """Spins up background embedded Spectre Relay Node in a dedicated asyncio thread."""
        try:
            self.node_loop = asyncio.new_event_loop()

            async def _spin_up():
                self.embedded_node = SpectreNode("BrowserEmbeddedRelay", "127.0.0.1", self.node_port, role="relay")
                await self.embedded_node.start()

            self.node_loop.run_until_complete(_spin_up())

            def _node_worker(l):
                asyncio.set_event_loop(l)
                l.run_forever()

            self.node_thread = threading.Thread(target=_node_worker, args=(self.node_loop,), daemon=True)
            self.node_thread.start()

            bound_port = self.embedded_node.port if self.embedded_node else self.node_port
            self.status_label.setText(f"[SPECTRE P2P] Embedded Relay Node Active on tcp://127.0.0.1:{bound_port} | Contributing to Network")
        except Exception as e:
            logger.warning(f"Could not start embedded browser node: {e}")

    def closeEvent(self, event):
        """Gracefully stops embedded node on window close."""
        if self.embedded_node and self.node_loop:
            try:
                async def _shut():
                    await self.embedded_node.stop()

                asyncio.run_coroutine_threadsafe(_shut(), self.node_loop).result(timeout=2.0)
                self.node_loop.call_soon_threadsafe(self.node_loop.stop)
            except Exception as e:
                logger.warning(f"Error stopping embedded node: {e}")
        event.accept()

    def init_ui(self):
        self.setWindowTitle("Spectre Protocol Onion HTML Browser (P2P Node Active)")
        self.resize(950, 700)
        self.setStyleSheet("background-color: #11111b; color: #cdd6f4;")

        main_widget = QWidget()
        layout = QVBoxLayout()
        main_widget.setLayout(layout)
        self.setCentralWidget(main_widget)

        # Navigation Bar Layout
        nav_layout = QHBoxLayout()

        self.back_btn = QPushButton("◄ Back")
        self.back_btn.setStyleSheet("padding: 6px 12px; background-color: #313244; color: #cdd6f4; border-radius: 4px;")
        self.back_btn.setEnabled(False)
        self.back_btn.clicked.connect(self.navigate_back)
        nav_layout.addWidget(self.back_btn)

        self.forward_btn = QPushButton("Forward ►")
        self.forward_btn.setStyleSheet("padding: 6px 12px; background-color: #313244; color: #cdd6f4; border-radius: 4px;")
        self.forward_btn.setEnabled(False)
        self.forward_btn.clicked.connect(self.navigate_forward)
        nav_layout.addWidget(self.forward_btn)

        self.address_bar = QLineEdit()
        self.address_bar.setPlaceholderText("Enter .spec address (e.g. spectre.spec)")
        self.address_bar.setText("spectre.spec")
        self.address_bar.setStyleSheet("padding: 6px; background-color: #1e1e2e; color: #89b4fa; border: 1px solid #45475a; border-radius: 4px; font-weight: bold;")
        self.address_bar.returnPressed.connect(self.load_current_url)
        nav_layout.addWidget(self.address_bar)

        self.go_btn = QPushButton("Go")
        self.go_btn.setStyleSheet("padding: 6px 16px; background-color: #89b4fa; color: #11111b; font-weight: bold; border-radius: 4px;")
        self.go_btn.clicked.connect(self.load_current_url)
        nav_layout.addWidget(self.go_btn)

        layout.addLayout(nav_layout)

        # Content Rendering Area
        self.content_viewer = QTextBrowser()
        self.content_viewer.setOpenExternalLinks(False)
        self.content_viewer.anchorClicked.connect(self.on_anchor_clicked)
        self.content_viewer.setStyleSheet("background-color: #181825; border: 1px solid #313244; border-radius: 6px;")
        layout.addWidget(self.content_viewer)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("Spectre Network Ready (P2P Node Initializing...)")
        self.status_bar.addWidget(self.status_label)

    def load_current_url(self):
        url = self.address_bar.text().strip()
        if not url:
            return
        self._fetch_page(url, add_to_history=True)

    def _fetch_page(self, url: str, add_to_history: bool = True):
        self.go_btn.setEnabled(False)
        self.address_bar.setEnabled(False)

        if add_to_history:
            if self.history_index < len(self.history) - 1:
                self.history = self.history[: self.history_index + 1]
            self.history.append(url)
            self.history_index = len(self.history) - 1
            self.update_nav_buttons()

        self.worker = SpectreNetworkWorker(url, self.guard_addr, self.relay_addr, self.exit_addr, self.server_addr)
        self.worker.page_loaded.connect(self.on_page_loaded)
        self.worker.status_updated.connect(self.on_status_updated)
        self.worker.error_occurred.connect(self.on_error_occurred)
        self.worker.start()

    def on_page_loaded(self, url: str, html_content: str):
        self.go_btn.setEnabled(True)
        self.address_bar.setEnabled(True)
        self.address_bar.setText(url)

        self.content_viewer.setHtml(html_content)

    def on_status_updated(self, msg: str):
        node_info = f" | [P2P Relay Node Active: tcp://127.0.0.1:{self.embedded_node.port}]" if self.embedded_node else ""
        self.status_label.setText(f"[SPECTRE] {msg}{node_info}")

    def on_error_occurred(self, err_msg: str):
        self.go_btn.setEnabled(True)
        self.address_bar.setEnabled(True)
        self.status_label.setText(f"[ERROR] {err_msg}")
        QMessageBox.critical(self, "Spectre Network Error", err_msg)

    def on_anchor_clicked(self, qurl):
        target_url = qurl.toString()
        self.address_bar.setText(target_url)
        self._fetch_page(target_url, add_to_history=True)

    def navigate_back(self):
        if self.history_index > 0:
            self.history_index -= 1
            url = self.history[self.history_index]
            self.update_nav_buttons()
            self._fetch_page(url, add_to_history=False)

    def navigate_forward(self):
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            url = self.history[self.history_index]
            self.update_nav_buttons()
            self._fetch_page(url, add_to_history=False)

    def update_nav_buttons(self):
        self.back_btn.setEnabled(self.history_index > 0)
        self.forward_btn.setEnabled(self.history_index < len(self.history) - 1)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SpectreBrowserWindow()
    window.show()
    sys.exit(app.exec())
