from PySide6.QtWidgets import QWidget, QLayout, QLineEdit, QStyle, QPushButton, QHBoxLayout, QSpacerItem, QSizePolicy
from PySide6.QtCore import Qt, Signal, QEvent
from time_manager import TimeManager

class CustomTimestampEdit(QWidget):
    
    focus_in = Signal()
    focus_out = Signal()
    value_changed = Signal()
    edit_finished = Signal()
    is_focused = False

    def __init__(self, parent=None, max_time = 3600000, fps = 25):
        super().__init__(parent)
        self.timestamp_edit = QLineEdit()
        self.ok_button = QPushButton("OK") # peut-être un NoFocusPushButton
        self.ok_button.setFixedWidth(40)
        self.setFixedWidth(120)
        self.timestamp_edit.setText("00:00:00[00]")
        # self.timestamp_edit.setAlignment(Qt.AlignCenter)
        self.timestamp_edit.setAlignment(Qt.AlignLeft)
        self.timestamp_edit.setFixedWidth(80)
        self.timestamp_edit.setFocusPolicy(Qt.ClickFocus)
        self.max_time = max_time
        self.fps = fps
        
        h_layout = QHBoxLayout(self)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(0)
        h_layout.addWidget(self.timestamp_edit)
        h_layout.addWidget(self.ok_button)
        # Spacer pour éviter le décalage dans le layout
        self.ok_button_spacer = QSpacerItem(40, 0, QSizePolicy.Fixed, QSizePolicy.Minimum)
        h_layout.addItem(self.ok_button_spacer)
        
        self.setLayout(h_layout)
        self.timestamp_edit.textChanged.connect(self.on_value_changed)
        
        
        self.timestamp_edit.installEventFilter(self)
        self.ok_button.hide()

    # Ne marche pas en passant par focusInEvent/focusOutEvent
    def eventFilter(self, obj, event):
        """ Filtre les événements du QLineEdit """
        if obj == self.timestamp_edit:

            # Quand le timestamp est focus
            if event.type() == QEvent.FocusIn:
                self.focus_in.emit()
                self.ok_button.show()
                self.is_focused = True
                self.ok_button_spacer.changeSize(0, 0)
                self.layout().invalidate()
                return False
            
            # Quand le timestamp perd le focus
            elif event.type() == QEvent.FocusOut:
                self.finish_edit()
                return False
            
            elif event.type() == QEvent.KeyPress:
                if event.key() in (Qt.Key_Enter, Qt.Key_Return):
                    self.finish_edit()
                    self.timestamp_edit.clearFocus()
                    return True
            
        return super().eventFilter(obj, event)
    
    def finish_edit(self):
        self.focus_out.emit()
        self.ok_button.hide()
        self.is_focused = False
        self.ok_button_spacer.changeSize(40, 0)
        self.layout().invalidate()
        self.edit_finished.emit()

    def set_text(self, text):
        self.timestamp_edit.setText(text)
    
    def get_time_str(self):
        return self.timestamp_edit.text()
    
    def on_value_changed(self):
        self.value_changed.emit()

    def on_button_clicked(self):
        self.edit_finished.emit()
