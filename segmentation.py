from PySide6.QtCore import QThread, Signal
import cv2
import os

from scenedetect import detect, AdaptiveDetector, ContentDetector, ThresholdDetector, HistogramDetector, HashDetector, open_video, SceneManager, FrameTimecode
from scenedetect.scene_manager import save_images


class SegmentationThread(QThread):
    segmentation_done = Signal(list)  # Signal émis à la fin

    def __init__(self, video_path,color=True):
        super().__init__()
        self.video_path = video_path
        self.running = True  # Flag d'arrêt
        self.color=color

    #calcul de la seg
    def run(self):
        if not os.path.exists(self.video_path):
            print("Impossible d'ouvrir la vidéo.")
            return

        # output_dir = "segmentation"
        # os.makedirs(output_dir, exist_ok=True)

        video = open_video(self.video_path)
        scene_manager = SceneManager()
        scene_manager.auto_downscale = True #pour réduire la qualité et gagner en temps de calcul
        #scene_manager.add_detector(HistogramDetector())
        if self.color:
            #print("AdaptiveDetector")
            scene_manager.add_detector(AdaptiveDetector())
        else:
            #print("HashDetector")
            scene_manager.add_detector(HashDetector())

        try:
            scene_manager.detect_scenes(video, show_progress=False, callback=self.check_stop)
            scene_list = scene_manager.get_scene_list()

            timecodes = []
            
            # Récupère les timecodes de chaque scène détectée
            # La fin (en frame) d'une scène est définie par la frame de début de la scène suivante - 1
            # Le temps de début et de fin sont calculés à partir des numéros de frame et du framerate de la vidéo
            # Check pour ne pas faire end - 1 sur la dernière scène, sinon on perdrait la dernière frame de la vidéo
            for i, scene in enumerate(scene_list) :

                is_last = i == (len(scene_list) - 1) 

                start_frame = scene[0].get_frames()
                end_frame = scene[1].get_frames() if is_last else scene[1].get_frames() - 1

                start_time = (float(scene[0].frame_num) / scene[0].framerate) * 1000
                end_time = (float(end_frame) / scene[1].framerate) * 1000

                timecodes.append((start_time, end_time, start_frame, end_frame))
            
            #save_images(scene_list,video,num_images=1,output_dir=output_dir)
            
            # Si pas de scène détectée, on considère que la vidéo entière est une seule scène
            if len(timecodes) == 0:
                timecodes.append((0, video.duration.get_seconds() * 1000, 0, video.frame_number))  

            if self.running:
                self.segmentation_done.emit(timecodes)
        except StopProcessingException:
            print("Segmentation interrompue avant la fin.")

    #fonction de callback
    def check_stop(self, frame_number, frame_time: FrameTimecode):
        """Callback appelé à chaque frame pour vérifier si on doit arrêter."""
        if not self.running:
            print("Interruption de la segmentation...")
            raise StopProcessingException("Segmentation interrompue par l'utilisateur.")
        return True  # Continue l'analyse

    #pour stopper l'exécution du calcul de seg
    def stop(self):
        self.running = False
        self.quit()
        self.wait()

class StopProcessingException(Exception):
    pass