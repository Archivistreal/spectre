import sys
import re
import asyncio
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
from core.node import SpectreClientCircuit


def render_spectre_markup_to_html(markup_text: str) -> str:
    """
    Parses .spectre markup format and converts it to HTML for QTextBrowser.
    Supported elements:
    - Headers: `# Header 1`, `## Header 2`, `### Header 3`
    - Bold text: `**text**`
    - Blockquotes: `> quote`
    - Links: `[label](target.spectre)` -> `<a href="target.spectre">label</a>`
    - Code blocks: ```spectre ... ```
    - Lists: `- item` or `1. item`
    """
    lines = markup_text.splitlines()
    html_lines = []
    in_code_block = False
    code_block_lines = []

    for line in lines:
        if line.strip().startswith("```"):
            if in_code_block:
                # Close code block
                code_content = "\n".join(code_block_lines)
                html_lines.append(
                    f'<pre style="background-color: #1e1e2e; color: #a6e3a1; padding: 10px; border-radius: 6px; font-family: monospace;">{code_content}</pre>'
                )
                code_block_lines = []
                in_code_block = False
            else:
                in_code_block = True
            continue

        if in_code_block:
            code_block_lines.append(line)
            continue

        # Parse headers
        if line.startswith("# "):
            html_lines.append(f'<h1 style="color: #89b4fa; border-bottom: 2px solid #89b4fa;">{line[2:]}</h1>')
            continue
        elif line.startswith("## "):
            html_lines.append(f'<h2 style="color: #f9e2af; border-bottom: 1px solid #45475a;">{line[3:]}</h2>')
            continue
        elif line.startswith("### "):
            html_lines.append(f'<h3 style="color: #cba6f7;">{line[4:]}</h3>')
            continue

        # Parse Blockquotes
        if line.startswith("> "):
            quote_text = line[2:]
            html_lines.append(
                f'<blockquote style="border-left: 4px solid #f5e0dc; margin-left: 0; padding-left: 10px; color: #bac2de; font-style: italic;">{quote_text}</blockquote>'
            )
            continue

        # Process inline markdown (bold & links)
        # Bold: **bold**
        formatted_line = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", line)
        # Links: [label](target)
        formatted_line = re.sub(r"\[(.*?)\]\((.*?)\)", r'<a href="\2" style="color: #89b4fa; font-weight: bold;">\1</a>', formatted_line)

        # Unordered / Ordered list items
        if formatted_line.strip().startswith("- "):
            html_lines.append(f'<li style="color: #cdd6f4;">{formatted_line.strip()[2:]}</li>')
            continue
        elif re.match(r"^\d+\.\s", formatted_line.strip()):
            item_text = re.sub(r"^\d+\.\s", "", formatted_line.strip())
            html_lines.append(f'<li style="color: #cdd6f4;">{item_text}</li>')
            continue

        if formatted_line.strip():
            html_lines.append(f'<p style="color: #cdd6f4; font-size: 14px; line-height: 1.5;">{formatted_line}</p>')
        else:
            html_lines.append("<br>")

    body_html = "\n".join(html_lines)
    full_html = f"""
    <html>
    <head>
        <style>
            body {{
                background-color: #181825;
                color: #cdd6f4;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                padding: 15px;
            }}
            a {{
                color: #89b4fa;
                text-decoration: none;
            }}
            a:hover {{
                text-decoration: underline;
            }}
        </style>
    </head>
    <body>
        {body_html}
    </body>
    </html>
    """
    return full_html


class SpectreNetworkWorker(QThread):
    """Worker thread running asyncio loop for circuit building & page requests."""
    page_loaded = pyqtSignal(str, str)  # (url, content)
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
            self.status_updated.emit("Establishing 3-Hop Onion Circuit (Guard -> Relay -> Exit)...")
            circuit = SpectreClientCircuit(self.guard_addr, self.relay_addr, self.exit_addr)
            await circuit.build_circuit()

            self.status_updated.emit(f"Circuit active. Requesting {self.target_url} via Exit node...")
            srv_host, srv_port = self.server_addr
            response = await circuit.send_request(srv_host, srv_port, f"GET {self.target_url}")

            await circuit.close()

            # Separate HTTP-like headers and body
            if "\r\n\r\n" in response:
                _, body = response.split("\r\n\r\n", 1)
            else:
                body = response

            self.status_updated.emit(f"Successfully retrieved {self.target_url} over Spectre Onion Network.")
            self.page_loaded.emit(self.target_url, body)

        except Exception as e:
            self.error_occurred.emit(f"Network error: {str(e)}")


class SpectreBrowserWindow(QMainWindow):
    """PyQt6 Desktop GUI Client for Spectre Onion Protocol."""

    def __init__(
        self,
        guard_addr: Tuple[str, int] = ("127.0.0.1", 19001),
        relay_addr: Tuple[str, int] = ("127.0.0.1", 19002),
        exit_addr: Tuple[str, int] = ("127.0.0.1", 19003),
        server_addr: Tuple[str, int] = ("127.0.0.1", 19080),
    ):
        super().__init__()
        self.guard_addr = guard_addr
        self.relay_addr = relay_addr
        self.exit_addr = exit_addr
        self.server_addr = server_addr

        self.history: List[str] = []
        self.history_index: int = -1

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Spectre Protocol Onion Browser")
        self.resize(900, 650)
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
        self.address_bar.setPlaceholderText("Enter .spectre address (e.g. genesis.spectre)")
        self.address_bar.setText("genesis.spectre")
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
        self.status_label = QLabel("Spectre Network Ready (3-Hop Circuit Ready)")
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
            # Truncate forward history if navigating to a new URL
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

    def on_page_loaded(self, url: str, raw_markup: str):
        self.go_btn.setEnabled(True)
        self.address_bar.setEnabled(True)
        self.address_bar.setText(url)

        html = render_spectre_markup_to_html(raw_markup)
        self.content_viewer.setHtml(html)

    def on_status_updated(self, msg: str):
        self.status_label.setText(f"[SPECTRE] {msg}")

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
