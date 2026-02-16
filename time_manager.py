import re

class TimeManager(): 
    def __init__(self,fps=25):
        super().__init__()
        self.fps=fps

    def set_fps(self,new_fps):
        self.fps=new_fps

    def m_to_mst(self,milliseconds):
        """ Formate un temps donné en millisecondes en mm:ss.d """
        total_seconds = milliseconds / 1000
        minutes = int(total_seconds // 60)
        seconds = int(total_seconds % 60)
        tenths = int((total_seconds * 10) % 10)  # Extraction du dixième de seconde
        return f"{minutes:02}'{seconds:02}''{tenths}"

    def s_to_ms(self,seconds):
        """ Formate un temps donné en secondes en mm:ss. """
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02}:{seconds:02}"

    def m_to_hms(self, milliseconds):
        """ Formate un temps donné en millisecondes en hh:mm:ss.d """
        total_seconds = milliseconds / 1000
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        return f"{hours:02},{minutes:02},{seconds:02}"

    def m_to_hmsf(self, milliseconds):
        """ Formate un temps donné en millisecondes en hh:mm:ss:ff """
        total_seconds = milliseconds / 1000
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)

        tf=1000/self.fps
        frame = int((milliseconds % 1000) // tf)
        return f"{hours:02}:{minutes:02}:{seconds:02}[{frame:02}]"

    def frame_to_m(self, frame):
        """Renvoie le temps en millisecondes correspondant à un numéro de frame."""
        return int((frame / self.fps) * 1000)
    
    def hmsf_to_m(time_str, fps):
        tf = 1000/fps
        try:
            hours, minutes, seconds_frames = time_str.split(":")
            seconds, frames = seconds_frames.split("[")
            frames = int(str(frames).replace("]", ""))
            new_time = (int(hours)*3600 + int(minutes) * 60 + int(seconds)) * 1000 + tf * frames
            return new_time
        except ValueError:
            print("Format du timecode invalide. Utilisez le format HH:MM:SS[FF].")
            return  # Si la conversion échoue, on ignore l'entrée

    def m_to_frame(self, milliseconds):
        """Renvoie le numéro de frame correspondant à un temps en millisecondes."""
        return int((milliseconds / 1000) * self.fps)

    def sanitize_timecodename(self, name):
        return re.sub(r'[\\/:*?"<>|]', '-', name)
    
    def timecodename(self, milliseconds):
        return self.sanitize_timecodename(self.m_to_hmsf(milliseconds))