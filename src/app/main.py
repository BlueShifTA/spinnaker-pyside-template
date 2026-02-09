"""Main application entry point."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


def main() -> int:
    """Run the application."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Set dark theme
    app.setStyleSheet("""
        QMainWindow, QWidget {
            background-color: #0a0a0a;
            color: #e0e0e0;
        }
        QGroupBox {
            border: 1px solid #333;
            border-radius: 4px;
            margin-top: 12px;
            padding-top: 8px;
            font-weight: bold;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
        }
        QPushButton {
            background-color: #2a2a2a;
            border: 1px solid #444;
            border-radius: 4px;
            padding: 6px 12px;
            min-width: 60px;
        }
        QPushButton:hover {
            background-color: #3a3a3a;
        }
        QPushButton:pressed {
            background-color: #1a1a1a;
        }
        QPushButton:disabled {
            background-color: #1a1a1a;
            color: #666;
        }
        QSpinBox, QDoubleSpinBox {
            background-color: #1a1a1a;
            border: 1px solid #333;
            border-radius: 4px;
            padding: 4px;
        }
        QSpinBox:focus, QDoubleSpinBox:focus {
            border-color: #3b82f6;
        }
    """)

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
