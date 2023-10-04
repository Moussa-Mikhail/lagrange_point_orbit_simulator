@echo off
pyinstaller src/lagrangepointgui/sim_gui.py --noconfirm --noconsole \
  --add-data 'src/lagrangepointgui/default_presets.toml:.'
