import sys
import os
from pathlib import Path
from PIL import Image
import cv2
import numpy as np
from moviepy import VideoFileClip

import vlc

import time
import ffmpeg
from datetime import datetime
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QFileDialog, QSlider, QLabel, QLineEdit
from PySide6.QtCore import Qt, QTimer, Signal, QMetaObject, QObject
from PySide6.QtGui import QKeySequence, QShortcut



from custom_slider import CustomSlider
from playback_speed_button import PlaybackSpeedButton
from time_manager import TimeManager
from no_focus_push_button import NoFocusPushButton
from message_popup import MessagePopUp


class VLCPlayerWidget(QWidget):
    enable_segmentation = Signal(bool)
    enable_recording = Signal(bool)

    # Signal pour demander le plein écran d'un player, envoie une référence au player qui a demandé le plein écran à sync_widget.
    full_screen_requested = Signal(object) 

    enable_load = Signal(bool)
    slider_was_playing = False
    previous_slider_pos = 0

    def __init__(self, parent=None,add_controls=False,add_window_time=True,m=True,c=True):
        super().__init__(parent)
        self.parent_element = parent
        self.instance = vlc.Instance("--quiet")

        #print(self.instance)
        self.player = self.instance.media_player_new()
        self.media = None  # Pour suivre le fichier chargé
        self.ac = add_controls
        self.mute = m
        if self.mute :
            self.player.audio_set_mute(True)
        else : 
            self.player.audio_set_mute(False)
        
        self.capture_dir = os.path.join(str(Path.home()), "SLV_Content", "Captures_Images")
        self.capture_video_dir = os.path.join(str(Path.home()),  "SLV_Content", "Captures_Vidéos")
        self.path_of_media=""

        # Layout principal
        main_layout = QVBoxLayout(self)
        
        # Cadre vidéo
        self.video_frame = QFrame(self)
        self.video_frame.setStyleSheet("background-color: black;")
        main_layout.addWidget(self.video_frame)

        # label pour afficher le nom de la vidéo
        self.video_name_label = QLabel("", self)
        self.video_name_label.setAlignment(Qt.AlignCenter)
        self.video_name_label.setFixedHeight(10)
        
        self.update_video_name() # à la création va permettre de cacher le label tant qu'aucune vidéo n'est chargée
        main_layout.addWidget(self.video_frame)
        main_layout.addWidget(self.video_name_label)

        if add_window_time:
            self.create_window_time(main_layout)
        if add_controls : 
            self.create_control_buttons(main_layout)
        if c :
            self.create_keyboard()

        # Définir la sortie vidéo en fonction de l'OS
        if sys.platform.startswith("linux"):
            self.player.set_xwindow(self.video_frame.winId())
        elif sys.platform == "win32":
            self.player.set_hwnd(self.video_frame.winId())
        elif sys.platform == "darwin":
            self.player.set_nsobject(self.video_frame.winId())

        # Timer pour mettre à jour le slider et l'affichage du temps
        self.timer = QTimer(self)
        self.timer.setInterval(200)
        self.timer.timeout.connect(self.update_ui)

        self.begin=True

        self.is_recording=False
        self.start=0
        self.end=0

        self.time_manager=TimeManager()

        self.fps=25

        self.full_screen=False

    def display(self,visible):
        self.video_name_label.setVisible(visible)
        self.toggle_layout_visibility(self.button_layout,visible)
        self.toggle_layout_visibility(self.time_layout,visible)
        self.progress_slider.setVisible(visible)

    # met a jour le nom de la vidéo affiché dans le label en fonction du fichier chargé et hide le label si aucun fichier chargé
    def update_video_name(self):
        if self.path_of_media:
            file_name = os.path.basename(self.path_of_media)
            self.video_name_label.setText(file_name)
            self.video_name_label.setVisible(True)
        else:
            self.video_name_label.setText("")
            self.video_name_label.setVisible(False)

    def toggle_layout_visibility(self, layout, visible):
        for i in range(layout.count()):
            widget = layout.itemAt(i).widget()
            if widget:
                widget.setVisible(visible)

    def create_control_buttons(self, parent_layout):
        """ Crée et ajoute automatiquement les boutons de contrôle au layout donné. """
        self.button_layout = QHBoxLayout()

        self.play_pause_button = NoFocusPushButton("⏯️ Lire", self)
        self.play_pause_button.clicked.connect(self.toggle_play_pause)
        self.button_layout.addWidget(self.play_pause_button)

        self.stop_button = NoFocusPushButton("⏹️ Stop", self)
        self.stop_button.clicked.connect(self.stop_video)
        self.button_layout.addWidget(self.stop_button)

        self.eject_button = NoFocusPushButton("⏏️ Éjecter", self)
        self.eject_button.clicked.connect(self.eject_video)
        self.button_layout.addWidget(self.eject_button)

        self.full_screen_button = NoFocusPushButton("⛶ Plein écran", self)
        self.full_screen_button.clicked.connect(self.full_screen_action)
        self.button_layout.addWidget(self.full_screen_button)

        parent_layout.addLayout(self.button_layout)

    def create_keyboard(self):
        self.play_pause_shortcut = QShortcut(QKeySequence("Space"), self)
        self.play_pause_shortcut.activated.connect(self.toggle_play_pause)

        self.move_back_shortcut = QShortcut(QKeySequence("Left"), self)
        self.move_back_shortcut.activated.connect(self.move_back)

        self.move_front_shortcut = QShortcut(QKeySequence("Right"), self)
        self.move_front_shortcut.activated.connect(self.move_front)


    def create_window_time(self, parent_layout):
        # Layout pour le temps + bouton mute
        self.time_layout = QHBoxLayout()

        self.line_edit=QLineEdit()
        self.line_edit.setText("00:00:00")
        self.line_edit.setAlignment(Qt.AlignCenter)
        self.line_edit.setFixedWidth(80)
        self.line_edit.setFocusPolicy(Qt.ClickFocus)
        self.line_edit.textChanged.connect(self.on_value_changed)

        # Affichage du temps
        self.time_label = QLabel("00:00:00 / 00:00:00", self)
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setFixedHeight(15)

        self.speed_button = PlaybackSpeedButton(parent=self)

        self.mute_button = NoFocusPushButton("🔇" if self.mute else "🔊", self)
        self.mute_button.setCheckable(True)
        self.mute_button.setChecked(self.mute)  # Définit l'état initial du bouton

        self.mute_button.setFixedSize(30, 30)
        self.mute_button.setCheckable(True)
        self.mute_button.clicked.connect(self.toggle_mute)  

        # Ajouter les éléments au layout
        self.time_layout.addWidget(self.line_edit)
        self.time_layout.addWidget(self.time_label)
        self.time_layout.addWidget(self.speed_button)
        self.time_layout.addWidget(self.mute_button)
        parent_layout.addLayout(self.time_layout)

        # Slider pour la progression
        self.progress_slider = CustomSlider(Qt.Horizontal, self)
        self.progress_slider.setRange(0, 1000)
        self.progress_slider.sliderMoved.connect(self.set_position)
        self.progress_slider.slider_mouse_clicked.connect(self.on_slider_clicked)
        self.progress_slider.slider_mouse_released.connect(self.on_slider_released)
        self.progress_slider.setEnabled(False)
        parent_layout.addWidget(self.progress_slider)

    def toggle_play_pause(self):
        """ Joue ou met en pause la vidéo, ou demande un fichier si aucune vidéo chargée. """
        if self.media is None:
            self.load_file()
            self.progress_slider.setRange(0, self.player.get_length())
        elif self.player.is_playing():
            self.pause_video()
        else:
            self.play_video()

    def toggle_mute(self):
        current_mute_state = self.player.audio_get_mute()
        new_mute_state = not current_mute_state  # Inverser l'état du mute

        self.player.audio_set_mute(new_mute_state)
        self.mute=new_mute_state
        self.mute_button.setChecked(new_mute_state)
        self.mute_button.setText("🔇" if new_mute_state else "🔊")

        #print(f"Mute toggled: {new_mute_state}")

    def toggle_speed(self):
        self.pause_video()
        self.player.set_rate(self.speed_button.getSpeed())
        self.play_video()

    def move_back(self):
        self.player.set_time(self.player.get_time()-5000)

    def move_front(self):
        self.player.set_time(self.player.get_time()+5000)

    def full_screen_action(self):
        # Demande le full screen
        self.full_screen_requested.emit(self)


    def load_file(self,auto=True):
        file_path, _ = QFileDialog.getOpenFileName(self, "Ouvrir une vidéo", "", "Fichiers vidéo (*.mp4 *.avi *.mkv *.mov *.m4v)")
        if not file_path :
            return 
        if auto : self.load_video(file_path)
        self.path_of_media=file_path
        return file_path


    def load_video(self,file_path,suppr_seg=True):
        if file_path:
            duration_ms = None
            try:
                video = VideoFileClip(file_path)
                self.fps = video.fps
                duration_ms = int(video.duration * 1000)
            except Exception as e:
                #print(f"Erreur lors du chargement de la vidéo : {e}")
                self.fps = 25
            self.time_manager.set_fps(self.fps)

            self.path_of_media=file_path
            self.media = self.instance.media_new(file_path)
            self.player.set_media(self.media)
            self.player.audio_set_mute(self.mute)

            if duration_ms is not None:
                self.progress_slider.setRange(0, duration_ms)
            
            if(self.begin):
                self.player.play()
                self.play_pause_button.setText("⏯️ Pause")

            self.progress_slider.setEnabled(True)
            self.time_label.setStyleSheet("color: red;")            
            self.active_segmentation()
            if (suppr_seg):
                self.enable_load.emit(True)
            self.timer.start()  

            self.update_video_name()
    
    def play_video(self):
        self.player.play()
        self.play_pause_button.setText("⏯️ Pause")

    def pause_video(self):
        self.player.set_pause(1)
        self.play_pause_button.setText("⏯️ Lire")
        #self.timer.stop()

    def on_slider_clicked(self):
        self.slider_was_playing = self.player.is_playing()
        self.pause_video()
    
    def on_slider_released(self):
        if self.slider_was_playing:
            self.play_video()

    def stop_video(self):
        """ Remet la vidéo à 00:00:00 et pause la lecture. """
        self.restart_video()
        self.pause_video()

    def empty_video_frame(self):
        """ Forcer le nettoyage de la dernière frame en détachant puis réattachant la sortie vidéo au player """
        if sys.platform.startswith("linux"):
            self.player.set_xwindow(0)
            self.player.set_xwindow(self.video_frame.winId())
        elif sys.platform == "win32":
            self.player.set_hwnd(0)
            self.player.set_hwnd(self.video_frame.winId())
        elif sys.platform == "darwin":
            self.player.set_nsobject(0)
            self.player.set_nsobject(self.video_frame.winId())

    # L'éjection est différée pour éviter les crashs liés à VLC, par défaut, pas différé (0ms)
    def eject_video(self):
        """ Arrête et décharge la vidéo. """

        if self.media is None or self.player is None: # Si déjà éjecté ou pas de vidéo chargée, on ne fait rien
            return

        self.timer.stop()
        
        if self.player.is_playing():
            self.player.set_pause(1)

        # Détacher le média sans appeler stop() sinon crash VLC, mais ça laisse la dernière frame affichée, d'où le nettoyage visuel ensuite
        self.player.set_media(None)
        self.path_of_media = None
        self.media = None

        self.empty_video_frame()

        if self.ac: 
            self.play_pause_button.setText("⏯️ Lire")
        
        self.progress_slider.setValue(0)
        self.progress_slider.setEnabled(False)

        self.time_label.setText("00:00:00 / 00:00:00")
        self.time_label.setStyleSheet("color: black;")

        self.disable_segmentation()
        self.update_video_name()
        self.enable_load.emit(False)

    def restart_video(self):
        self.player.stop()
        self.media = None
        if self.ac : 
            self.play_pause_button.setText("⏯️ Lire")
        self.timer.stop()
        self.progress_slider.setValue(0)
        self.progress_slider.setEnabled(False)
        self.time_label.setText("00:00:00 / 00:00:00")
        self.time_label.setStyleSheet("color: white;")
        self.load_video(self.path_of_media,False)

    def capture_screenshot(self, name="",post_traitement=False,format_capture=False,gamma=1.4):
        """ Capture un screenshot de la vidéo. """
        if not os.path.exists(self.capture_dir):
            os.makedirs(self.capture_dir, exist_ok=True)

        file_name = self.name_of_video()
        #timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
        raw_timecode = self.time_manager.m_to_hmsf(self.player.get_time())
        timecode = self.time_manager.sanitize_timecodename(raw_timecode)
        #framenumber = self.time_manager.m_to_frame(self.player.get_time())

        # Définir le chemin du fichier en fonction du format
        if name :
            capture_path = os.path.join(self.capture_dir, f"{file_name}_{timecode}_{name}.png")
        else:
            if post_traitement:
                capture_path = os.path.join(self.capture_dir, f"{file_name}_{timecode}_adjust.png")
            else:
                capture_path = os.path.join(self.capture_dir, f"{file_name}_{timecode}.png")

        # Capturer l'image (mais ne pas se fier au retour de la fonction)
        self.player.video_take_snapshot(0, capture_path, 0, 0)

        # Vérifier si l'image a bien été enregistrée
        if os.path.exists(capture_path):
            print(f" Capture enregistrée : {capture_path}")
            if post_traitement:
                image = cv2.imread(capture_path)
                image_corrige=self.adjust_gamma(image,gamma=gamma)
                cv2.imwrite(capture_path,image_corrige)

            # Si le format demandé est JPEG, convertir l'image
            if format_capture:  # Vérifie si format_capture existe et est True
                print("Conversion en JPEG...")
                capture_path=self.png_to_jpeg(capture_path)

        else:
            print("Erreur : La capture n'a pas été enregistrée !")

        return capture_path, timecode

    def adjust_gamma(self,image, gamma=1.4):
        inv_gamma = 1.0 / gamma
        table = np.array([(i / 255.0) ** inv_gamma * 255 for i in np.arange(0, 256)]).astype("uint8")
        return cv2.LUT(image, table)

    def png_to_jpeg(self,capture_path):
        jpeg_path = capture_path.replace(".png", ".jpg")
        try:
            img = Image.open(capture_path)
            img = img.convert("RGB")  # Supprime la transparence pour JPEG
            img.save(jpeg_path, "JPEG", quality=60)
            os.remove(capture_path)  # Supprimer l'ancien fichier PNG
            print(f" Converti en JPEG : {jpeg_path}")
            return jpeg_path
        except Exception as e:
            print(f" Erreur lors de la conversion en JPEG : {e}")

    def name_of_video(self):
        return os.path.splitext(os.path.basename(self.path_of_media))[0]

    def update_ui(self):
        """ Met à jour le slider et l'affichage du temps. """

        # print("var",self.mute)
        # print("état",self.player.audio_get_mute())

        if self.media is None:
            return

        # Position actuelle et durée totale
        current_time = self.player.get_time()
        total_time = self.player.get_length()

        if current_time >= 0 and total_time > 0:
            self.progress_slider.setValue(int((current_time / total_time) * total_time))
            current_time_str = self.time_manager.m_to_hmsf(current_time).replace(",",":")
            #self.line_edit.setText(current_time_str)
            total_time_str = self.time_manager.m_to_hmsf(total_time).replace(",",":")
            self.time_label.setText(f"{current_time_str} / {total_time_str}")

        if self.player.get_state()==6 :
            self.restart_video()

    def set_position(self, position):
        """ Définit la position de lecture en fonction du slider. """
        position = position / self.player.get_length()
        if position == self.previous_slider_pos:
            return

        if self.media is not None:
            
            # décalage à gauche atténué mais toujours présent 
            total_time = float(self.player.get_length())  # en secondes
            new_time = (float(position)) * total_time
            self.player.set_time(int(new_time))
            self.previous_slider_pos = position

    def on_value_changed(self):
        """ Change la position de la vidéo lorsqu'on modifie le timecode dans le QLineEdit. """
        time_str = self.line_edit.text()
        
        # Vérifier si le format est valide (mm:ss)
        try:
            hours, minutes, seconds = map(int, time_str.split(":"))
            new_time = (hours*3600 + minutes * 60 + seconds) * 1000  # Convertir en millisecondes
        except ValueError:
            return  # Si la conversion échoue, on ignore l'entrée

        self.set_position_timecode(new_time)
    
    
    def set_position_timecode(self,new_time):
        # Utilisation de set_position pour une meilleure précision
        # Besoin d'avoir un temps normalisé entre 0 et 1 pour set_position, d'où la division par total_time
        total_time = self.player.get_length()
        if total_time > 0 and 0 <= new_time <= total_time:
            normalized_time = new_time / total_time
            self.player.set_position(normalized_time) 
            self.update_ui()

    def active_segmentation(self):
        self.enable_segmentation.emit(True)

    def disable_segmentation(self):
        self.enable_segmentation.emit(False)

    def capture_video(self):
        if self.is_recording:
            return self.stop_recording()
        else:
            self.start_recording()

    #extraction vidéo temps en secondes
    def extract_segment_with_ffmpeg(self,input_file, start_time, duration, output_file):
        try:
            # Utilisation de la librairie ffmpeg-python
            (
                ffmpeg
                .input(input_file, ss=start_time)  # Spécifie le fichier d'entrée et le temps de début
                .output(output_file, t=duration)  # Définit la durée 
                .run(overwrite_output=True, quiet=True)  # Exécute la commande sans afficher la sortie
            )
            print(f"Extrait enregistré dans {output_file}")
        except ffmpeg.Error as e:
            print(f"Erreur lors de l'extraction : {e.stderr.decode()}")


    def start_recording(self):
        self.is_recording=True
        self.enable_recording.emit(True)
        self.start=self.player.get_time()

    def stop_recording(self):
        self.is_recording = False
        self.enable_recording.emit(False)
        end_acc = self.player.get_time()
        self.end = end_acc // 1000  # Conversion en secondes
        duration = self.end - (self.start // 1000 )

        if not os.path.exists(self.capture_video_dir):
            os.makedirs(self.capture_video_dir)

        file_name = os.path.splitext(os.path.basename(self.path_of_media))[0]
        capture_path = os.path.join(self.capture_video_dir, f"{file_name}_{self.time_manager.timecodename(self.start)}_{self.time_manager.timecodename(end_acc)}.mp4")
        self.extract_segment_with_ffmpeg(self.path_of_media, self.start//1000, duration, capture_path)
        msg=MessagePopUp(self,txt="Capture vidéo enregistré dans SLV_Content/Captures_Vidéos")
        return capture_path



    def get_subtitles(self):
        descriptions = self.player.video_get_spu_description()
        
        if descriptions is None:
            return []

        pistes = []
        for desc in descriptions:
            pistes.append({'id': desc[0], 'nom': desc[1]})
    
        return pistes

    def get_track(self):
        return self.player.video_get_spu()

    def set_subtitles(self,id=-1):
        self.player.video_set_spu(id)

    def get_size_of_slider(self):
        #print("Taille :",self.progress_slider.width())
        return self.progress_slider.width()

