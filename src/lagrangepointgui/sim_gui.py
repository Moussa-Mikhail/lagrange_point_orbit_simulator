import sys
import time
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import cast

import numpy as np
from PyQt6.QtCore import QObject, QRunnable, Qt, QThreadPool, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QErrorMessage,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from lagrangepointgui.orbit_plotter import Plotter
from lagrangepointgui.preset_dialogs import PresetFileDialog
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
from lagrangepointinputs.user_presets import (
    EXAMPLE_TEXT,
    PresetError,
    delete_preset,
    read_text,
    save_preset,
    save_text,
    user_preset_names,
)
from lagrangepointsimulator import Simulator

type Input = str | float | None

SIMULATE = "Simulate"

SAVE_PRESET = "Save…"

DELETE_PRESET = "Delete"

EDIT_PRESETS = "Edit…"

EXPORT_PRESETS = "Export"

IMPORT_PRESETS = "Import…"

PRESETS_FILE_NAME = "user_presets.toml"

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
        self.textToPresetButton: dict[str, QPushButton] = {}
        self.autoPlotConserved = QCheckBox("Auto Plot Conserved")
        self.statusLabel = QLabel()

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
        field = QLineEdit()
        field.setReadOnly(True)

        self.presetBox.setLineEdit(field)
        self.refreshPresets()

        self._inputsLayout.addRow("Presets", self.presetBox)

        presetButtonsLayout = QHBoxLayout()
        for btnText in (SAVE_PRESET, DELETE_PRESET, EDIT_PRESETS, EXPORT_PRESETS, IMPORT_PRESETS):
            self.textToPresetButton[btnText] = QPushButton(btnText)
            presetButtonsLayout.addWidget(self.textToPresetButton[btnText])

        self._inputsLayout.addRow(presetButtonsLayout)
        self.updateDeleteButton()

    def refreshPresets(self, selected: str | None = None) -> None:
        """Reload the list of presets, keeping the current one selected unless selected is given."""
        selected = selected or self.presetBox.currentText()

        presets, _ = readPresets()
        self.presetBox.clear()
        self.presetBox.addItems(presets)
        if selected in presets:
            self.presetBox.setCurrentText(selected)

    def updateDeleteButton(self) -> None:
        """Only the user's own presets can be deleted."""
        self.textToPresetButton[DELETE_PRESET].setEnabled(self.presetBox.currentText() in user_preset_names())

    def getInputTexts(self) -> dict[str, str]:
        """The text of every input field as it is written, e.g. to store it as a preset."""
        return {label: field.text() for label, field in self.inputFields.items()}

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

        buttonAndStatusLayout = QHBoxLayout()
        buttonAndStatusLayout.addWidget(conservedPlotsButton)
        buttonAndStatusLayout.addWidget(self.statusLabel, 1)
        self._inputsAndConservedButtonLayout.addLayout(buttonAndStatusLayout)

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

    def setStatus(self, text: str) -> None:
        self.statusLabel.setText(text)

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
        self._view.presetBox.currentTextChanged.connect(self._view.updateDeleteButton)

        presetButtonTextToAction = {
            SAVE_PRESET: self._savePreset,
            DELETE_PRESET: self._deletePreset,
            EDIT_PRESETS: self._editPresets,
            EXPORT_PRESETS: self._exportPresets,
            IMPORT_PRESETS: self._importPresets,
        }

        for buttonText, action in presetButtonTextToAction.items():
            self._view.textToPresetButton[buttonText].clicked.connect(action)

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

    def _savePreset(self) -> None:
        current = self._view.presetBox.currentText()
        name, accepted = QInputDialog.getText(
            self._view,
            "Save preset",
            "Save the values in the fields as the preset:",
            text=current if current in user_preset_names() else "",
        )
        name = name.strip()
        if not accepted or not name:
            return

        if name in readPresets()[0]:
            kind = "one of your presets" if name in user_preset_names() else "a built-in preset"
            question = f"'{name}' is {kind}. Replace it?"
            if QMessageBox.question(self._view, "Replace preset", question) != QMessageBox.StandardButton.Yes:
                return

        try:
            save_preset(name, self._view.getInputTexts())
        except PresetError as e:
            _displayErrorMessage(str(e))
            return

        self._view.refreshPresets(name)

    def _deletePreset(self) -> None:
        name = self._view.presetBox.currentText()
        if (
            QMessageBox.question(self._view, "Delete preset", f"Delete the preset '{name}'?")
            != QMessageBox.StandardButton.Yes
        ):
            return

        try:
            delete_preset(name)
        except PresetError as e:
            _displayErrorMessage(str(e))
            return

        self._view.refreshPresets()
        self._view.updateDeleteButton()

    def _editPresets(self) -> None:
        if PresetFileDialog(self._view).exec():
            self._view.refreshPresets()
            self._view.updateDeleteButton()

    def _exportPresets(self) -> None:
        fileName, _ = QFileDialog.getSaveFileName(
            self._view, "Export presets", PRESETS_FILE_NAME, "TOML files (*.toml)"
        )
        if not fileName:
            return

        try:
            Path(fileName).write_text(read_text() or EXAMPLE_TEXT, encoding="utf-8")
        except OSError as e:
            _displayErrorMessage(str(e))

    def _importPresets(self) -> None:
        fileName, _ = QFileDialog.getOpenFileName(
            self._view, "Import presets", "", "TOML files (*.toml);;All files (*)"
        )
        if not fileName:
            return

        question = f"Replace your presets with the contents of {Path(fileName).name}?"
        if QMessageBox.question(self._view, "Import presets", question) != QMessageBox.StandardButton.Yes:
            return

        try:
            save_text(Path(fileName).read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, PresetError) as e:
            _displayErrorMessage(str(e))
            return

        self._view.refreshPresets()
        self._view.updateDeleteButton()

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
        self._view.setStatus("Simulating…")
        start = time.perf_counter()
        onFinishFuncs: list[Callable[[], None]] = [self._view.updateOrbitPlots, lambda: self._reportSimulated(start)]
        if self._view.autoPlotConserved.isChecked():
            onFinishFuncs.append(self._plotConservedQuantities)

        self._disableButtons()
        self._runInThread(self._model.simulate, onFinishFuncs)

    def _reportSimulated(self, start: float) -> None:
        self._view.setStatus(f"Simulated {self._model.num_steps:,} steps in {time.perf_counter() - start:.2f} s")

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
