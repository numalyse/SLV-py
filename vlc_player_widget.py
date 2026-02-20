import sys
import os
from pathlib import Path
from PIL import Image
import cv2
import numpy as np
from moviepy import VideoFileClip

import vlc

import time
import threading
import ffmpeg
from datetime import datetime
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QFileDialog, QSlider, QLabel, QLineEdit
from PySide6.QtCore import Qt, QTimer, Signal, QMetaObject, QObject
from PySide6.QtGui import QKeySequence, QShortcut


from preference_manager import PreferenceManager
from custom_slider import CustomSlider
from custom_timestamp_edit import CustomTimestampEdit
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
    ts_was_video_playing = False

    def __init__(self, parent=None,add_controls=False,add_window_time=True,m=False,c=True):
        super().__init__(parent)
        self.parent_element = parent
        self.instance = vlc.Instance("--quiet --aout=directsound")

        #print(self.instance)
        self.player = self.instance.media_player_new()
        self.media = None  # Pour suivre le fichier chargé
        self.ac = add_controls
        self.mute = m
        self.pref_manager = PreferenceManager(self)
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
        self.loop = True

        self.estimated_time = None  # temps estimé après avance frame par frame
        self.setAcceptDrops(True) # Nécessaire pour le drag & drop



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
        self.eject_button.clicked.connect(lambda: self.eject_video(True))
        self.button_layout.addWidget(self.eject_button)

        self.full_screen_button = NoFocusPushButton("⛶ Plein écran", self)
        self.full_screen_button.clicked.connect(self.full_screen_action)
        self.button_layout.addWidget(self.full_screen_button)

        self.loop_button = NoFocusPushButton("🔁 Boucle", self)
        self.loop_button.clicked.connect(self.toggle_loop)
        self.loop_button.setStyleSheet("background-color: lightblue;")
        self.button_layout.addWidget(self.loop_button)

        parent_layout.addLayout(self.button_layout)

    def toggle_loop(self):
        self.loop = not self.loop
        if self.loop:
            self.loop_button.setStyleSheet("background-color: lightblue;")
        else:
            self.loop_button.setStyleSheet("")

    def create_keyboard(self):
        self.play_pause_shortcut = QShortcut(QKeySequence("Space"), self)
        self.play_pause_shortcut.activated.connect(self.toggle_play_pause)

        self.move_back_shortcut = QShortcut(QKeySequence("Left"), self)
        self.move_back_shortcut.activated.connect(self.move_back)

        self.move_front_shortcut = QShortcut(QKeySequence("Right"), self)
        self.move_front_shortcut.activated.connect(self.move_front)

        self.move_front_one_frame_shortcut = QShortcut(QKeySequence("E"), self)
        self.move_front_one_frame_shortcut.activated.connect(self.move_front_one_frame)
        
    def timestamp_edit_play_pause(self):
        """ Si la vidéo était en train de jouer, relance la lecture """
        if(self.ts_was_video_playing):
            self.play_video()
    
    def on_timestamp_focus_in(self):
        self.ts_was_video_playing = self.player.is_playing()
        self.pause_video()


    def create_window_time(self, parent_layout):
        # Layout pour le temps + bouton mute
        self.time_layout = QHBoxLayout()
        self.line_edit = CustomTimestampEdit(self)
        self.line_edit.focus_in.connect(self.on_timestamp_focus_in)
        self.line_edit.value_changed.connect(self.on_value_changed)
        self.line_edit.edit_finished.connect(self.timestamp_edit_play_pause)

        # Affichage du temps
        self.time_label = QLabel("00:00:00[00] / 00:00:00[00]", self)
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setFixedHeight(15)

        self.speed_button = PlaybackSpeedButton(parent=self)
        self.mute_button = NoFocusPushButton("🔇" if self.mute else "🔊", self)
        # self.mute_button.setCheckable(True)
        # self.mute_button.setChecked(self.mute)  # Définit l'état initial du bouton

        self.mute_button.setFixedSize(30, 30)
        
        self.mute_button.setCheckable(False)
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
        self.progress_slider.sliderMoved.connect(self.on_slider_value_change_time_edit)
        self.progress_slider.slider_mouse_clicked.connect(self.on_slider_clicked)
        self.progress_slider.slider_mouse_released.connect(self.on_slider_released)
        self.progress_slider.setEnabled(False)
        parent_layout.addWidget(self.progress_slider)

    def on_slider_value_change_time_edit(self):
        current_time = self.get_current_time()
        current_time_str = self.time_manager.m_to_hmsf(current_time).replace(",",":")
        self.line_edit.set_text(f"{current_time_str}")

    def toggle_play_pause(self):
        """ Joue ou met en pause la vidéo, ou demande un fichier si aucune vidéo chargée. """
        if self.media is None:
            self.load_file()
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
        self.player.set_time(self.get_current_time()-5000)
        
    def move_front(self):
        self.player.set_time(self.get_current_time()+5000)

    def move_front_one_frame(self):
        if self.media is None:
            return
        
        if self.player.is_playing():
            self.pause_video()

        try:
            # get_time() n'est pas mis à jour immédiatement après next_frame(),
            # on stocke un temps estimé que update_ui() utilisera
            self.player.next_frame()

            frame_duration_ms = 1000.0 / self.fps

            # si on a deja un temps estimé, on part de celui-ci pour éviter d'avoir un décalage, sinon on part du temps actuel du player
            vlc_time = self.player.get_time()
            estimated_time = self.estimated_time if self.estimated_time is not None else 0
            current_time = max(vlc_time, estimated_time)

            total_time = self.player.get_length()

            if total_time > 0: # ne pas depasser la durée totale de la vidéo
                self.estimated_time = min(current_time + int(frame_duration_ms), total_time)

            self.update_ui()

            return
        except Exception:
            pass    

    def full_screen_action(self):
        # Demande le full screen
        self.full_screen_requested.emit(self)


    def load_file(self,auto=True):
        self.pref_manager.load_preferences()
        file_path, _ = QFileDialog.getOpenFileName(self, "Ouvrir une vidéo", self.pref_manager.preferences["open_video_path"], "Fichiers vidéo (*.mp4 *.avi *.mkv *.mov *.m4v *.vob)")
        if not file_path :
            return
        self.pref_manager.change_preference("open_video_path", file_path)
        if auto : self.load_video(file_path)
        self.path_of_media=file_path
        return file_path


    def load_video(self,file_path,suppr_seg=True):
        if file_path:
            duration_ms = None
            self.estimated_time = None
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

            self.progress_slider.setEnabled(True)
            self.line_edit.fps = self.fps

            if duration_ms is not None:
                self.progress_slider.setRange(0, duration_ms)
                self.line_edit.max_time = duration_ms
            
            if(self.begin):
                self.player.play()
                self.play_pause_button.setText("⏯️ Pause")

            self.time_label.setStyleSheet("color: red;")            
            self.active_segmentation()
            if (suppr_seg):
                self.enable_load.emit(True)
            self.timer.start()  

            self.update_video_name()
            self.video_name_label.setVisible(not self.full_screen)

            # si on est dans un lecteur sync mode, on veut que le slider soit à jour et que la vidéo soit prête à être jouée, 
            # mais on ne veut pas que la vidéo commence à jouer automatiquement
            from main_window import VLCMainWindow
            if not isinstance(self.parent_element, VLCMainWindow):
                # pour avoir le slider qui se met a jour, on play puis remet à 0, sinon player.get_length() / get_time() retourne -1 et le slider ne fonctionne pas
                self.player.play()
                self.player.set_pause(1)
                self.set_position(0)
                
                self.update_ui() # update l'ui pour afficher la totale ect

    def get_current_time(self):
        if self.media is None:
            return 0

        vlc_time = self.player.get_time()
        estimated_time = self.estimated_time if self.estimated_time is not None else 0
        current_time = max(vlc_time, estimated_time)

        return current_time     
    
    def play_video(self):
        self.player.play()
        self.play_pause_button.setText("⏯️ Pause")

    def pause_video(self): 
        self.player.set_pause(1)
        self.play_pause_button.setText("⏯️ Lire")
        #self.timer.stop()

    def on_slider_clicked(self):
        self.estimated_time = None
        self.slider_was_playing = self.player.is_playing()
        self.pause_video()
    
    def on_slider_released(self):
        self.estimated_time = None
        if self.slider_was_playing:
            self.play_video()

    def stop_video(self):
        self.estimated_time = None
        """ Remet la vidéo à 00:00:00 et pause la lecture. """
        self.restart_video(False) # remet la vidéo à 0 et force la pause directement après le chargement


    def eject_video(self, use_stop = True):
        """ Arrête et décharge la vidéo. Lance player.stop() depuis un thread séparé """

        if self.media is None or self.player is None: # Si déjà éjecté ou pas de vidéo chargée, on ne fait rien
            return

        self.timer.stop()
        
        if self.player.is_playing():
            self.player.set_pause(1)

        self.path_of_media = None
        self.media = None
        self.estimated_time = None

        if self.ac: 
            self.play_pause_button.setText("⏯️ Lire")

        self.progress_slider.setValue(0)
        self.progress_slider.setEnabled(False)

        self.time_label.setText("00:00:00 / 00:00:00")
        self.time_label.setStyleSheet("color: black;")

        self.disable_segmentation()
        self.update_video_name()

        self.enable_load.emit(False)

        if(use_stop):
            def _stop_player():
                try:
                    self.player.stop()
                except Exception:
                    pass

            threading.Thread(target=_stop_player, daemon=True).start()
        else:
            self.player.set_media(None)


    def restart_video(self, auto_play=True):
        if auto_play: 
            self.player.set_media(None)
            self.player.set_media(self.media)
            self.player.set_time(0)
            self.player.play()
        else :
            self.player.stop()
            self.player.set_media(None)
            self.player.set_media(self.media)
            self.player.set_time(0)
            self.player.play()
            self.play_pause_button.setText("⏯️ Lire")
            self.player.set_pause(1)

        self.estimated_time = None 

    def capture_screenshot(self, name="",post_traitement=False,format_capture=False,gamma=1.4):
        """ Capture un screenshot de la vidéo. """
        if not os.path.exists(self.capture_dir):
            os.makedirs(self.capture_dir, exist_ok=True)

        file_name = self.name_of_video()
        #timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
        raw_timecode = self.time_manager.m_to_hmsf(self.get_current_time())
        timecode = self.time_manager.sanitize_timecodename(raw_timecode)
        #framenumber = self.time_manager.m_to_frame(self.player.get_time())

        capture_path_str = ""

        # Définir le chemin du fichier en fonction du format
        if name :
            capture_path = os.path.join(self.capture_dir, f"{file_name}_{timecode}_{name}.png")
        else:
            capture_path = os.path.join(self.capture_dir, f"{file_name}_{timecode}.png")

        # Capturer l'image (mais ne pas se fier au retour de la fonction)
        self.player.video_take_snapshot(0, capture_path, 0, 0)

        # Vérifier si l'image a bien été enregistrée
        if os.path.exists(capture_path):
            print(f" Capture enregistrée : {capture_path}")
            if post_traitement:

                image = cv2.imread(capture_path)
                cv2.imwrite(capture_path, image)
                capture_path_str = file_name + "_" + timecode + "_adjusted"
                print(capture_path)
                

            # Si le format demandé est JPEG, convertir l'image
            if format_capture:  # Vérifie si format_capture existe et est True
                print("Conversion en JPEG...")
                capture_path=self.png_to_jpeg(capture_path)

        else:
            print("Erreur : La capture n'a pas été enregistrée !")

        return capture_path, timecode, capture_path_str, self.capture_dir

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

        total_time = self.player.get_length()

        current_time = self.get_current_time()

        if current_time >= 0 and total_time > 0:
            self.progress_slider.setValue(int((current_time / total_time) * total_time))
            current_time_str = self.time_manager.m_to_hmsf(current_time).replace(",",":")
            #self.line_edit.setText(current_time_str)
            total_time_str = self.time_manager.m_to_hmsf(total_time).replace(",",":")
            self.time_label.setText(f"{current_time_str} / {total_time_str}")
            self.line_edit.blockSignals(True)
            if self.player.is_playing(): self.line_edit.set_text(current_time_str)
            self.line_edit.blockSignals(False)

        if self.player.get_state()==6 :
            self.restart_video(self.loop) # si la vidéo est à la fin et que le mode boucle est activé, recommence la vidéo, sinon remet la vidéo à 0 et pause

    def set_position(self, position):
        """ Définit la position de lecture en fonction du slider. """
        if self.player.get_length() <= 0:
            return

        position = position / self.player.get_length()
        if position == self.previous_slider_pos and position != 0:
            return

        if self.media is not None:
            self.estimated_time = None 
            # décalage à gauche atténué mais toujours présent 
            total_time = float(self.player.get_length())  # en secondes
            new_time = (float(position)) * total_time
            self.player.set_time(int(new_time))
            self.previous_slider_pos = position

    def on_value_changed(self):
        """ Change la position de la vidéo lorsqu'on modifie le timecode dans le QLineEdit. """
        time_str = self.line_edit.get_time_str()
        
        # Vérifier si le format est valide (mm:ss)
        try:
            hours, minutes, seconds_frames = time_str.split(":")
            seconds, frames = seconds_frames.split("[")
            frames = int(str(frames).replace("]", ""))
            new_time = (int(hours)*3600 + int(minutes) * 60 + int(seconds)) * 1000 + 1000/self.fps * frames # Convertir en millisecondes
        except ValueError:
            print("Format du timecode invalide. Utilisez le format HH:MM:SS[FF].")
            return  # Si la conversion échoue, on ignore l'entrée
        
        bounded_time = max(0, min(new_time, self.line_edit.max_time))
        if bounded_time != new_time:
            self.line_edit.blockSignals(True)
            self.line_edit.set_text(TimeManager.m_to_hmsf(self, bounded_time))
            self.line_edit.blockSignals(False)
        self.set_position_timecode(bounded_time)
    
    
    def set_position_timecode(self,new_time):
        # Utilisation de set_position pour une meilleure précision
        # Besoin d'avoir un temps normalisé entre 0 et 1 pour set_position, d'où la division par total_time
        total_time = self.player.get_length()
        if total_time > 0 and 0 <= new_time <= total_time:
            self.estimated_time = None  # reset du temps estimé en cas de changement manuel du timecode
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

    def dragEnterEvent(self, event):
        # Accepter les fichiers droppés
        if self.test_video_drop(event) != None:
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dropEvent(self, event):
        file_path = self.test_video_drop(event)
        if file_path != None:
            self.load_video(file_path)
    
    def test_video_drop(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasFormat("text/uri-list"):
            mime_data = event.mimeData()
            if mime_data.hasUrls():
                urls = mime_data.urls()
                for url in urls:
                    file_path = url.toLocalFile()
                    if file_path.lower().endswith(('.mp4', '.avi', '.mkv', '.mov', '.m4v', '.vob')):
                        return file_path
        return

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

    def get_number_of_frames(self):
        duration_ms = self.player.get_length()
        if duration_ms <= 0:
            return 0
        total_frames = self.time_manager.m_to_frame(duration_ms)
        return total_frames
