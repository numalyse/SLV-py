from PySide6.QtWidgets import QWidget, QVBoxLayout, QMessageBox, QPushButton, QMenu, QInputDialog, QScrollArea, QDockWidget, QLabel, QDialog, QLineEdit, QSlider, QHBoxLayout, QSpinBox, QTextEdit, QFrame, QApplication, QSizePolicy, QFormLayout, QGridLayout
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt, QTimer, Signal, QEvent

import cv2 
import os
from datetime import datetime
from moviepy import VideoFileClip
from pathlib import Path

from segmentation import SegmentationThread
from time_selector import TimeSelector
from time_editor import TimeEditor
from time_manager import TimeManager
from message_popup import MessagePopUp
from no_focus_push_button import NoFocusPushButton
from frame_previewer import FramePreviewer
from export_manager import ExportManager

class MyTextEdit(QTextEdit):

    SignalFocusIn = Signal()
    SignalFocusOut = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.installEventFilter(self)

    def eventFilter(self, source, event):
        if event.type() == QEvent.FocusIn and source is self:
            self.SignalFocusIn.emit()
        if event.type() == QEvent.FocusOut and source is self:
            self.SignalFocusOut.emit()
        return super().eventFilter(source, event)
    
class MyLineEdit(QLineEdit):

    SignalFocusIn = Signal() 
    SignalFocusOut = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.installEventFilter(self)

    def eventFilter(self, source, event):
        if event.type() == QEvent.FocusIn and source is self:
            self.SignalFocusIn.emit()
        if event.type() == QEvent.FocusOut and source is self:
            self.SignalFocusOut.emit()
        return super().eventFilter(source, event)





