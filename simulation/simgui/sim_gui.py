# pylint: disable=no-name-in-module, invalid-name, missing-docstring, attribute-defined-outside-init
import sys
from typing import TypeVar

import pyqtgraph as pg  # type: ignore
from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from simulation import Simulator

from simulation.constants import safe_eval as safeEval

simParams = {
    "number of years": "10",
    "number of steps": "10**5",
}

satParams = {
    "perturbation size": "0",
    "perturbation angle": "60",
    "initial speed": "1",
    "initial velocity angle": "150",
    "Lagrange label": "L4",
}

sysParams = {
    "star mass": "sun_mass",
    "planet mass": "earth_mass",
    "planet distance": "1.0",
}

# used to translate param labels used in gui to arg names used in simMain
argNames = {
    "number of steps": "num_steps",
    "number of years": "num_years",
    "time step": "time_step",
    "perturbation size": "perturbation_size",
    "perturbation angle": "perturbation_angle",
    "initial speed": "speed",
    "initial velocity angle": "vel_angle",
    "star mass": "star_mass",
    "planet mass": "planet_mass",
    "planet distance": "planet_distance",
    "Lagrange label": "lagrange_label",
}


class SimUi(QtWidgets.QMainWindow):
    def __init__(self):

        super().__init__()

        self.setWindowTitle("Simulation of Orbits near Lagrange Points")

        self._generalLayout = QtWidgets.QHBoxLayout()

        self._centralWidget = QtWidgets.QWidget(self)

        self.setCentralWidget(self._centralWidget)

        self._centralWidget.setLayout(self._generalLayout)

        self.inputFields: dict[str, QtWidgets.QLineEdit] = {}

        self._addInputFields()

        self._initializePlots()

    def _addInputFields(self):

        self._inputsLayout = QtWidgets.QFormLayout()

        self.buttons: dict[str, QtWidgets.QPushButton] = {}

        self._addButtons()

        self._addParams("Simulation Parameters", simParams)

        self._addParams("Satellite Parameters", satParams)

        self._addParams("System Parameters", sysParams)

        self._generalLayout.addLayout(self._inputsLayout)

    def _addButtons(self):

        buttons = ("Simulate", "Start/Stop")

        buttonsLayout = QtWidgets.QHBoxLayout()

        for btnText in buttons:

            self.buttons[btnText] = QtWidgets.QPushButton(btnText)

            buttonsLayout.addWidget(self.buttons[btnText])

        self._inputsLayout.addRow(buttonsLayout)

    def _addParams(self, argLabelText: str, Params: dict[str, str]):

        argLabel = QtWidgets.QLabel(argLabelText)

        argLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._inputsLayout.addRow(argLabel)

        for fieldText, defaultValue in Params.items():

            fieldLine = QtWidgets.QLineEdit(defaultValue)

            self.inputFields[fieldText] = fieldLine

            self._inputsLayout.addRow(fieldText, fieldLine)

    def _initializePlots(self):

        orbitPlot = pg.plot(title="Orbits of Masses")
        orbitPlot.setLabel("bottom", "x", units="AU")
        orbitPlot.setLabel("left", "y", units="AU")

        corotatingPlot = pg.plot(title="Orbits in Co-Rotating Coordinate System")
        corotatingPlot.setLabel("bottom", "x", units="AU")
        corotatingPlot.setLabel("left", "y", units="AU")

        self._orbitPlot = orbitPlot

        self._corotatingPlot = corotatingPlot

        self._generalLayout.addWidget(orbitPlot)

        self._generalLayout.addWidget(corotatingPlot)

        # time in milliseconds between plot updates
        self._period = 33

        self._timer: QTimer | None = None

    def setPlots(
        self, orbitPlot: pg.PlotWidget, corotatingPlot: pg.PlotWidget, timer: QTimer
    ):

        self._timer = timer

        currOrbitPlot = self._orbitPlot

        currCorotatingPlot = self._corotatingPlot

        self._generalLayout.replaceWidget(currOrbitPlot, orbitPlot)

        self._generalLayout.replaceWidget(currCorotatingPlot, corotatingPlot)

        self._orbitPlot = orbitPlot

        self._corotatingPlot = corotatingPlot

        currOrbitPlot.hide()

        currCorotatingPlot.hide()

        del currOrbitPlot

        del currCorotatingPlot

    def toggleAnimation(self):

        if self._timer is None:

            errorMessage("No plot to animate")

            return

        if self._timer.isActive():

            self._timer.stop()

        else:

            self._timer.start(self._period)


class SimCtrl:
    def __init__(
        self,
        model: Simulator,
        view: SimUi,
    ):

        self._model = model

        self._view = view

        self._connectSignals()

        self._addReturnPressed()

    def _connectSignals(self):

        btnActions = {"Simulate": self._simulate, "Start/Stop": self._toggleAnimation}

        for btnText, btn in self._view.buttons.items():

            action = btnActions[btnText]

            btn.clicked.connect(action)  # type: ignore

    def _addReturnPressed(self):

        for field in self._view.inputFields.values():

            field.returnPressed.connect(self._simulate)  # type: ignore

    def _simulate(self):

        try:

            simulationInputs = self._getSimulationInputs()

        except (ValueError, SyntaxError, ZeroDivisionError, TypeError):

            return

        translatedInputs = _translateInputs(simulationInputs)

        try:

            orbitPlot, corotatingPlot, timer = self._model(**translatedInputs)

        except (TypeError, ValueError) as e:

            msg = str(e)

            for k, v in argNames.items():

                msg = msg.replace(v, k)

            errorMessage(msg)

            return

        timer.stop()

        self._view.setPlots(orbitPlot, corotatingPlot, timer)

    def _getSimulationInputs(self) -> dict[str, str | int | float]:

        inputs: dict[str, str | int | float] = {}

        for fieldText, field in self._view.inputFields.items():

            fieldValue = field.text()

            if fieldText == "Lagrange label":

                inputs[fieldText] = fieldValue

                continue

            try:

                value = safeEval(fieldValue)

            except (ValueError, SyntaxError, ZeroDivisionError) as e:

                errorMessage(f"Invalid expression in field '{fieldText}'")

                raise e

            if fieldText == "number of steps":

                inputs[fieldText] = int(value)

                continue

            try:

                inputs[fieldText] = float(value)

            except TypeError as e:

                errorMessage(
                    f"{fieldText} must be a real number, not {type(value).__name__}"
                )

                raise e

        return inputs

    def _toggleAnimation(self):

        self._view.toggleAnimation()


def errorMessage(message: str):

    errorMsg = QtWidgets.QErrorMessage()

    errorMsg.showMessage(message)

    errorMsg.exec()


T = TypeVar("T")


def _translateInputs(inputs: dict[str, T]) -> dict[str, T]:

    return {argNames[label]: v for label, v in inputs.items()}


def main():

    simApp = QtWidgets.QApplication(sys.argv)

    simApp.setFont(QFont("Arial", 10))

    view = SimUi()

    view.show()

    # pylint: disable=unused-variable
    # this assignment shouldn't be necessary, but it is
    # TODO: fix this bug
    ctrl = SimCtrl(model=Simulator(), view=view)  # noqa: F841

    sys.exit(simApp.exec())


if __name__ == "__main__":

    main()
