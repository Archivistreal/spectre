import sys
import pytest
from PyQt6.QtWidgets import QApplication
from browser.ui import SpectreBrowserWindow

# Initialize QApplication instance for GUI unit testing in headless environment
app = QApplication.instance() or QApplication(sys.argv)


def test_browser_window_navigation_history():
    window = SpectreBrowserWindow()
    assert window.history == []
    assert window.history_index == -1

    # Override SpectreNetworkWorker to simulate instant load without real sockets in history unit test
    def mock_fetch_page(url, add_to_history=True):
        if add_to_history:
            if window.history_index < len(window.history) - 1:
                window.history = window.history[: window.history_index + 1]
            window.history.append(url)
            window.history_index = len(window.history) - 1
            window.update_nav_buttons()

    window._fetch_page = mock_fetch_page

    # Navigate to page 1 (spectre.spec)
    window.address_bar.setText("spectre.spec")
    window.load_current_url()

    assert window.history == ["spectre.spec"]
    assert window.history_index == 0

    # Navigate to page 2 (genesis.spec)
    window.address_bar.setText("genesis.spec")
    window.load_current_url()

    assert window.history == ["spectre.spec", "genesis.spec"]
    assert window.history_index == 1

    # Test back button
    window.navigate_back()
    assert window.history_index == 0

    # Test forward button
    window.navigate_forward()
    assert window.history_index == 1
