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
    QVBoxLayout,
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


class ThesisUi(QMainWindow):
    def __init__(self):

        super().__init__()

        self.setWindowTitle("Simulation of Orbits near Lagrange Points")

        self._generalLayout = QHBoxLayout()

        self._centralWidget = QWidget(self)

        self.setCentralWidget(self._centralWidget)

        self._centralWidget.setLayout(self._generalLayout)

        self._addInputFields()

        self._initializePlots()

        # TODO: implement conserved plots

        # plotConservedLayout = QHBoxLayout()

        # plotConservedLayout.addWidget(QLabel("plot conserved quantities"))

        # time in milliseconds between plot updates
        self._period = 33

        self._timer = None

        # TODO: make it so that plot_orbit shows initial conditions

    def _addInputFields(self):

        # TODO: refactor how this is done.
        # Add input fields all at once and then insert text

        self._inputsLayout = QVBoxLayout()

        self._buttons = {}

        self._addButtons()

        self._addSimParams()

        self._addSatParams()

        self._generalLayout.addLayout(self._inputsLayout)

    def _addButtons(self):

        buttons = ("Simulate", "Start/Stop")

        buttonsLayout = QHBoxLayout()

        for btnText in buttons:

            self._buttons[btnText] = QPushButton(btnText)

            buttonsLayout.addWidget(self._buttons[btnText])

        self._inputsLayout.addLayout(buttonsLayout)

    def _addSimParams(self):

        simParamsLabel = QLabel("Simulation Parameters")

        self._inputsLayout.addWidget(simParamsLabel)

        simParams = {
            "number of years": "10",
            "number of steps": "10**6",
            "time step": "0.1",
        }

        for fieldText, defaultValue in simParams.items():

            fieldLayout = QHBoxLayout()

            fieldLabel = QLabel(fieldText)

            fieldLayout.addWidget(fieldLabel)

            fieldLine = QLineEdit(defaultValue)

            fieldLine.setAlignment(Qt.AlignRight)

            fieldLayout.addWidget(fieldLine)

            self._inputsLayout.addLayout(fieldLayout)

    def _addSatParams(self):

        satParamsLabel = QLabel("\nSatellite Parameters")

        self._inputsLayout.addWidget(satParamsLabel)

        satParams = {
            "perturbation size": "0",
            "perturbation angle": "60",
            "initial speed": "1",
            "initial velocity angle": "150",
            "Lagrange Point": "L4",
        }

        for fieldText, defaultValue in satParams.items():

            fieldLayout = QHBoxLayout()

            fieldLabel = QLabel(fieldText)

            fieldLayout.addWidget(fieldLabel)

            fieldLine = QLineEdit(defaultValue)

            fieldLine.setAlignment(Qt.AlignRight)

            fieldLayout.addWidget(fieldLine)

            self._inputsLayout.addLayout(fieldLayout)

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

        inputsLayout = self._view._inputsLayout

        num_items = inputsLayout.count()

        for i in range(num_items):

            itemAtIdx = inputsLayout.itemAt(i)

            if isinstance(itemAtIdx, QHBoxLayout):

                label = itemAtIdx.itemAt(0).widget().text()

                field = itemAtIdx.itemAt(1).widget()

                if isinstance(field, QLineEdit):

                    displayText = field.displayText()

                    try:

                        inputs[label] = float(displayText)

                    except ValueError:

                        try:

                            inputs[label] = int(safeEval(displayText))

                        except (ValueError, TypeError):

                            inputs[label] = displayText

                elif isinstance(field, QCheckBox):

                    inputs[label] = field.isChecked()

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
