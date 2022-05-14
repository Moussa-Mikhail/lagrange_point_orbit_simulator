# pylint: disable=no-name-in-module, invalid-name
import sys

from PyQt5.QtWidgets import (
    QApplication,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QLabel,
)

from PyQt5.QtCore import Qt


class ThesisUi(QMainWindow):
    def __init__(self):

        super().__init__()

        self.setWindowTitle("Simulation of Orbits near Lagrange Points")

        self._generalLayout = QHBoxLayout()

        self._centralWidget = QWidget(self)

        self.setCentralWidget(self._centralWidget)

        self._centralWidget.setLayout(self._generalLayout)

        self._createInputs()

        # self._createDisplay()

    def _createInputs(self):

        self._inputsLayout = QVBoxLayout()

        self._buttons = {}

        self._addButtons()

        self._addSimParams()

        self._addSatParams()

        self._generalLayout.addLayout(self._inputsLayout)

    def _addButtons(self):

        # Add Run button

        buttons = ["Simulate", "Start Animation", "Pause"]

        buttonsLayout = QHBoxLayout()

        for btnText in buttons:

            self._buttons[btnText] = QPushButton(btnText)

            buttonsLayout.addWidget(self._buttons[btnText])

        self._inputsLayout.addLayout(buttonsLayout)

    def _addSimParams(self):

        # Add Simulation Parameters

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

            if fieldText == "time step":

                fieldLine.setReadOnly(True)

            fieldLayout.addWidget(fieldLine)

            self._inputsLayout.addLayout(fieldLayout)

    def _addSatParams(self):

        # Add Satellite Parameters

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

    # TODO: Figure out how to insert graph into gui
    # def _createDisplay(self):

    #     self._display = QHBoxLayout()

    #     self._generalLayout.addWidget(self._display)


def main():
    """Main function."""
    # Create an instance of `QApplication`
    thesisGui = QApplication(sys.argv)

    # Show the calculator's GUI
    view = ThesisUi()

    view.show()

    # ThesisCtrl(model=model, view=view)

    # Execute calculator's main loop
    sys.exit(thesisGui.exec_())


if __name__ == "__main__":

    main()