class SideMenuWidgetDisplay(QDockWidget):
    change = Signal(bool)
    segmentation_done = Signal(bool)
    button_next_plan_clicked = Signal()
    button_prev_plan_clicked = Signal()


    def __init__(self, vlc_widget, parent=None):
        super().__init__("Segmentation", parent)  # Titre du dock
        self.vlc_widget = vlc_widget

        self.setFeatures(QDockWidget.NoDockWidgetFeatures)
        #self.setFeatures(QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetMovable) 

        self.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)  # Zones autorisées

        self.parent=parent
        # Définir la largeur du dock
        self.setFixedWidth(340)

        # Créer un widget de conteneur pour le contenu
        self.container = QWidget(self)

        # Créer une zone défilante pour les boutons
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.container)

        # Définir le widget pour le dock
        self.setWidget(self.scroll_area)

        # Layout vertical pour stocker les boutons
        self.layout = QVBoxLayout(self.container)
        self.container.setLayout(self.layout)

        # Liste pour stocker les boutons et leurs informations
        self.stock_button = []
        self.button_notes = {}

        self.id_affichage = -1

        self.fps=None

        self.max_time=self.vlc_widget.player.get_length()

        self.time_manager=TimeManager(fps=self.vlc_widget.fps)

    def select_plan(self,i):
        self.id_affichage=i
        self.reorganize_buttons()


    #fonction de tri appelée après ajout de bouton pour un affichage logique
    def reorganize_buttons(self):
        for i in reversed(range(self.layout.count())):
            item = self.layout.itemAt(i)
            if item is not None:
                widget = item.widget()
                if widget:
                    self.layout.removeWidget(widget)
                    widget.setParent(None)
                else: 
                    self.layout.removeItem(item)

        # Réinsère les frames triés
        for i,btn_data in enumerate(self.stock_button):
            if self.id_affichage==i:
                self.layout.addWidget(btn_data["frame"])
                btn_data["frame"].setVisible(True)
            else:
                btn_data["frame"].setVisible(False)

        # Réajoute un stretch à la fin
        self.layout.addStretch()

    def info_data_form(self, name="", text="", modifiable=True):
        background_frame = QFrame(self)
        background_frame.setAutoFillBackground(True)

        background_frame.setStyleSheet("border: none; background-color: palette(base); padding: 1px; border-radius: 5px;")
        background_layout= QFormLayout(background_frame)

        name_label = QLabel(name, background_frame)
        name_label.setAlignment(Qt.AlignLeft)
        name_label.setStyleSheet("font-weight: bold;")

        name_input = MyLineEdit(background_frame)
        name_input.setText(text)
        name_input.setReadOnly(not modifiable)
        name_input.setAlignment(Qt.AlignRight)
        
        if modifiable:
            name_input.SignalFocusIn.connect(lambda: self.vlc_widget.pause_video())
            name_input.SignalFocusOut.connect(lambda: self.vlc_widget.play_video())

        background_layout.addRow(name_label, name_input)

        return background_frame

    #fonction d'ajout d'une nouveaux bouton
    def add_new_button(self, btn,rect,color,name="", time=0, end=0, verif=True, frame1=-1, frame2=-1, notes=[]):
        if verif and time >= self.max_time:
            return

        # ===== INFOS PLAN sur le volet droit =====
        # Création du cadre du volet pour regrouper le bouton et ses éléments associés
        frame = QFrame(self)
        #frame.setStyleSheet("border: 1px solid gray; padding: 5px; border-radius: 5px;")
        frame.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        frame_layout = QVBoxLayout(frame)
        

        if name == "":
            cpt = len(self.stock_button)
            name = "Plan " + f"{cpt+1}"

        # Affichage numérotation des plans
        numbering_name = f"Plan n°{len(self.stock_button) + 1}"
        frame_name = QLabel(numbering_name, self)
        frame_name.setAlignment(Qt.AlignCenter)
        frame_name.setStyleSheet("border: none; background: transparent;")
        frame_name.adjustSize()

        # -------------- A ENLEVER

        # Bouton du nom du plan
        button = NoFocusPushButton(name, self)
        #button.setStyleSheet("background-color: #666; color: white; padding: 5px; border-radius: 5px;")
        #button.setContextMenuPolicy(Qt.CustomContextMenu)
        #button.customContextMenuRequested.connect(lambda pos, btn=button: self.show_context_menu(pos, btn))
        #button.clicked.connect(lambda _, btn=button: self.rename_button(btn))
        #button.setFocusPolicy(Qt.NoFocus)
        #button.setFixedSize(180, 25)

        # Création du label pour afficher le timecode
        if end == 0:
            time_label = QLabel(f"Début : " + self.time_manager.m_to_hmsf(time), self)
        else:
            duration = self.time_manager.m_to_hmsf(end - time)
            time_label = QLabel(f"Début : {self.time_manager.m_to_hmsf(time)} / Fin : {self.time_manager.m_to_hmsf(end)} \nDurée : {duration}", self)

        time_label.setFixedHeight(50)

        # -------------- FIN A ENLEVER

        frame_layout.addWidget(self.info_data_form(name="Numéro du plan", text=numbering_name, modifiable=False))
        frame_layout.addWidget(self.info_data_form(name="Nom du plan", text=name, modifiable=True))

        frame_layout.addWidget(self.info_data_form(name="Début du plan", text=self.time_manager.m_to_hmsf(time), modifiable=False))
        frame_layout.addWidget(self.info_data_form(name="Fin du plan", text=self.time_manager.m_to_hmsf(end), modifiable=False))
        frame_layout.addWidget(self.info_data_form(name="Durée du plan", text=self.time_manager.m_to_hmsf(end - time), modifiable=False))
        
        #frame_layout.addWidget(frame_name)
        #frame_layout.addWidget(button)
        #frame_layout.addWidget(time_label)

        #frame.setVisible(False)

        # Ajouter le frame à la liste des boutons stockés
        self.stock_button.append({"id":btn,"rect":rect,"color":color,"frame": frame, "button": button, "time": time, "end": end, "label": time_label, "frame1": frame1, "frame2":frame2})

        # Trier les boutons
        self.stock_button.sort(key=lambda btn_data: btn_data["time"])

        self.button_notes[button] = []  # Associer une liste vide de notes au bouton
        self.add_note(button, notes[0] if notes else "") 
        
        frame_buttons_actions = QFrame(self)
        frame_buttons_layout = QGridLayout(frame_buttons_actions)

        button_prev_plan = NoFocusPushButton("Plan précédent", self)
        button_prev_plan.setFocusPolicy(Qt.NoFocus)
        button_prev_plan.clicked.connect(self.button_prev_plan_clicked.emit)
        frame_buttons_layout.addWidget(button_prev_plan, 0, 0)

        button_next_plan = NoFocusPushButton("Plan suivant", self)
        button_next_plan.setFocusPolicy(Qt.NoFocus)
        button_next_plan.clicked.connect(self.button_next_plan_clicked.emit)
        frame_buttons_layout.addWidget(button_next_plan, 0, 1)

        button_extract_plan = NoFocusPushButton("Extraire le plan", self)
        button_extract_plan.clicked.connect(lambda _, btn=button: self.extract_confirm(btn))
        button_extract_plan.setFocusPolicy(Qt.NoFocus)
        frame_buttons_layout.addWidget(button_extract_plan, 1, 0)

        button_modify_timecode = NoFocusPushButton("Modifier Timecode", self)
        button_modify_timecode.clicked.connect(lambda _, btn=button: self.modify_time(btn))  
        button_modify_timecode.setFocusPolicy(Qt.NoFocus)  
        frame_buttons_layout.addWidget(button_modify_timecode, 1, 1)

        frame_layout.addWidget(frame_buttons_actions)

        # Réorganiser les boutons dans l'affichage
        self.reorganize_buttons()

        if verif:
            self.segmentation_done.emit(True)

        return button

    def get_button_data(self, button):
        for btn_data in self.stock_button:
            if btn_data["button"] == button:
                return btn_data["time"], btn_data["end"]
        return None, None

    #menu clique droit du bouton/séquence
    def show_context_menu(self, pos, button):
        """Affiche un menu contextuel avec options de renommer et modifier valeurs."""
        time, end = self.get_button_data(button)

        menu = QMenu(self)

        rename_action = QAction("Renommer", self)
        rename_action.triggered.connect(lambda: self.rename_button(button))
        menu.addAction(rename_action)

        mod_action = QAction("Modifier Timecode", self)
        mod_action.triggered.connect(lambda: self.modify_time(button))
        menu.addAction(mod_action)

        add_note_action = QAction("Ajouter une note")
        add_note_action.triggered.connect(lambda: self.add_note_menu(button))
        menu.addAction(add_note_action)

        extract_action = QAction("Extraire le plan")
        extract_action.triggered.connect(lambda: self.extract_confirm(button))
        menu.addAction(extract_action)

        # Vérifie si le plan n'est pas le premier dans la liste pour afficher l'option de concaténer avec le précédent
        if(not self.is_first_shot(button)):
            delete_action = QAction("Supprimer et concaténer avec le précedent", self)
            delete_action.triggered.connect(lambda: self.parent.delate_button_prec(button))
            menu.addAction(delete_action)

        # Vérifie si le plan n'est pas le dernier dans la liste pour afficher l'option de concaténer avec le suivant
        if (not self.is_last_shot(button)):
            delete_action2 = QAction("Supprimer et concaténer avec le suivant", self)
            delete_action2.triggered.connect(lambda: self.parent.delate_button_suiv(button))
            menu.addAction(delete_action2)

        menu.exec_(button.mapToGlobal(pos))

    # Retoune True si le bouton correspond à la dernière séquence, sinon False
    def is_last_shot(self, button):
        return button == self.stock_button[-1]["button"] if self.stock_button else False
    
    def is_first_shot(self, button):
        return button == self.stock_button[0]["button"] if self.stock_button else False

    #fonction 1
    def rename_button(self, button):
        """Ouvre une boîte de dialogue pour renommer le bouton."""
        new_name, ok = QInputDialog.getText(self, "Renommer le bouton", "Nouveau nom :", text=button.text())
        if ok and new_name.strip():
            button.setText(new_name)
            # Mettre à jour dans stock_button
            for btn_data in self.stock_button:
                if btn_data["button"] == button:
                    btn_data["button"].setText(new_name)
        self.parent.emit_change()

    def rename_button2(self, button):
        line_edit = QLineEdit(button.text(), self)
        line_edit.setGeometry(button.geometry())
        line_edit.setFocus()
        line_edit.selectAll()
        line_edit.show()

        button.hide()

        def finish_edit():
            new_name = line_edit.text().strip()
            if new_name:
                button.setText(new_name)

                for btn_data in self.stock_button:
                    if btn_data["button"] == button:
                        btn_data["button"].setText(new_name)

            line_edit.deleteLater()
            button.show()
            self.parent.emit_change()

        line_edit.editingFinished.connect(finish_edit)

    #fonction 3
    def add_note_menu(self, button):
        self.add_note(button, "")  # Ajoute une note vide directement
        self.parent.emit_change()

    def add_note(self, button, text=""):
        note_widget = MyTextEdit(self)
        note_widget.setPlainText(text)
        note_widget.setReadOnly(False)
        note_widget.setStyleSheet("background-color: palette(base)")
        #note_widget.setFixedSize(285, 200)
        note_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        #note_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        #note_widget.customContextMenuRequested.connect(lambda pos: self.show_note_context_menu(note_widget, pos))
        note_widget.SignalFocusIn.connect(lambda: self.vlc_widget.pause_video())
        note_widget.SignalFocusOut.connect(lambda: self.vlc_widget.play_video())

        note_frame = QFrame(self)
        #note_frame.setFixedSize(285, 200)
        note_frame.setStyleSheet("border: none; background-color: palette(base); padding: 5px; border-radius: 5px;")
        note_layout = QVBoxLayout(note_frame)
        note_layout.setContentsMargins(0, 0, 0, 0)
        note_layout.setSpacing(2)

        note_label = QLabel("Note", note_frame)
        note_label.setStyleSheet("font-weight: bold;")
        note_label.setAlignment(Qt.AlignLeft)

        note_layout.addWidget(note_label)
        note_layout.addWidget(note_widget)

        if button not in self.button_notes:
            self.button_notes[button] = []

        self.button_notes[button].append(note_widget)

        #note_widget.setFocus()

        # Trouver le `frame` associé au bouton et ajouter la note dedans
        for btn_data in self.stock_button:
            if btn_data["button"] == button:
                frame_layout = btn_data["frame"].layout()
                frame_layout.addWidget(note_frame)
                break  # On sort de la boucle une fois trouvé

        # Détecte si du texte est ajouté
        note_widget.textChanged.connect(lambda: self.on_text_changed(note_widget))



    def on_text_changed(self, note_widget):
        text = note_widget.toPlainText().strip()
        if text:
            note_widget.setStyleSheet("")  # Normal
        else:
            note_widget.setStyleSheet("color: gray; font-style: italic;")
        self.parent.emit_change()

    #menu clique droit note
    def show_note_context_menu(self, note_widget, pos):
        """ Affiche un menu contextuel sur un clic droit. """
        menu = QMenu(self)

        delete_action = QAction("Supprimer la note", self)
        delete_action.triggered.connect(lambda: self.remove_note(note_widget))

        menu.addAction(delete_action)
        
        menu.exec_(note_widget.mapToGlobal(pos))

    #fonction 1 clique droit note
    def remove_note(self, note_widget):
        """ Supprime la note de l'interface et de la liste. """
        for button, notes in self.button_notes.items():
            if note_widget in notes:
                notes.remove(note_widget)
                self.layout.removeWidget(note_widget)
                note_widget.deleteLater()
                break
        self.parent.emit_change()

    def extract_confirm(self, button):
        msg = QMessageBox(self)
        msg.setWindowTitle("Extraire le plan")
        msg.setText("Voulez-vous enregistrer le plan sélectionné ?")
        msg.setIcon(QMessageBox.Question)
        ok = msg.addButton("Oui", QMessageBox.ActionRole)
        cancel = msg.addButton("Annuler", QMessageBox.ActionRole)
        ok.clicked.connect(lambda _, btn=button : self.extract_action(btn))
        cancel.clicked.connect(msg.close)
        msg.show()

    #fonction 4 extraction
    def extract_action(self, button): 
        for btn_data in self.stock_button:
            if btn_data["button"] == button:
                time = btn_data["time"]
                end = btn_data["end"]
                duration = end - time


        capture_dir = os.path.join(str(Path.home()), "SLV_Content", "Captures_Vidéos")

        if not os.path.exists(capture_dir):
            os.makedirs(capture_dir,exist_ok=True)

        capture_path = os.path.join(capture_dir, f"{button.text()}_{self.time_manager.timecodename(time)}_{self.time_manager.timecodename(end)}.mp4")

        self.vlc_widget.extract_segment_with_ffmpeg(self.vlc_widget.path_of_media,time/1000,duration/1000,capture_path)
        affichage=MessagePopUp(self, time=-1, capture_button=True)


    #modif temps non utilisé
    def modify_time(self, button):

        for btn_data in self.stock_button:
            if btn_data["button"] == button:
                start = btn_data["time"]
                end = btn_data["end"]

        dialog = QDialog(self)
        dialog.setWindowTitle("Modification TimeCode")
        dialog.setModal(True)

        layout = QVBoxLayout(dialog)

        interval_layout = QHBoxLayout()

        start_time_editor_layout = QVBoxLayout()

        time_label = QLabel("Début :", dialog)
        start_time_editor_layout.addWidget(time_label)

        self.time = TimeEditor(dialog, self.vlc_widget.player.get_length(), self.vlc_widget.player.get_time(),fps=self.vlc_widget.fps)
        self.time.timechanged.connect(lambda: self.previewer1.preview_frame(self.time.get_time_in_milliseconds()))

        # Label pour afficher l'image d'aperçu
        self.img1 = QLabel("", dialog)
        self.img1.setAlignment(Qt.AlignCenter)
        start_time_editor_layout.addWidget(self.img1)
        self.previewer1 = FramePreviewer(self.img1, self.vlc_widget.fps, self.vlc_widget.path_of_media)  
        self.previewer1.preview_frame(self.time.get_time_in_milliseconds())   

        start_time_editor_layout.addWidget(self.time)

        interval_layout.addLayout(start_time_editor_layout)

        end_time_editor_layout = QVBoxLayout()

        time_label2 = QLabel("Fin :", dialog)
        end_time_editor_layout.addWidget(time_label2)

        self.time2 = TimeEditor(dialog, self.vlc_widget.player.get_length(), end ,fps=self.vlc_widget.fps)
        self.time2.timechanged.connect(lambda: self.previewer2.preview_frame(self.time2.get_time_in_milliseconds()))
        self.time.timechanged.connect(lambda: self.change_end_min_time(self.time.get_time_in_milliseconds())) 

        self.img2 = QLabel("", dialog)
        self.img2.setAlignment(Qt.AlignCenter)
        end_time_editor_layout.addWidget(self.img2)
        self.previewer2 = FramePreviewer(self.img2, self.vlc_widget.fps, self.vlc_widget.path_of_media)   
        self.previewer2.preview_frame(self.time2.get_time_in_milliseconds())

        end_time_editor_layout.addWidget(self.time2)
        interval_layout.addLayout(end_time_editor_layout)
        layout.addLayout(interval_layout)

        space = QHBoxLayout()
        load = QLabel("")
        load.setAlignment(Qt.AlignCenter)
        space.addWidget(load)
        layout.addLayout(space)

        # Boutons OK et Annuler
        button_layout = QHBoxLayout()
        ok_button = NoFocusPushButton("OK", dialog)
        cancel_button = NoFocusPushButton("Annuler", dialog)

        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        # Action du bouton OK
        def on_ok():
            if self.time.get_time_in_milliseconds() >= self.time2.get_time_in_milliseconds():
                affichage=MessagePopUp(self, time=-1, titre="Modification impossible", txt="Vérifiez que le timecode de fin se situe après le timecode de début.", type="warning")
                return
            new_time = self.time.get_time_in_milliseconds()
            end_time = self.time2.get_time_in_milliseconds()
            for btn_data in self.stock_button:
                if btn_data["button"] == button:
                    btn_data["time"] = new_time
                    btn_data["end"] = end_time
                    self.change_label_time(btn_data["label"],new_time,end_time)
                    self.parent.change_rect(btn_data["rect"],new_time,end_time)
            self.adjust_neighbors(new_time,end_time)
            self.reorganize_buttons()
            self.parent.emit_change()
            dialog.accept()


        ok_button.clicked.connect(on_ok)
        cancel_button.clicked.connect(dialog.reject)

        dialog.exec()

    def change_end_min_time(self, min_time):
        self.time2.on_new_min_value(min_time)
        self.previewer2.preview_frame(self.time2.get_time_in_milliseconds())

    def change_label_time(self,label,new_time,end_time):
        new_label ="Début : "+self.time_manager.m_to_hmsf(new_time)+" / Fin : "+self.time_manager.m_to_hmsf(end_time)+ " \nDurée : "+self.time_manager.m_to_hmsf(end_time-new_time)
        label.setText(new_label)

    def change_frame(self, id ,btn_data):
        """Met à jour l'affichage d'un bouton existant après modification de ses timecodes.

        Réutilise le "frame" existant.
        Les champs "Début / Fin / Durée" sont mis à jour.
        """
        try:
            stock = self.stock_button[id]
        except Exception:
            print("Erreur : ID de bouton non trouvé dans stock_button.")
            return

        # Mettre à jour les valeurs temporelles dans stock
        stock["time"] = btn_data.get("time", stock.get("time"))
        stock["end"] = btn_data.get("end", stock.get("end"))
        stock["frame1"] = btn_data.get("frame1", stock.get("frame1"))
        stock["frame2"] = btn_data.get("frame2", stock.get("frame2"))

        time = stock["time"]
        end = stock["end"]
        button = stock["button"]

        # Conserver les notes : si aucune note, créer une note vide pour l'édition
        if button not in self.button_notes or not self.button_notes.get(button):
            self.button_notes.setdefault(button, [])
            self.add_note(button, "")

        # Mettre à jour les champs "Début / Fin / Durée" dans le frame existant
        frame = stock.get("frame")
        if frame is not None and frame.layout() is not None:
            for i in range(frame.layout().count()):
                child = frame.layout().itemAt(i).widget()
                if not child:
                    continue
                label = child.findChild(QLabel)
                line_edit = child.findChild(MyLineEdit)
                if label and line_edit:
                    key = label.text().strip()
                    if key.startswith("Début"):
                        line_edit.setText(self.time_manager.m_to_hmsf(time))
                    elif key.startswith("Fin"):
                        line_edit.setText(self.time_manager.m_to_hmsf(end))
                    elif key.startswith("Durée"):
                        line_edit.setText(self.time_manager.m_to_hmsf(max(0, end - time)))

        # S'assurer que le nom du bouton affiché est à jour (ne pas recréer le bouton)
        try:
            button.setText(btn_data.get("button").text())
        except Exception:
            pass

        self.stock_button.sort(key=lambda b: b["time"])
        self.reorganize_buttons()

        self.segmentation_done.emit(True)
        
    def adjust_neighbors(self, new_time, new_end_time):
        frame1 = self.parent.get_frame(new_time)
        frame2 = self.parent.get_frame(new_end_time)
        tab_suppr = []
        
        for btn_data in self.stock_button:
            # Ignorer le bouton qui a exactement les mêmes bornes que le nouveau bouton
            if btn_data["time"] == new_time and btn_data["end"] == new_end_time:
                continue
                
            # Cas de chevauchement complet : le nouveau bouton est au milieu d'un bouton existant
            if btn_data["time"] < new_time and btn_data["end"] > new_end_time:
                # On conserve la partie avant en modifiant la fin du bouton existant
                old_end = btn_data["end"]
                btn_data["end"] = new_time
                btn_data["frame2"] = frame1
                self.parent.change_rect(btn_data["rect"], btn_data["time"], new_time)
                self.change_label_time(btn_data["label"], btn_data["time"], new_time)
                
                # Et on crée un nouveau bouton pour la partie après
                # On suppose ici que btn_data possède une clé "name" à réutiliser, sinon vous pouvez passer un nom souhaité.
                self.parent.add_new_button(
                    name=btn_data.get("name", "Nouveau Plan"), 
                    time=new_end_time, 
                    end=old_end, 
                    frame1=frame2, 
                    frame2=self.parent.get_frame(old_end)
                )
            else:
                # Cas où le bouton existant commence dans l'intervalle du nouveau bouton
                if btn_data["time"] == new_end_time or (btn_data["time"] <= new_end_time and btn_data["time"] > new_time):
                    if new_end_time < btn_data["end"]:
                        btn_data["time"] = new_end_time
                        btn_data["frame1"] = frame2
                        self.parent.change_rect(btn_data["rect"], new_end_time, btn_data["end"])
                        self.change_label_time(btn_data["label"], new_end_time, btn_data["end"])
                    else:
                        tab_suppr.append(btn_data["button"])
                # Cas où le bouton existant se termine dans l'intervalle du nouveau bouton
                if btn_data["end"] == new_time or (btn_data["end"] >= new_time and btn_data["end"] <= new_end_time):
                    if new_time > btn_data["time"]:
                        btn_data["end"] = new_time
                        btn_data["frame2"] = frame1
                        self.parent.change_rect(btn_data["rect"], btn_data["time"], new_time)
                        self.change_label_time(btn_data["label"], btn_data["time"], new_time)
                    else:
                        tab_suppr.append(btn_data["button"])
                        
        for btn in tab_suppr:
            self.parent.delate_button(btn)


    def update_label_numbering_shots(self):
        """Met à jour la numérotation des plans affichée dans les side menu widget"""
        for i, btn_data in enumerate(self.stock_button):
            numbering_name = f"Plan n°{i + 1}"
            frame_layout = btn_data["frame"].layout()
            for j in range(frame_layout.count()):
                child = frame_layout.itemAt(j).widget()
                if child is None:
                    continue
                for desc in child.findChildren(QWidget):
                    if isinstance(desc, (MyLineEdit, QLineEdit)) and desc.text().startswith("Plan n°"):
                        desc.setText(numbering_name)
                        found = True
                        break
                    if isinstance(desc, QLabel) and desc.text().startswith("Plan n°"):
                        desc.setText(numbering_name)
                        found = True
                        break
                if found:
                    break