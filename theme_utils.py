
def apply_dark_mode(window, enabled: bool) -> None:
    """
    Applique ou retire un style sombre sur la fenêtre.
    - enabled=True => applique un style "sombre".
    - enabled=False => retire le style (style par défaut).
    """
    if not enabled:
        window.setStyleSheet("")
        return
    dark_style = """
        * {
            background-color: #000000;
            color: #ffffff;
        }
        QPushButton {
            background-color: transparent;
        }
        QSlider::groove:horizontal {
            background: #444;
        }
        QSlider::handle:horizontal {
            background: #888;
        }
    """
    window.setStyleSheet(dark_style)