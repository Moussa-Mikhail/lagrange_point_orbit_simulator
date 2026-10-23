import sys
import traceback
from collections.abc import Callable
from typing import cast

import numpy as np
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

from lagrangepointgui.orbit_plotter import Plotter
from lagrangepointinputs.parameters import (
    DEFAULT_LAGRANGE_LABEL,
    LABEL_TO_ATTRIBUTE,
    LAGRANGE_LABEL,
    LAGRANGE_LABELS,
    PARAMETER_GROUPS,
    Parameter,
)
from lagrangepointinputs.presets import read_presets as readPresets
from lagrangepointinputs.safe_eval import safe_eval as safeEval
from lagrangepointsimulator import Simulator

type Input = str | float | None

SIMULATE = "Simulate"

TOGGLE_ANIMATION = "Toggle Animation"

PLOT_CONSERVED = "Plot Conserved Quantities"

TOGGLE_CONSERVED = "Toggle Conserved Quantity Plots"


class _SimUi(QMainWindow):
    def __init__(self, plotter: Plotter) -> None:
        super().__init__()

        self._plotter = plotter
        self._plotted = False
        self.inputFields: dict[str, QLineEdit] = {}
        self.presetBox = QComboBox()
        self.textToButton: dict[str, QPushButton] = {}
        self.autoPlotConserved = QCheckBox("Auto Plot Conserved")

        self.setWindowTitle("Orbits near Lagrange Points")

        self._centralWidget = QWidget(self)
        self.setCentralWidget(self._centralWidget)

        self._mainLayout = QVBoxLayout()
        self._centralWidget.setLayout(self._mainLayout)

        inputAndOrbitsLayout = QHBoxLayout()
        self._mainLayout.addLayout(inputAndOrbitsLayout)

        self._inputsAndConservedButtonLayout = QVBoxLayout()
        inputAndOrbitsLayout.addLayout(self._inputsAndConservedButtonLayout)

        self._inputsLayout = QFormLayout()
        self._inputsAndConservedButtonLayout.addLayout(self._inputsLayout)

        self._addMainButtons()
        self._addPresetBox()
        self._addInputFields()
        inputAndOrbitsLayout.addWidget(self._plotter.inertial_plot)
        inputAndOrbitsLayout.addWidget(self._plotter.corotating_plot)

        self._addToggleConservedPlotsButton()

        self._conservedPlotsWidget = QWidget(self)
        conservedPlotsLayout = QHBoxLayout()
        self._conservedPlotsWidget.setLayout(conservedPlotsLayout)
        self._mainLayout.addWidget(self._conservedPlotsWidget)

        conservedPlotsLayout.addWidget(self._plotter.linear_momentum_plot)
        conservedPlotsLayout.addWidget(self._plotter.angular_momentum_plot)
        conservedPlotsLayout.addWidget(self._plotter.energy_plot)

        self._hideConservedPlots()

    def _addMainButtons(self) -> None:
        buttonsLayout = QHBoxLayout()
        self._inputsLayout.addRow(buttonsLayout)

        for btnText in (SIMULATE, TOGGLE_ANIMATION, PLOT_CONSERVED):
            self.textToButton[btnText] = QPushButton(btnText)
            buttonsLayout.addWidget(self.textToButton[btnText])

        buttonsLayout.addWidget(self.autoPlotConserved)

    def _addPresetBox(self) -> None:
        presets, _ = readPresets()
        self.presetBox.addItems(presets)

        field = QLineEdit()
        field.setReadOnly(True)

        self.presetBox.setLineEdit(field)

        self._inputsLayout.addRow("Presets", self.presetBox)

    def _addInputFields(self) -> None:
        for paramCategory, params in PARAMETER_GROUPS.items():
            self._addParams(paramCategory, params)

        self._addLagrangeLabel()

    def _addParams(self, paramCategory: str, params: tuple[Parameter, ...]) -> None:
        argLabel = QLabel(paramCategory)
        argLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._inputsLayout.addRow(argLabel)

        for param in params:
            field = QLineEdit(param.default)
            self.inputFields[param.label] = field
            self._inputsLayout.addRow(param.display_label, field)

    def _addToggleConservedPlotsButton(self) -> None:
        conservedPlotsButton = QPushButton(TOGGLE_CONSERVED)
        conservedPlotsButton.setFixedSize(conservedPlotsButton.sizeHint())
        conservedPlotsButton.setContentsMargins(100, 100, 100, 100)

        self._inputsAndConservedButtonLayout.addWidget(conservedPlotsButton)

        self.textToButton[TOGGLE_CONSERVED] = conservedPlotsButton

    def _addLagrangeLabel(self) -> None:
        field = QLineEdit()
        field.setReadOnly(True)

        box = QComboBox()
        box.addItems(LAGRANGE_LABELS)
        box.setCurrentText(DEFAULT_LAGRANGE_LABEL)
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

    def plotConservedQuantities(self) -> None:
        if not self._plotted:
            _displayErrorMessage("No data to plot.")
            return

        self._plotter.plot_conserved_quantities()
        self._showConservedPlots()

    def _showConservedPlots(self) -> None:
        self._conservedPlotsWidget.show()
        self.resize(self._mainLayout.sizeHint())
        self._conservedPlotsIsVisible = True

    def _hideConservedPlots(self) -> None:
        self._conservedPlotsWidget.hide()
        self.resize(self._mainLayout.sizeHint())
        self._conservedPlotsIsVisible = False

    def toggleConservationPlots(self) -> None:
        if self._conservedPlotsIsVisible:
            self._hideConservedPlots()
        else:
            self._showConservedPlots()

    def getInputs(self) -> dict[str, Input]:
        """Get the parameters from the input fields. Returns a dict of parameter label to value.
        Raises a ValueError if any of the numerical fields can't be evaluated.
        """
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


