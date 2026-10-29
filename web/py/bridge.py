"""Python side of the web UI. Runs inside Pyodide in a Web Worker.

lagrangepointapi.session does the work, and this only hands its results to JS. The integration itself runs in JS
(web/integrator.js), between prepare and finish.
"""

from js import Object
from pyodide.ffi import to_js

from lagrangepointapi import session

_session = session.Session()


def _to_js(obj):
    return to_js(obj, dict_converter=Object.fromEntries)


def get_spec():
    return _to_js(session.get_spec())


# The user's presets file lives in Pyodide's in-memory file system, so it is gone when the page closes. app.js keeps
# the text in localStorage and sends it back through set_user_text at startup.


def get_user_text():
    return session.get_presets_text()["text"]


def set_user_text(text):
    return _to_js(session.set_presets_text(text))


def save_preset(name, values):
    return _to_js(session.save_preset(name, values.to_py()))


def delete_preset(name):
    return _to_js(session.delete_preset(name))


def prepare(inputs):
    """Validate the inputs and set up the first row of the simulation. inputs maps parameter labels to field text.

    Returns what web/integrator.js needs to run the integration, or {"error": message}.
    """
    if (error := _session.apply_inputs(inputs.to_py())) is not None:
        return _to_js({"error": error})

    return _to_js(_session.initial_state())


def finish(rows):
    """Take the rows integrated in JS and prepare the data for the plots."""
    _session.set_rows(rows.to_py())
    return _to_js(_session.plot_data())


def conserved():
    return _to_js(_session.conserved())


def report():
    return _to_js(_session.report())
