import json
import os
from pathlib import Path

class PreferenceManager:
    def __init__(self, parent, filename="config.json"):
        self.parent = parent
        self.dir = Path.home() / "SLV_Content"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.filename = filename
        self.filepath = self.dir / self.filename
        self.default_preferences = {
            "format_capture": False,
            "post_traitement": False,
            "gamma":1.4,
            "format_export_text": [False, False, True, False]
        }
        self.load_preferences()

    def load_preferences(self):
        if self.filepath.exists():
            try:
                with open(self.filepath, "r") as f:
                    preferences = json.load(f)
            except (json.JSONDecodeError, IOError):
                print("Erreur lecture —> valeurs par défaut utilisées")
                preferences = self.default_preferences
        else:
            print("Aucun fichier trouvé —> création d’un nouveau avec les valeurs par défaut")
            preferences = self.default_preferences
            self.save_preferences()

        for key, value in preferences.items():
            setattr(self.parent, key, value)

    def save_preferences(self):
        preferences = {
            "format_capture": getattr(self.parent, "format_capture", False),
            "post_traitement": getattr(self.parent, "post_traitement", False),
            "gamma": getattr(self.parent, "gamma", 1.4),
            "format_export_text": getattr(self.parent, "format_export_text", [False, False, True, False])
        }

        try:
            with open(self.filepath, "w") as f:
                json.dump(preferences, f, indent=4)
            print(f"Préférences sauvegardées dans : {self.filepath}")
        except IOError as e:
            print(f"Erreur lors de la sauvegarde : {e}")
