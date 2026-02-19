import sys

import traceback
import os
from pathlib import Path
import datetime
import logging

if sys.platform == "darwin":  # "darwin" = macOS
    os.environ["PATH"] += os.pathsep + "/opt/homebrew/bin"
    os.environ["PATH"] += os.pathsep + "usr/local/bin"

    os.listdir(os.path.expanduser("~/Documents"))  # ➜ demande d’accès à Documents
    os.listdir(os.path.expanduser("~/Desktop"))    # ➜ demande d’accès à Bureau
    os.listdir(os.path.expanduser("~/Movies"))     # ➜ demande d’accès à Vidéos
    os.listdir(os.path.expanduser("~/Music"))      # ➜ demande d’accès à Musique

# Dossier log
log_dir = Path.home() / "SLV_Content" / "Logs"
log_dir.mkdir(parents=True, exist_ok=True)

timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
log_file = log_dir / f"slv_{timestamp}.log"

# Config logger
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)  # utile si lancé via terminal
    ]
)

# Capturer toutes les exceptions non gérées et les écrire dans le log
def excepthook(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        # Laisser l'interruption clavier normale
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.error("Exception non gérée !", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = excepthook

logging.info("=== Application démarrée ===")

# Rediriger print() vers logging.info
print = logging.info

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon, QPalette
from PySide6.QtCore import Qt
from main_window import VLCMainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)

    app.setApplicationName("SLV")
    app.setWindowIcon(QIcon("icon/numalyse_logo.ico"))

    # app.setStyle("Fusion")

    # palette = QPalette()
    # palette.setColor(QPalette.Window, Qt.black)
    # palette.setColor(QPalette.WindowText, Qt.white)
    # palette.setColor(QPalette.Base, Qt.black)
    # palette.setColor(QPalette.AlternateBase, Qt.gray)
    # palette.setColor(QPalette.ToolTipBase, Qt.black)
    # palette.setColor(QPalette.ToolTipText, Qt.white)
    # palette.setColor(QPalette.Text, Qt.white)
    # palette.setColor(QPalette.Button, Qt.darkGray)
    # palette.setColor(QPalette.ButtonText, Qt.white)
    # palette.setColor(QPalette.BrightText, Qt.red)
    # palette.setColor(QPalette.Highlight, Qt.blue)
    # palette.setColor(QPalette.HighlightedText, Qt.black)

    # app.setPalette(palette)

    window = VLCMainWindow()
    window.show()
    sys.exit(app.exec())



# pyinstaller --name "SLV" --windowed --icon=icon/icon3.ico --exclude PyQt5 --exclude PyQt6 --onefile \
# --add-binary "/usr/lib/x86_64-linux-gnu/libvlc.so:." \
# --add-binary "/usr/lib/x86_64-linux-gnu/libvlccore.so.9:." main.py


#pyinstaller -w --add-binary "C:\Program Files\VideoLAN\VLC\libvlc.dll;." main.py

#penser à intégrer le plugin vlc dans le dossier
#--add-binary "C:\\Program Files\\VideoLAN\\VLC\\libvlccore.dll;." à tester avec
#-w pour normalement enlever le terminal

#windows slv_installeur inno_setup
#pyinstaller --name "SLV" --icon=icon/icon3.ico -w --add-data "icon;icon" --add-binary "C:\ffmpeg\bin\ffmpeg.exe;." --add-binary "C:\Program Files\VideoLAN\VLC\libvlc.dll;." main.py
#--add-binary "C:\ffmpeg\bin\ffmpeg.exe;."
#--add-binary "C:\Users\33652\AppData\Local\Programs\Python\Python310\python310.dll;."


#linux ne fonctionne pas
#pyinstaller --name "SLV" --icon=icon/icon3.ico -w --exclude PyQt5 --exclude PyQt6 --add-binary "/usr/lib/x86_64-linux-gnu/libvlc.so:." main.py