def _translateInputs(inputs: dict[str, Input]) -> dict[str, Input]:
    return {LABEL_TO_ATTRIBUTE[label]: v for label, v in inputs.items()}


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

    # noinspection PyUnresolvedReferences
    def _connectSignals(self) -> None:
        buttonTextToAction = {
            SIMULATE: self._simulate,
            TOGGLE_ANIMATION: self._view.toggleAnimation,
            PLOT_CONSERVED: self._plotConservedQuantities,
            TOGGLE_CONSERVED: self._view.toggleConservationPlots,
        }

        for buttonText, action in buttonTextToAction.items():
            button = self._view.textToButton[buttonText]
            button.clicked.connect(action)

        self._view.presetBox.activated.connect(self._applySelectedPreset)

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
            field.returnPressed.connect(self._simulate)

        lineEdit = self._view.presetBox.lineEdit()
        assert lineEdit
        lineEdit.returnPressed.connect(self._simulate)

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
            for paramLabel, attributeName in LABEL_TO_ATTRIBUTE.items():
                msg = msg.replace(attributeName, paramLabel)

            _displayErrorMessage(msg)
            return

        self._view.stopAnimation()
        onFinishFuncs: list[Callable[[], None]] = [self._view.updateOrbitPlots]
        if self._view.autoPlotConserved.isChecked():
            onFinishFuncs.append(self._plotConservedQuantities)

        self._disableButtons()
        self._runInThread(self._model.simulate, onFinishFuncs)

    def _enableButtons(self) -> None:
        for btn in self._view.textToButton.values():
            btn.setEnabled(True)

    def _disableButtons(self) -> None:
        for btn in self._view.textToButton.values():
            btn.setEnabled(False)

    def _disableButtonsExceptToggleAnimation(self) -> None:
        for btnText, btn in self._view.textToButton.items():
            if btnText == TOGGLE_ANIMATION:
                continue

            btn.setEnabled(False)

    def _plotConservedQuantities(self) -> None:
        self._disableButtonsExceptToggleAnimation()
        self._runInThread(self._view.calcConservedQuantities, [self._view.plotConservedQuantities])

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


def _selfTest(view: _SimUi) -> None:
    """Check that the app has what it needs to work. Used to smoke test packaged builds."""
    if view.presetBox.count() == 0:
        msg = "no presets were loaded"
        raise RuntimeError(msg)

    sim = Simulator()
    for attribute, value in _translateInputs(view.getInputs()).items():
        setattr(sim, attribute, value)

    sim.num_years = 0.1
    sim.simulate()

    if not np.isfinite(sim.sat_pos).all():
        msg = "simulation produced non-finite positions"
        raise RuntimeError(msg)


def main() -> None:
    # The flag is for builds without a console, so the result is only reported through the exit code.
    selfTesting = "--self-test" in sys.argv
    if selfTesting:
        sys.argv.remove("--self-test")

    simApp = QApplication(sys.argv)
    simApp.setFont(QFont("Arial", 13))
    simApp.setStyle("fusion")

    sim = Simulator()
    plotter = Plotter(sim)
    view = _SimUi(plotter)

    if selfTesting:
        try:
            _selfTest(view)
        except Exception:  # noqa: BLE001
            traceback.print_exc()
            sys.exit(1)

        sys.exit(0)

    view.show()

    _ = _SimCtrl(sim, view)

    sys.exit(simApp.exec())


if __name__ == "__main__":
    main()
