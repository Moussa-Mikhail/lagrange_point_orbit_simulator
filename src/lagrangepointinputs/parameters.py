"""The simulation parameters a user can set, shared by the GUI and the web page."""

from typing import NamedTuple

from lagrangepointsimulator.descriptors import lagrange_labels


class Parameter(NamedTuple):
    label: str
    default: str
    """Text shown in the field initially. May be an expression using constants, or empty."""
    attribute: str
    """Name of the corresponding attribute of Simulator."""
    unit: str

    @property
    def display_label(self) -> str:
        return f"{self.label} ({self.unit})"


LAGRANGE_LABEL = "Lagrange label"
LAGRANGE_LABELS = lagrange_labels
DEFAULT_LAGRANGE_LABEL = "L4"

PARAMETER_GROUPS: dict[str, tuple[Parameter, ...]] = {
    "Simulation Parameters": (
        Parameter("simulation time", "10.0", "num_years", "years"),
        Parameter("time step", "1.0", "time_step", "hours"),
    ),
    "System Parameters": (
        Parameter("star mass", "sun_mass", "star_mass", "kg"),
        Parameter("planet mass", "earth_mass", "planet_mass", "kg"),
        Parameter("planet distance", "1.0", "planet_distance", "AU"),
    ),
    "Satellite Parameters": (
        Parameter("perturbation size", "0.0", "perturbation_size", "AU"),
        Parameter("perturbation angle", "", "perturbation_angle", "deg"),
        Parameter("initial speed", "1.0", "speed", "x planet speed"),
        Parameter("initial velocity angle", "", "vel_angle", "deg"),
    ),
}

# used to translate parameter labels to attribute names in Simulator
LABEL_TO_ATTRIBUTE: dict[str, str] = {
    parameter.label: parameter.attribute for parameters in PARAMETER_GROUPS.values() for parameter in parameters
}
LABEL_TO_ATTRIBUTE[LAGRANGE_LABEL] = "lagrange_label"
