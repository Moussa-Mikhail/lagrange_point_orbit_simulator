# ruff: noqa: N802 N803 N806 N812
import sys
from collections.abc import Callable
from typing import TypeAlias, cast

from PyQt6.QtCore import QObject, QRunnable, Qt, QThreadPool, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
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

# parameter label in gui: (default value, attribute name in Simulator
SIMULATION_PARAMS: Params = {
    "number of years": ("10.0", "num_years"),
    "time step (hours)": ("1.0", "time_step"),
}

SATELLITE_PARAMS: Params = {
    "perturbation size": ("0.0", "perturbation_size"),
    "perturbation angle": ("", "perturbation_angle"),
    "initial speed": ("1.0", "speed"),
    "initial velocity angle": ("", "vel_angle"),
}

LAGRANGE_PARAM: Params = {LAGRANGE_LABEL: ("L4", "lagrange_label")}

SYSTEM_PARAMS: Params = {
    "star mass": ("sun_mass", "star_mass"),
    "planet mass": ("earth_mass", "planet_mass"),
    "planet distance": ("1.0", "planet_distance"),
}

Input: TypeAlias = str | float | None

SIMULATE = "Simulate"

TOGGLE_ANIMATION = "Toggle Animation"

PLOT_CONSERVED = "Plot Conserved Quantities"


class _SimUi(QMainWindow):
    def __init__(self, plotter: Plotter) -> None:
        super().__init__()

        self._plotter = plotter
        self._plotted = False
        self.inputFields: dict[str, QLineEdit] = {}
        self.presetBox = QComboBox()
        self.buttons: dict[str, QPushButton] = {}
        self.autoPlotConserved = QCheckBox("Auto Plot Conserved")

        self.setWindowTitle("Orbits near Lagrange Points")

        centralWidget = QWidget(self)
        self.setCentralWidget(centralWidget)

        mainLayout = QVBoxLayout()
        centralWidget.setLayout(mainLayout)

        inputAndOrbitsLayout = QHBoxLayout()
        mainLayout.addLayout(inputAndOrbitsLayout)

        self._inputsLayout = QFormLayout()
        inputAndOrbitsLayout.addLayout(self._inputsLayout)
        self._addButtons()
        self._addPresetBox()
        self._addInputFields()
        inputAndOrbitsLayout.addWidget(self._plotter.inertial_plot)
        inputAndOrbitsLayout.addWidget(self._plotter.corotating_plot)

        conservedPlotsLayout = QHBoxLayout()
        mainLayout.addLayout(conservedPlotsLayout)

        conservedPlotsLayout.addWidget(self._plotter.linear_momentum_plot)
        conservedPlotsLayout.addWidget(self._plotter.angular_momentum_plot)
        conservedPlotsLayout.addWidget(self._plotter.energy_plot)

        self.resize(mainLayout.sizeHint())

    def _addButtons(self) -> None:
        buttonsLayout = QHBoxLayout()
        self._inputsLayout.addRow(buttonsLayout)

        for btnText in (SIMULATE, TOGGLE_ANIMATION, PLOT_CONSERVED):
            self.buttons[btnText] = QPushButton(btnText)
            buttonsLayout.addWidget(self.buttons[btnText])

        buttonsLayout.addWidget(self.autoPlotConserved)

    def _addPresetBox(self) -> None:
        presets, _ = readPresets()
        self.presetBox.addItems(presets)

        field = QLineEdit()
        field.setReadOnly(True)

        self.presetBox.setLineEdit(field)

        self._inputsLayout.addRow("Presets", self.presetBox)

    def _addInputFields(self) -> None:
        self._addParams("Simulation Parameters", SIMULATION_PARAMS)
        self._addParams("System Parameters", SYSTEM_PARAMS)
        self._addParams("Satellite Parameters", SATELLITE_PARAMS)
        self._addLagrangeLabel()

    def _addParams(self, paramCategory: str, params: Params) -> None:
        argLabel = QLabel(paramCategory)
        argLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._inputsLayout.addRow(argLabel)

        for fieldLabel, (defaultValue, _) in params.items():
            field = QLineEdit(defaultValue)
            self.inputFields[fieldLabel] = field
            self._inputsLayout.addRow(fieldLabel, field)

    def _addLagrangeLabel(self) -> None:
        defaultValue = LAGRANGE_PARAM[LAGRANGE_LABEL][0]
        field = QLineEdit()
        field.setReadOnly(True)

        box = QComboBox()
        box.addItems([f"L{i}" for i in range(1, 6)])
        box.setCurrentText(defaultValue)
        box.setLineEdit(field)

        self.inputFields[LAGRANGE_LABEL] = field
        self._inputsLayout.addRow(LAGRANGE_LABEL, box)

    def updateOrbitPlots(self) -> None:
        self._plotted = True
        self._plotter.plot_orbit_inertial_and_corotating()

    def toggleAnimation(self) -> None:
        if not self._plotted:
            _displayErrorMessage("No plots to animate.")
            return

        self._plotter.toggle_animation()

    def stopAnimation(self) -> None:
        self._plotter.stop_animation()

    def calcConservedQuantities(self) -> None:
        self._plotter.get_conserved_quantities()

    def plotConservedQuantites(self) -> None:
        if not self._plotted:
            _displayErrorMessage("No data to plot.")
            return

        self._plotter.plot_conserved_quantities()

    def getInputs(self) -> dict[str, Input]:
        """Get the parameters from the input fields. Returns a dict of parameter label to value.
        Raises a ValueError if any of the numerical fields can't be evaluated."""
        inputs: dict[str, Input] = {}
        for fieldLabel, field in self.inputFields.items():
            fieldText = field.text()

            if fieldLabel == LAGRANGE_LABEL:
                inputs[fieldLabel] = fieldText
                continue

            try:
                value = safeEval(fieldText)
            except (ValueError, TypeError) as e:
                msg = f"Invalid expression in field '{fieldLabel}'.\n{e}"
                raise ValueError(msg) from e

            inputs[fieldLabel] = value

        return inputs


