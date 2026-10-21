#!/usr/bin/env bash

if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
    PYTHONPATH=src python3 -m lagrangepointgui.sim_gui
else
    echo "Virtual environment not found at .venv/. Please activate your environment manually."
fi