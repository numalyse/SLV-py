from PySide6.QtWidgets import QSlider, QStyle
from PySide6.QtCore import Qt

class CustomSlider(QSlider):

    scribbling = False  # Si l'user/clique glisse la souris

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

        # Provoque une erreur en appelant la méthode originale qui décale de nouveau le slider, qui se décale donc indéfiniment
        # super().mousePressEvent(event)  # Appelle l'événement original

    def mouseMoveEvent(self, event):
        if not self.scribbling:
            return
        self.follow_mouse_click(event)

    def mouseReleaseEvent(self, event):
        self.scribbling = False

