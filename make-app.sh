poetry run pyinstaller src/lagrangepointgui/sim_gui.py --noconfirm --noconsole \
  --add-data 'src/lagrangepointgui/default_presets.toml:.' --add-data 'src/lagrangepointgui/user_presets.toml:.'
