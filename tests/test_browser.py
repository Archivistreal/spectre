import sys
import pytest
from PyQt6.QtWidgets import QApplication
from browser.ui import render_spectre_markup_to_html, SpectreBrowserWindow

# Initialize QApplication instance for GUI unit testing in headless environment
app = QApplication.instance() or QApplication(sys.argv)


def test_spectre_markup_renderer():
    markup = """# Title Header
## Subtitle Header
> Quote line

**Bold Text** and [Link Label](genesis.spectre)

- Item 1
- Item 2

```spectre
Code block inside
```
"""
    html = render_spectre_markup_to_html(markup)
    assert "<h1" in html and "Title Header" in html
    assert "<h2" in html and "Subtitle Header" in html
    assert "<blockquote" in html and "Quote line" in html
    assert "<b>Bold Text</b>" in html
    assert '<a href="genesis.spectre"' in html
    assert "Link Label" in html
    assert "<li" in html and "Item 1" in html
    assert "<pre" in html and "Code block inside" in html


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

    # Navigate to page 1
    window.address_bar.setText("page1.spectre")
    window.load_current_url()

    assert window.history == ["page1.spectre"]
    assert window.history_index == 0

    # Navigate to page 2
    window.address_bar.setText("page2.spectre")
    window.load_current_url()

    assert window.history == ["page1.spectre", "page2.spectre"]
    assert window.history_index == 1

    # Test back button
    window.navigate_back()
    assert window.history_index == 0

    # Test forward button
    window.navigate_forward()
    assert window.history_index == 1