ALL_PARAMS = SIMULATION_PARAMS | SATELLITE_PARAMS | LAGRANGE_PARAM | SYSTEM_PARAMS

# used to translate param labels used in gui to attribute names in simulator class
PARAM_LABEL_TO_ATTRIBUTE_NAME = {paramLabel: attribute for paramLabel, (_, attribute) in ALL_PARAMS.items()}


def _translateInputs(inputs: dict[str, Input]) -> dict[str, Input]:
    return {PARAM_LABEL_TO_ATTRIBUTE_NAME[label]: v for label, v in inputs.items()}


class WorkerSignals(QObject):
    finished = pyqtSignal()


class ExpensiveFuncRunner(QRunnable):
    def __init__(self, expensiveFunc: Callable[[], None]) -> None:
        super().__init__()
        self.expensiveFunc = expensiveFunc
        self.signals = WorkerSignals()

    def run(self) -> None:
        self.expensiveFunc()
        # noinspection PyUnresolvedReferences
        self.signals.finished.emit()


class _SimCtrl:
    def __init__(self, model: Simulator, view: _SimUi) -> None:
        self._model = model
        self._view = view
        self._connectSignals()
        self._addReturnPressed()
        self._calculating = False

    def _connectSignals(self) -> None:
        btnActions = {
            SIMULATE: self._simulate,
            TOGGLE_ANIMATION: self._toggleAnimation,
            PLOT_CONSERVED: self._plotConservedQuantites,
        }
        for btnText, btn in self._view.buttons.items():
            action = btnActions[btnText]
            btn.clicked.connect(action)  # type: ignore

        self._view.presetBox.activated.connect(self._applySelectedPreset)  # type: ignore

    def _applySelectedPreset(self) -> None:
        presetName = self._view.presetBox.currentText()
        self._applyPreset(presetName)

    def _applyPreset(self, presetName: str) -> None:
        presets, _ = readPresets()
        preset = presets[presetName]
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

        self._view.presetBox.lineEdit().returnPressed.connect(self._simulate)  # type: ignore

    def _simulate(self) -> None:
        if self._calculating:
            return

        try:
            paramLabelToValue = self._view.getInputs()

        except ValueError as e:
            _displayErrorMessage(str(e))
            return

        attributeNameToValue = _translateInputs(paramLabelToValue)

        try:
            for attributeName, value in attributeNameToValue.items():
                setattr(self._model, attributeName, value)

        except (TypeError, ValueError) as e:
            msg = str(e)
            # replace attribute names with parameter labels
            for paramLabel, attributeName in PARAM_LABEL_TO_ATTRIBUTE_NAME.items():
                msg = msg.replace(attributeName, paramLabel)

            _displayErrorMessage(msg)
            return

        self._view.stopAnimation()
        onFinishFuncs = [self._view.updateOrbitPlots]
        if self._view.autoPlotConserved.isChecked():
            onFinishFuncs.append(self._plotConservedQuantites)

        self._disableButtons()
        self._runInThread(self._model.simulate, onFinishFuncs)

    def _enableButtons(self) -> None:
        for btn in self._view.buttons.values():
            btn.setEnabled(True)

    def _disableButtons(self) -> None:
        for btn in self._view.buttons.values():
            btn.setEnabled(False)

    def _disableButtonsExceptToggleAnimation(self) -> None:
        for btnText, btn in self._view.buttons.items():
            if btnText == TOGGLE_ANIMATION:
                continue

            btn.setEnabled(False)

    def _toggleAnimation(self) -> None:
        self._view.toggleAnimation()

    def _plotConservedQuantites(self) -> None:
        self._disableButtonsExceptToggleAnimation()
        self._runInThread(self._view.calcConservedQuantities, [self._view.plotConservedQuantites])

    # noinspection PyUnresolvedReferences
    def _runInThread(self, expensiveFunc: Callable[[], None], onFinishFuncs: list[Callable[[], None]]) -> None:
        """Run an expensive function in a separate thread."""
        runnable = ExpensiveFuncRunner(expensiveFunc)

        runnable.signals.finished.connect(self._enableButtons)
        runnable.signals.finished.connect(self._setCalculatingFalse)
        for onFinishFunc in onFinishFuncs:
            runnable.signals.finished.connect(onFinishFunc)

        if not (pool := QThreadPool.globalInstance()):
            msg = "Unable to find thread pool."
            raise RuntimeError(msg)
        pool.start(runnable)
        self._calculating = True

    def _setCalculatingFalse(self) -> None:
        self._calculating = False


def _displayErrorMessage(message: str) -> None:
    """Display an error message in a dialog box."""
    errorMsg = QErrorMessage()
    errorMsg.showMessage(message)
    errorMsg.exec()


def main() -> None:
    simApp = QApplication(sys.argv)
    simApp.setFont(QFont("Arial", 13))
    simApp.setStyle("fusion")

    sim = Simulator()
    plotter = Plotter(sim)
    view = _SimUi(plotter)
    view.show()

    _ = _SimCtrl(sim, view)

    sys.exit(simApp.exec())


if __name__ == "__main__":
    main()
