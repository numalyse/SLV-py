from PySide6.QtWidgets import QWidget, QMessageBox, QLabel, QPushButton
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
import os
import platform
import subprocess
from pathlib import Path

class MessagePopUp(QWidget):  
    def __init__(self, parent, msg1=True,titre="Succès",txt="L'action a été effectuée avec succès !",type="info",time=2000, capture_button=False):
        super().__init__(parent)
        
        self.affichage = QLabel("Appuyez sur Échap pour quitter le plein écran", parent)
        self.affichage.setFixedSize(600, 80)  # Taille plus petite et fixe
        self.affichage.move(
            (parent.width() - self.affichage.width()) // 2, 
            (parent.height() - self.affichage.height()) // 2
        )  # Centre le label dans la fenêtre
        
        self.affichage.setAlignment(Qt.AlignCenter) 
        self.affichage.setStyleSheet("""
            color: white; 
            background-color: rgba(0, 0, 0, 150);  /* Fond semi-transparent réduit */
            font-size: 24px;  
            padding: 10px;
            border-radius: 10px;
        """)
        self.affichage.setFont(QFont("Arial", 20, QFont.Bold)) 
        self.affichage.hide()

        self.parent = parent

        if msg1:
            self.show_message(titre,txt,type,time, capture_button=capture_button)
        else:
            self.show_message_2()

    def show_message(self, title, message, message_type="info", timeout=2000, capture_button=False):
        self.msg_box = QMessageBox(self.parent)  

        if message_type == "info":
            self.msg_box.setIcon(QMessageBox.Information)
        elif message_type == "warning":
            self.msg_box.setIcon(QMessageBox.Warning)
        elif message_type == "error":
            self.msg_box.setIcon(QMessageBox.Critical)
        else:
            self.msg_box.setIcon(QMessageBox.NoIcon)

        self.msg_box.setWindowTitle(title)
        self.msg_box.setText(message)
        
        if(capture_button):
            capture_button = self.msg_box.addButton("Ouvrir", QMessageBox.ActionRole)
            capture_button.clicked.connect(self.open_capture_folder)
        
        self.msg_box.addButton("OK", QMessageBox.ActionRole)

        if(timeout>0):
            QTimer.singleShot(timeout, self.msg_box.accept)
        self.msg_box.show()

    def open_capture_folder(self):
        capture_dir = os.path.join(str(Path.home()), "SLV_Content", "Captures_Vidéos")
        if platform.system() == "Windows":
            os.startfile(capture_dir)
        elif platform.system() == "Darwin": 
            subprocess.run(["open", capture_dir])
        else:
            subprocess.run(["xdg-open", capture_dir])


    def hide_message(self):
        self.msg_box.hide()

    def show_message_2(self, timeout=1000):
        """ Affiche le message en transparence pendant `timeout` ms """
        self.affichage.show()
        QTimer.singleShot(timeout, self.affichage.hide)  # Cache le message après le timeout
    
    def hide_message_2(self):
        self.affichage.hide()