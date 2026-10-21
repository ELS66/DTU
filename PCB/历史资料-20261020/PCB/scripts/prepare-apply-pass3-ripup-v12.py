from pathlib import Path
exec(Path('PCB/scripts/prepare-apply-ripup-large-v12.py').read_text(encoding='utf-8').replace('escape-ripup-large-v12','pass3-ripup-large-v12').replace('apply-selective-ripup-large-v12','apply-pass3-ripup-large-v12'))
