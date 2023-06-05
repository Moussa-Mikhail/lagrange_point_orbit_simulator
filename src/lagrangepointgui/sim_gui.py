# pylint: disable=no-name-in-module, invalid-name, missing-docstring
import sys
from typing import Callable, TypeAlias, TypeVar

from PyQt6.QtCore import QObject, QRunnable, QThreadPool, Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QErrorMessage,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QWidget,
)

from src.lagrangepointgui.orbit_plotter import Plotter
from src.lagrangepointgui.safe_eval import safe_eval as safeEval
from src.lagrangepointsimulator import Simulator

LAGRANGE_LABEL = "Lagrange label"

Params: TypeAlias = dict[str, tuple[str, str]]

# parameter name: (default value, attribute name)
SIM_PARAMS: Params = {
    "number of years": ("10.0", "num_years"),
    "time step (hours)": ("1.0", "time_step"),
}

SAT_PARAMS: Params = {
    "perturbation size": ("0.0", "perturbation_size"),
    "perturbation angle": ("", "perturbation_angle"),
    "initial speed": ("1.0", "speed"),
    "initial velocity angle": ("", "vel_angle"),
}

LAGRANGE_PARAM: Params = {LAGRANGE_LABEL: ("L4", "lagrange_label")}

SYS_PARAMS: Params = {
    "star mass": ("sun_mass", "star_mass"),
    "planet mass": ("earth_mass", "planet_mass"),
    "planet distance": ("1.0", "planet_distance"),
}


class SimUi(QMainWindow):
    def __init__(self, plotter: Plotter):
        super().__init__()

        self._plotter = plotter
        self._plotted = False

        self.setWindowTitle("Orbits near Lagrange Point")

        self._centralWidget = QWidget(self)
        self.setCentralWidget(self._centralWidget)
        self._generalLayout = QHBoxLayout()
        self._centralWidget.setLayout(self._generalLayout)

        self.inputFields: dict[str, QLineEdit] = {}
        self._addInputFields()

        self._generalLayout.addWidget(self._plotter.inertial_plot)
        self._generalLayout.addWidget(self._plotter.corotating_plot)
        self.resize(self._generalLayout.sizeHint())

    def _addInputFields(self) -> None:
        self._inputsLayout = QFormLayout()

        self.buttons: dict[str, QPushButton] = {}
        self._addButtons()

        self._addParams("Simulation Parameters", SIM_PARAMS)
        self._addParams("System Parameters", SYS_PARAMS)
        self._addParams("Satellite Parameters", SAT_PARAMS)
        self._addLagrangeLabel()

        self._generalLayout.addLayout(self._inputsLayout)

    def _addButtons(self) -> None:
        buttonsLayout = QHBoxLayout()
        for btnText in ("Simulate", "Start/Stop"):
            self.buttons[btnText] = QPushButton(btnText)
            buttonsLayout.addWidget(self.buttons[btnText])

        self._inputsLayout.addRow(buttonsLayout)

    def _addParams(self, argLabelText: str, params: Params) -> None:
        argLabel = QLabel(argLabelText)
        argLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._inputsLayout.addRow(argLabel)

        for fieldText, (defaultValue, _) in params.items():
            fieldLine = QLineEdit(defaultValue)
            self.inputFields[fieldText] = fieldLine
            self._inputsLayout.addRow(fieldText, fieldLine)

    def _addLagrangeLabel(self) -> None:
        fieldText = LAGRANGE_LABEL
        defaultValue = LAGRANGE_PARAM[fieldText][0]
        fieldLine = QLineEdit()
        fieldLine.setReadOnly(True)

        box = QComboBox()
        box.addItems([f"L{i}" for i in range(1, 6)])
        box.setCurrentText(defaultValue)
        box.setLineEdit(fieldLine)

        self.inputFields[fieldText] = fieldLine
        self._inputsLayout.addRow(fieldText, box)

    def updatePlots(self) -> None:
        self._plotted = True
        self._plotter.plot_orbits()

    def toggleAnimation(self) -> None:
        if not self._plotted:
            errorMessage("No plots to animate.")
            return

        self._plotter.toggle_animation()

    def stopAnimation(self) -> None:
        self._plotter.stop_animation()


