# pylint: disable=no-name-in-module, invalid-name, protected-access, missing-docstring
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QFormLayout,
    QWidget,
)

import pyqtgraph as pg  # type: ignore

from thesis_code import L1, L2, L3, L4, L5
from thesis_code import main as thesisMain

lagrangePoints = {
    "L1": L1,
    "L2": L2,
    "L3": L3,
    "L4": L4,
    "L5": L5,
}

simParams = {
    "number of years": "10",
    "number of steps": "10**6",
    "time step": "0.1",
}

satParams = {
    "perturbation size": "0",
    "perturbation angle": "60",
    "initial speed": "1",
    "initial velocity angle": "150",
    "Lagrange Point": "L4",
}


class ThesisUi(QMainWindow):
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

        # TODO: implement conserved plots

        # plotConservedLayout = QHBoxLayout()

        # plotConservedLayout.addWidget(QLabel("plot conserved quantities"))

    def _addInputFields(self):

        self._inputsLayout = QFormLayout()

        self._buttons = {}

        self._addButtons()

        self._addParams("Simulation Parameters", simParams)

        self._addParams("Satellite Parameters", satParams)

        self._generalLayout.addLayout(self._inputsLayout)

    def _addButtons(self):

        buttons = ("Simulate", "Start/Stop")

        buttonsLayout = QHBoxLayout()

        for btnText in buttons:

            self._buttons[btnText] = QPushButton(btnText)

            buttonsLayout.addWidget(self._buttons[btnText])

        self._inputsLayout.addRow(buttonsLayout)

    def _addParams(self, paramLabelText, params):

        paramLabel = QLabel(paramLabelText)

        paramLabel.setAlignment(Qt.AlignCenter)

        self._inputsLayout.addRow(paramLabel)

        for fieldText, defaultValue in params.items():

            fieldLine = QLineEdit(defaultValue)

            self._inputFields[fieldText] = fieldLine

            self._inputsLayout.addRow(fieldText, fieldLine)

    def _initializePlots(self):

        orbitPlot = pg.plot(title="Orbits of Masses")
        orbitPlot.setLabel("bottom", "x", units="AU")
        orbitPlot.setLabel("left", "y", units="AU")

        self._orbitPlot = orbitPlot

        corotatingPlot = pg.plot(title="Orbits in Co-Rotating Coordinate System")
        corotatingPlot.setLabel("bottom", "x", units="AU")
        corotatingPlot.setLabel("left", "y", units="AU")

        self._corotatingPlot = corotatingPlot

        self._generalLayout.addWidget(orbitPlot)

        self._generalLayout.addWidget(corotatingPlot)

        # time in milliseconds between plot updates
        self._period = 33

        self._timer = None


class ThesisCtrl:
    def __init__(self, model, view):

        self._model = model

        self._view = view

        self._connectSignals()

    def _connectSignals(self):

        btnActions = {"Simulate": self._simulate, "Start/Stop": self._toggleAnimation}

        for btnText, btn in self._view._buttons.items():

            action = btnActions[btnText]

            btn.clicked.connect(action)

    def _simulate(self):

        simulationInputs = self._getSimulationInputs()

        orbitPlot, corotatingPlot, timer = self._model(*simulationInputs.values())

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

        inputFields = self._view._inputFields

        for fieldText, field in inputFields.items():

            fieldValue = field.text()

            if fieldText == "Lagrange Point":

                inputs[fieldText] = fieldValue

                continue

            try:

                inputs[fieldText] = float(fieldValue)

            except ValueError:

                try:

                    inputs[fieldText] = int(safeEval(fieldValue))

                except (ValueError, TypeError):

                    inputs[fieldText] = fieldValue

        lagrangeStr = inputs["Lagrange Point"]
        inputs["Lagrange Point"] = lagrangePoints[lagrangeStr]

        del inputs["time step"]

        return inputs

    def _toggleAnimation(self):

        if self._view._timer.isActive():

            self._view._timer.stop()

        else:

            self._view._timer.start(self._view._period)


def safeEval(expr):

    chars = set(expr)

    if not chars.issubset("0123456789.+-*/()"):

        raise ValueError("invalid expression")

    return eval(expr)  # pylint: disable=eval-used


def main():

    thesisGui = QApplication(sys.argv)

    view = ThesisUi()

    view.show()

    ctrl = ThesisCtrl(model=thesisMain, view=view)

    sys.exit(thesisGui.exec_())


if __name__ == "__main__":

    main()
