import sys
sys.path.insert(0, 'omr-web/backend-2')
from omr_engine import load_template, scan_image
from pathlib import Path

template = load_template()
OPT_MAP  = {1:'A', 2:'B', 3:'C', 4:'D'}
sheets   = sorted(Path('SAMPLESSHEET').glob('*.jpeg'))
print(f'{"Sheet":<45} {"OK":>4} {"MULTI":>6} {"REVIEW":>7} {"BLANK":>6}')
print('-'*70)
for p in sheets:
    res  = scan_image(str(p), template)
    qs   = res['questions']
    n_ok = sum(1 for q in qs if q['status']=='OK')
    n_mu = sum(1 for q in qs if q['status']=='MULTI')
    n_rv = sum(1 for q in qs if q['status']=='REVIEW')
    n_bl = sum(1 for q in qs if q['status']=='BLANK')
    print(f'{p.name[:44]:<45} {n_ok:>4} {n_mu:>6} {n_rv:>7} {n_bl:>6}')
