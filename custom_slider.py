from PySide6.QtWidgets import QSlider, QStyle
from PySide6.QtCore import Qt, Signal

class CustomSlider(QSlider):

    scribbling = False  # Si l'user clique et glisse la souris
    slider_mouse_clicked = Signal()
    slider_mouse_released = Signal()  # Signal quand le clic est relâché

    def follow_mouse_click(self, event):
        self.setFocusPolicy(Qt.NoFocus)
        """ Permet de cliquer n'importe où sur la barre pour déplacer le curseur immédiatement """
        if self.orientation() == Qt.Horizontal:
            value = QStyle.sliderValueFromPosition(self.minimum(), self.maximum(), event.pos().x(), self.width())
        else:
            value = QStyle.sliderValueFromPosition(self.minimum(), self.maximum(), event.pos().y(), self.height())

        self.setValue(value)
        self.sliderMoved.emit(value)  # Émet l'événement pour mettre à jour la position

    def mousePressEvent(self, event):
        self.follow_mouse_click(event)
        self.scribbling = True
        self.slider_mouse_clicked.emit() # Mettre en pause la vidéo tant que le slider est bougé

        # Provoque une erreur en appelant la méthode originale qui décale de nouveau le slider, qui se décale donc indéfiniment
        # super().mousePressEvent(event)  # Appelle l'événement original

    def mouseMoveEvent(self, event):
        if not self.scribbling:
            return
        self.follow_mouse_click(event)

    def mouseReleaseEvent(self, event):
        self.scribbling = False
        self.slider_mouse_released.emit()

