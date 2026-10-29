from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLabel, QVBoxLayout, QWidget

from lagrangepointsimulator.analytics import RunSummary


class ReportDialog(QDialog):
    """Shows the summary of the last simulation."""

    def __init__(self, summary: RunSummary, lagrangeLabel: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Report")

        layout = QVBoxLayout(self)

        form = QFormLayout()
        for name, value in summary.rows(lagrangeLabel):
            form.addRow(name, QLabel(value))
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