ALL_PARAMS = SIM_PARAMS | SAT_PARAMS | LAGRANGE_PARAM | SYS_PARAMS

# used to translate param labels used in gui to attribute names
PARAM_LABELS_TO_ATTRIBUTE = {paramLabel: attribute for paramLabel, (_, attribute) in ALL_PARAMS.items()}

T = TypeVar("T")


def _translateInputs(inputs: dict[str, T]) -> dict[str, T]:
    return {PARAM_LABELS_TO_ATTRIBUTE[label]: v for label, v in inputs.items()}


class WorkerSignals(QObject):
    finished = pyqtSignal()


class Runnable(QRunnable):
    def __init__(self, simulate: Callable[[], None]) -> None:
        super().__init__()
        self.simulate = simulate
        self.signals = WorkerSignals()

    def run(self) -> None:
        self.simulate()
        # noinspection PyUnresolvedReferences
        self.signals.finished.emit()


class SimCtrl:  # pylint: disable=too-few-public-methods
    def __init__(
        self,
        model: Simulator,
        view: SimUi,
    ):
        self._model = model
        self._view = view
        self._connectSignals()
        self._addReturnPressed()

    def _connectSignals(self) -> None:
        btnActions = {"Simulate": self._simulate, "Start/Stop": self._toggleAnimation}
        for btnText, btn in self._view.buttons.items():
            action = btnActions[btnText]
            btn.clicked.connect(action)  # type: ignore

    def _addReturnPressed(self) -> None:
        for field in self._view.inputFields.values():
            field.returnPressed.connect(self._simulate)  # type: ignore

    def _simulate(self) -> None:
        try:
            simulationInputs = self._getSimParams()

        except ValueError as e:
            errorMessage(str(e))
            return

        translatedInputs = _translateInputs(simulationInputs)

        try:
            for attr, value in translatedInputs.items():
                setattr(self._model, attr, value)

        except (TypeError, ValueError) as e:
            msg = str(e)
            for paramLabel, attr in PARAM_LABELS_TO_ATTRIBUTE.items():
                msg = msg.replace(attr, paramLabel)

            errorMessage(msg)
            return

        self._simulate_thread()

    def _getSimParams(self) -> dict[str, str | float | None]:
        inputs: dict[str, str | float | None] = {}
        for fieldText, field in self._view.inputFields.items():
            fieldValue = field.text()

            if fieldText == LAGRANGE_LABEL:
                inputs[fieldText] = fieldValue
                continue
            try:
                value = safeEval(fieldValue)

            except ValueError as e:
                raise ValueError(f"Invalid expression in field '{fieldText}'.\n{e}") from e

            inputs[fieldText] = value

        return inputs

    # noinspection PyUnresolvedReferences
    def _simulate_thread(self) -> None:
        runnable = Runnable(self._model.simulate)
        runnable.signals.finished.connect(self._view.updatePlots)
        buttons = self._view.buttons
        runnable.signals.finished.connect(self._enableButtons)
        for btn in buttons.values():
            btn.setEnabled(False)
        self._view.stopAnimation()

        pool = QThreadPool.globalInstance()
        pool.start(runnable)

    def _enableButtons(self) -> None:
        for btn in self._view.buttons.values():
            btn.setEnabled(True)

    def _toggleAnimation(self) -> None:
        self._view.toggleAnimation()


def errorMessage(message: str) -> None:
    errorMsg = QErrorMessage()
    errorMsg.showMessage(message)
    errorMsg.exec()


def main() -> None:
    simApp = QApplication(sys.argv)
    simApp.setFont(QFont("Arial", 10))

    sim = Simulator()
    plotter = Plotter(sim)
    view = SimUi(plotter)
    view.show()

    _ = SimCtrl(sim, view)

    sys.exit(simApp.exec())


if __name__ == "__main__":
    main()
