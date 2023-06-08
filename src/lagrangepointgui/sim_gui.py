# pylint: disable=no-name-in-module, invalid-name, missing-docstring
import sys
from typing import Callable, Iterable, TypeAlias, TypeVar, cast

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
    QVBoxLayout,
    QWidget,
)

from src.lagrangepointgui.orbit_plotter import Plotter
from src.lagrangepointgui.presets import read_presets as readPresets
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


# pylint: disable=too-many-instance-attributes
class SimUi(QMainWindow):
    def __init__(self, plotter: Plotter):
        super().__init__()

        self._plotter = plotter
        self._plotted = False

        self.setWindowTitle("Orbits near Lagrange Points")

        centralWidget = QWidget(self)
        self.setCentralWidget(centralWidget)

        mainLayout = QVBoxLayout()
        centralWidget.setLayout(mainLayout)

        self._generalLayout = QHBoxLayout()
        self._addInputFields()
        self._generalLayout.addWidget(self._plotter.inertial_plot)
        self._generalLayout.addWidget(self._plotter.corotating_plot)
        mainLayout.addLayout(self._generalLayout)

        conservedPlotsLayout = QHBoxLayout()
        conservedPlotsLayout.addWidget(self._plotter.linear_momentum_plot)
        conservedPlotsLayout.addWidget(self._plotter.angular_momentum_plot)
        conservedPlotsLayout.addWidget(self._plotter.energy_plot)
        mainLayout.addLayout(conservedPlotsLayout)

        self.resize(mainLayout.sizeHint())

    def _addInputFields(self) -> None:
        self.inputFields: dict[str, QLineEdit] = {}
        self._inputsLayout = QFormLayout()
        self._generalLayout.addLayout(self._inputsLayout)

        self.buttons: dict[str, QPushButton] = {}
        self._addButtons()

        self.presetBox = QComboBox()
        presets, _ = readPresets()
        self.presetBox.addItems(presets)
        self._inputsLayout.addRow("Presets", self.presetBox)

        self._addParams("Simulation Parameters", SIM_PARAMS)
        self._addParams("System Parameters", SYS_PARAMS)
        self._addParams("Satellite Parameters", SAT_PARAMS)
        self._addLagrangeLabel()

    def _addButtons(self) -> None:
        buttonsLayout = QHBoxLayout()
        self._inputsLayout.addRow(buttonsLayout)

        for btnText in ("Simulate", "Start/Stop", "Plot Conserved"):
            self.buttons[btnText] = QPushButton(btnText)
            buttonsLayout.addWidget(self.buttons[btnText])

    def _addParams(self, paramCategory: str, params: Params) -> None:
        argLabel = QLabel(paramCategory)
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

    def calcConservedQuantities(self) -> None:
        self._plotter.get_conserved_quantities()

    def plotConservedQuantites(self) -> None:
        if not self._plotted:
            errorMessage("No data to plot.")
            return

        self._plotter.plot_conserved_quantities()


ALL_PARAMS = SIM_PARAMS | SAT_PARAMS | LAGRANGE_PARAM | SYS_PARAMS

# used to translate param labels used in gui to attribute names
PARAM_LABELS_TO_ATTRIBUTE = {paramLabel: attribute for paramLabel, (_, attribute) in ALL_PARAMS.items()}

T = TypeVar("T")


def _translateInputs(inputs: dict[str, T]) -> dict[str, T]:
    return {PARAM_LABELS_TO_ATTRIBUTE[label]: v for label, v in inputs.items()}


class WorkerSignals(QObject):
    finished = pyqtSignal()


class Runnable(QRunnable):
    def __init__(self, expensiveFunc: Callable[[], None]) -> None:
        super().__init__()
        self.expensiveFunc = expensiveFunc
        self.signals = WorkerSignals()

    def run(self) -> None:
        self.expensiveFunc()
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
        btnActions = {
            "Simulate": self._simulate,
            "Start/Stop": self._toggleAnimation,
            "Plot Conserved": self._plotConservedQuantites,
        }
        for btnText, btn in self._view.buttons.items():
            action = btnActions[btnText]
            btn.clicked.connect(action)  # type: ignore

        self._view.presetBox.activated.connect(self._applySelectedPreset)  # type: ignore

    def _applySelectedPreset(self) -> None:
        presetName = self._view.presetBox.currentText()
        self._applyPreset(presetName)

    def _applyPreset(self, presetName: str) -> None:
        preset = readPresets()[0][presetName]
        bases = cast(list[str], preset.get("bases", []))
        for base in bases:
            self._applyPreset(base)

        for paramLabel, value in preset.items():
            if paramLabel == "bases":
                continue

            field = self._view.inputFields[paramLabel]
            field.setText(str(value))

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

        self._simulateThread()

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

    def _simulateThread(self) -> None:
        self._view.stopAnimation()
        self._runExpensiveCalc(self._model.simulate, [self._view.updatePlots])

    def _enableButtons(self) -> None:
        for btn in self._view.buttons.values():
            btn.setEnabled(True)

    def _disableButtons(self) -> None:
        for btn in self._view.buttons.values():
            btn.setEnabled(False)

    def _toggleAnimation(self) -> None:
        self._view.toggleAnimation()

    def _plotConservedQuantites(self) -> None:
        self._runExpensiveCalc(self._view.calcConservedQuantities, [self._view.plotConservedQuantites])

    # noinspection PyUnresolvedReferences
    def _runExpensiveCalc(
        self,
        expensiveCalc: Callable[[], None],
        onFinishFuncs: Iterable[Callable[[], None]] = (),
    ) -> None:
        self._disableButtons()

        runnable = Runnable(expensiveCalc)

        onFinishFuncs = (*onFinishFuncs, self._enableButtons)
        for func in onFinishFuncs:
            runnable.signals.finished.connect(func)

        pool = QThreadPool.globalInstance()
        pool.start(runnable)


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
