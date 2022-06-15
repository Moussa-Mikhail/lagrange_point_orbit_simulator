# pylint: disable=no-name-in-module, invalid-name, protected-access, missing-docstring
import sys

import pyqtgraph as pg  # type: ignore
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QErrorMessage,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QWidget,
)

# pylint: disable=unused-import
from simulation.constants import safe_eval as safeEval  # noqa: F401
from simulation import main as simMain

simMain = simMain.__wrapped__

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


class SimUi(QMainWindow):
    def __init__(self):

        super().__init__()

        self.setWindowTitle("Simulation of Orbits near Lagrange Points")

        self._generalLayout = QHBoxLayout()

        self._centralWidget = QWidget(self)

        self.setCentralWidget(self._centralWidget)

        self._centralWidget.setLayout(self._generalLayout)

        self._inputFields = {}

        self._addInputFields()

        self._initializePlots()

    def _addInputFields(self):

        self._inputsLayout = QFormLayout()

        self._buttons = {}

        self._addButtons()

        self._addParams("Simulation Parameters", simParams)

        self._addParams("Satellite Parameters", satParams)

        self._addParams("System Parameters", sysParams)

        self._generalLayout.addLayout(self._inputsLayout)

    def _addButtons(self):

        buttons = ("Simulate", "Start/Stop")

        buttonsLayout = QHBoxLayout()

        for btnText in buttons:

            self._buttons[btnText] = QPushButton(btnText)

            buttonsLayout.addWidget(self._buttons[btnText])

        self._inputsLayout.addRow(buttonsLayout)

    def _addParams(self, argLabelText, Params):

        argLabel = QLabel(argLabelText)

        argLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._inputsLayout.addRow(argLabel)

        for fieldText, defaultValue in Params.items():

            fieldLine = QLineEdit(defaultValue)

            self._inputFields[fieldText] = fieldLine

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

        self._timer = None


class SimCtrl:
    def __init__(self, model, view):

        self._model = model

        self._view = view

        self._connectSignals()

        self._addReturnPressed()

    def _connectSignals(self):

        btnActions = {"Simulate": self._simulate, "Start/Stop": self._toggleAnimation}

        for btnText, btn in self._view._buttons.items():

            action = btnActions[btnText]

            btn.clicked.connect(action)

    def _addReturnPressed(self):

        for field in self._view._inputFields.values():

            field.returnPressed.connect(self._simulate)

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

        self._view._timer = timer

        currOrbitPlot = self._view._orbitPlot

        currCorotatingPlot = self._view._corotatingPlot

        self._view._generalLayout.replaceWidget(currOrbitPlot, orbitPlot)

        self._view._generalLayout.replaceWidget(currCorotatingPlot, corotatingPlot)

        self._view._orbitPlot = orbitPlot

        self._view._corotatingPlot = corotatingPlot

        currOrbitPlot.hide()

        currCorotatingPlot.hide()

        del currOrbitPlot

        del currCorotatingPlot

    def _getSimulationInputs(self):

        inputs = {}

        for fieldText, field in self._view._inputFields.items():

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

        if self._view._timer is None:

            errorMessage("No simulation to animate")

            return

        if self._view._timer.isActive():

            self._view._timer.stop()

        else:

            self._view._timer.start(self._view._period)


def errorMessage(message):

    errorMsg = QErrorMessage()

    errorMsg.showMessage(message)

    errorMsg.exec()


def _translateInputs(inputs):

    return {argNames[label]: v for label, v in inputs.items()}


def main():

    simApp = QApplication(sys.argv)

    view = SimUi()

    view.show()

    # pylint: disable=unused-variable
    # this assignment shouldn't be necessary, but it is
    # TODO: fix this bug
    ctrl = SimCtrl(model=simMain, view=view)  # noqa: F841

    sys.exit(simApp.exec())


if __name__ == "__main__":

    main()
