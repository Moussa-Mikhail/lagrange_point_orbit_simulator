# pylint: disable=no-name-in-module, invalid-name, missing-docstring
import sys
from typing import TypeVar, TypeAlias

from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from lagrangepointsimulator import Simulator

from lagrangepointgui.orbit_plotter import Plotter
from lagrangepointgui.safe_eval import safe_eval as safeEval

Params: TypeAlias = dict[str, tuple[str, str]]

# parameter name: (default value, attribute name)
simParams: Params = {
    "number of years": ("10.0", "num_years"),
    "time step (hours)": ("1.0", "time_step"),
}

satParams: Params = {
    "perturbation size": ("0.0", "perturbation_size"),
    "perturbation angle": ("", "perturbation_angle"),
    "initial speed": ("1.0", "speed"),
    "initial velocity angle": ("", "vel_angle"),
    "Lagrange label": ("L4", "lagrange_label"),
}

sysParams: Params = {
    "star mass": ("sun_mass", "star_mass"),
    "planet mass": ("earth_mass", "planet_mass"),
    "planet distance": ("1.0", "planet_distance"),
}


class SimUi(QtWidgets.QMainWindow):
    def __init__(self, plotter: Plotter):

        super().__init__()

        self._plotter = plotter
        self._plotted = False

        self.setWindowTitle("Orbits near Lagrange Point")

        self._centralWidget = QtWidgets.QWidget(self)
        self.setCentralWidget(self._centralWidget)
        self._generalLayout = QtWidgets.QHBoxLayout()
        self._centralWidget.setLayout(self._generalLayout)

        self.inputFields: dict[str, QtWidgets.QLineEdit] = {}
        self._addInputFields()

        self._generalLayout.addWidget(self._plotter.inertial_plot)
        self._generalLayout.addWidget(self._plotter.corotating_plot)
        self.resize(self._generalLayout.sizeHint())

    def _addInputFields(self) -> None:

        self._inputsLayout = QtWidgets.QFormLayout()

        self.buttons: dict[str, QtWidgets.QPushButton] = {}
        self._addButtons()

        self._addParams("Simulation Parameters", simParams)
        self._addParams("Satellite Parameters", satParams)
        self._addParams("System Parameters", sysParams)

        self._generalLayout.addLayout(self._inputsLayout)

    def _addButtons(self) -> None:

        buttons = ("Simulate", "Start/Stop")
        buttonsLayout = QtWidgets.QHBoxLayout()

        for btnText in buttons:
            self.buttons[btnText] = QtWidgets.QPushButton(btnText)

            buttonsLayout.addWidget(self.buttons[btnText])

        self._inputsLayout.addRow(buttonsLayout)

    def _addParams(self, argLabelText: str, params: Params) -> None:

        argLabel = QtWidgets.QLabel(argLabelText)
        argLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._inputsLayout.addRow(argLabel)

        for fieldText, (defaultValue, _) in params.items():
            fieldLine = QtWidgets.QLineEdit(defaultValue)

            self.inputFields[fieldText] = fieldLine
            self._inputsLayout.addRow(fieldText, fieldLine)

    def updatePlots(self) -> None:

        self._plotted = True
        self._plotter.plot_orbits()

    def toggleAnimation(self) -> None:

        if not self._plotted:
            errorMessage("No plots to animate.")

            return

        self._plotter.toggle_animation()


allParams = simParams | satParams | sysParams

# used to translate param labels used in gui to attribute names
paramLabelsToAttribute = {
    paramLabel: attribute for paramLabel, (_, attribute) in allParams.items()
}


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
            simulationInputs = self._getSimulationInputs()

        except ValueError as e:
            errorMessage(str(e))
            return

        translatedInputs = _translateInputs(simulationInputs)

        try:
            for attr, value in translatedInputs.items():
                setattr(self._model, attr, value)

        except (TypeError, ValueError) as e:

            msg = str(e)

            for paramLabel, attr in paramLabelsToAttribute.items():
                msg = msg.replace(attr, paramLabel)

            errorMessage(msg)

            return

        self._model.simulate()
        self._view.updatePlots()

    def _getSimulationInputs(self) -> dict[str, str | float | None]:

        inputs: dict[str, str | float | None] = {}

        for fieldText, field in self._view.inputFields.items():

            fieldValue = field.text()

            if fieldText == "Lagrange label":
                inputs[fieldText] = fieldValue
                continue

            try:
                value = safeEval(fieldValue)

            except ValueError as e:

                raise ValueError(
                    f"Invalid expression in field '{fieldText}'.\n{e}"
                ) from e

            if value is None:
                inputs[fieldText] = value
                continue

            inputs[fieldText] = float(value)

        return inputs

    def _toggleAnimation(self) -> None:
        self._view.toggleAnimation()


def errorMessage(message: str) -> None:
    errorMsg = QtWidgets.QErrorMessage()
    errorMsg.showMessage(message)
    errorMsg.exec()


T = TypeVar("T")


def _translateInputs(inputs: dict[str, T]) -> dict[str, T]:
    return {paramLabelsToAttribute[label]: v for label, v in inputs.items()}


def main() -> None:
    simApp = QtWidgets.QApplication(sys.argv)

    simApp.setFont(QFont("Arial", 10))

    sim = Simulator()

    plotter = Plotter(sim)

    view = SimUi(plotter)

    view.show()

    ctrl = SimCtrl(model=sim, view=view)  # noqa: F841 # pylint: disable=unused-variable

    sys.exit(simApp.exec())


if __name__ == "__main__":
    main()
