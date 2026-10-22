from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from lagrangepointinputs import user_presets


class PresetFileDialog(QDialog):
    """Edits the text of the user's presets file. Saving is refused, with the reason shown, while it's invalid."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Edit presets")
        self.resize(720, 480)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(f"Your presets and constants, stored in\n{user_presets.presets.user_presets_path}"))

        self.editor = QPlainTextEdit(user_presets.read_text() or user_presets.EXAMPLE_TEXT)
        self.editor.setFont(QFont("monospace"))
        self.editor.setTabStopDistance(32)
        layout.addWidget(self.editor)

        self.errorLabel = QLabel()
        self.errorLabel.setStyleSheet("color: #c0392b")
        self.errorLabel.setWordWrap(True)
        layout.addWidget(self.errorLabel)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _save(self) -> None:
        try:
            user_presets.save_text(self.editor.toPlainText())
        except user_presets.PresetError as e:
            self.errorLabel.setText(str(e))
            return

        self.accept()
