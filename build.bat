@echo off
pyinstaller --paths src src/lagrangepointgui/sim_gui.py --noconfirm --noconsole --add-data 'src/lagrangepointinputs/default_presets.toml:.'
