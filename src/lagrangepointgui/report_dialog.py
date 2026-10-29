from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLabel, QVBoxLayout, QWidget

from lagrangepointsimulator.analytics import RunSummary


def reportRows(summary: RunSummary, lagrangeLabel: str) -> list[tuple[str, str]]:
    """The (name, value) pairs of the report, with values written the way they are shown."""
    return [
        ("Orbital period of the planet", f"{summary.planet_period:.4f} years"),
        (f"Distance from {lagrangeLabel} at the start", f"{summary.initial_distance:.4g} AU"),
        (f"Distance from {lagrangeLabel} at the end", f"{summary.final_distance:.4g} AU"),
        (
            f"Largest distance from {lagrangeLabel}",
            f"{summary.max_distance:.4g} AU, after {summary.time_of_max_distance:,.2f} years",
        ),
        ("Largest change in energy", f"{summary.max_energy_change:.2e}"),
        ("Largest change in angular momentum", f"{summary.max_angular_momentum_change:.2e}"),
        ("Largest total linear momentum", f"{summary.max_linear_momentum_change:.2e} × the planet's initial momentum"),
    ]


class ReportDialog(QDialog):
    """Shows the summary of the last simulation."""

    def __init__(self, summary: RunSummary, lagrangeLabel: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Report")

        layout = QVBoxLayout(self)

        form = QFormLayout()
        for name, value in reportRows(summary, lagrangeLabel):
            form.addRow(name, QLabel(value))
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
