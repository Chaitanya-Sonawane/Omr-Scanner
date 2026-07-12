import sys
sys.path.insert(0, 'omr-web/backend-2')
import cv2
import numpy as np
from pathlib import Path
from omr_engine import load_template, scan_image
from align import align_sheet, load_image
from scan_omr import grid_correct

OUT_DIR = Path('scan_results/SAMPLESSHEET')
OUT_DIR.mkdir(parents=True, exist_ok=True)

OPT_MAP = {1:'A', 2:'B', 3:'C', 4:'D'}
COL_OK     = (34, 180, 34)
COL_MULTI  = (0, 0, 210)
COL_REVIEW = (0, 150, 255)
COL_BLANK  = (160,160,160)
COL_WHITE  = (255,255,255)
COL_HDR    = (37, 90, 200)
COL_TEXT   = (30, 30, 30)

def bcolor(s):
    return {'OK':COL_OK,'MULTI':COL_MULTI,'REVIEW':COL_REVIEW,'BLANK':COL_BLANK}.get(s,COL_BLANK)

def draw_overlay(img_path, template, qs):
    img = load_image(img_path)
    warped, _ = align_sheet(img, out_size=(template['canon_w'], template['canon_h']))
    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    cxy, _ = grid_correct(gray, template)
    r = template['radius']
    out = warped.copy()
    q_map = {q['q']: q for q in qs}
    for key, c in template['bubbles'].items():
        qn, opt = map(int, key.split('_'))
        cx = int(round(cxy(c['x'], c['y'])[0]))
        cy = int(round(cxy(c['x'], c['y'])[1]))
        item = q_map.get(qn)
        if not item: continue
        st, sel = item['status'], item['option']
        if st == 'MULTI':
            cv2.circle(out,(cx,cy),r,COL_MULTI,3)
        elif st == 'REVIEW':
            cv2.circle(out,(cx,cy),r,COL_REVIEW,2)
        elif st == 'BLANK':
            cv2.circle(out,(cx,cy),r,COL_BLANK,1)
        elif sel == opt:
            cv2.circle(out,(cx,cy),r,COL_OK,-1)
            cv2.putText(out, OPT_MAP.get(opt,''), (cx-8,cy+6),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, COL_WHITE, 1, cv2.LINE_AA)
        else:
            cv2.circle(out,(cx,cy),r,(200,200,200),1)
    h = 1100
    sc = h / out.shape[0]
    return cv2.resize(out, (int(out.shape[1]*sc), h))

def draw_card(qs, name, meta):
    CW=520; RH=22; HDR=115; N=len(qs); FTR=50
    CH = HDR+(N+1)*RH+FTR
    card = np.full((CH,CW,3), 245, dtype=np.uint8)
    cv2.rectangle(card,(0,0),(CW,HDR),COL_HDR,-1)
    cv2.putText(card, name[:38], (12,32), cv2.FONT_HERSHEY_SIMPLEX, 0.62, COL_WHITE, 2, cv2.LINE_AA)
    aq  = meta.get('align_quality',{})
    brd = aq.get('border_confidence','?')
    grd = 'yes' if meta.get('grid_matched') else 'no'
    blr = aq.get('blur_score',0)
    rng = f"{meta.get('score_min',0):.0f}-{meta.get('score_max',0):.0f}"
    cv2.putText(card, f'Border:{brd}  Grid:{grd}  Blur:{blr:.0f}  Range:{rng}',
        (12,56), cv2.FONT_HERSHEY_SIMPLEX, 0.35, COL_WHITE, 1, cv2.LINE_AA)
    n_ok=sum(1 for q in qs if q['status']=='OK')
    n_mu=sum(1 for q in qs if q['status']=='MULTI')
    n_rv=sum(1 for q in qs if q['status']=='REVIEW')
    n_bl=sum(1 for q in qs if q['status']=='BLANK')
    cv2.putText(card, f'OK:{n_ok}  MULTI:{n_mu}  REVIEW:{n_rv}  BLANK:{n_bl}',
        (12,76), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (255,220,80), 1, cv2.LINE_AA)
    notes = meta.get('sheet_notes',[])
    if notes:
        cv2.putText(card, notes[0][:62], (12,96),
            cv2.FONT_HERSHEY_SIMPLEX, 0.30, (200,230,255), 1, cv2.LINE_AA)
    y0 = HDR
    cv2.rectangle(card,(0,y0),(CW,y0+RH),(200,205,220),-1)
    for x,lbl in [(8,'Q'),(55,'Answer'),(155,'Status'),(270,'Conf'),(370,'')]:
        cv2.putText(card,lbl,(x,y0+15),cv2.FONT_HERSHEY_SIMPLEX,0.38,COL_TEXT,1,cv2.LINE_AA)
    for i,item in enumerate(qs):
        y  = HDR+(i+1)*RH
        bg = (255,255,255) if i%2==0 else (235,235,242)
        cv2.rectangle(card,(0,y),(CW,y+RH),bg,-1)
        st  = item['status']
        opt = OPT_MAP.get(item['option'],'—') if item['option'] else '—'
        if st=='MULTI': opt='MULTI'
        if st=='BLANK': opt='—'
        conf = f"{item['confidence']:.0f}%"
        sc   = bcolor(st)
        cv2.circle(card,(7,y+12),5,sc,-1)
        cv2.putText(card,f"Q{item['q']}",(16,y+15),cv2.FONT_HERSHEY_SIMPLEX,0.38,COL_TEXT,1,cv2.LINE_AA)
        cv2.putText(card,opt,   (55, y+15),cv2.FONT_HERSHEY_SIMPLEX,0.40,sc,     1,cv2.LINE_AA)
        cv2.putText(card,st,    (155,y+15),cv2.FONT_HERSHEY_SIMPLEX,0.34,sc,     1,cv2.LINE_AA)
        cv2.putText(card,conf,  (270,y+15),cv2.FONT_HERSHEY_SIMPLEX,0.34,COL_TEXT,1,cv2.LINE_AA)
        bw = int(item['confidence']/100.0*110)
        cv2.rectangle(card,(370,y+5),(370+bw,y+RH-4),sc,-1)
    yf = HDR+(N+1)*RH+10
    for x,col,lbl in [(8,COL_OK,'OK'),(70,COL_MULTI,'MULTI'),(160,COL_REVIEW,'REVIEW'),(270,COL_BLANK,'BLANK')]:
        cv2.circle(card,(x,yf+8),6,col,-1)
        cv2.putText(card,lbl,(x+14,yf+13),cv2.FONT_HERSHEY_SIMPLEX,0.36,COL_TEXT,1,cv2.LINE_AA)
    return card

def combine(s, c):
    sh,ch = s.shape[0],c.shape[0]
    if sh>ch:
        c = np.vstack([c, np.full((sh-ch,c.shape[1],3),245,dtype=np.uint8)])
    elif ch>sh:
        s = np.vstack([s, np.full((ch-sh,s.shape[1],3),245,dtype=np.uint8)])
    div = np.full((max(sh,ch),4,3),180,dtype=np.uint8)
    return np.hstack([s,div,c])

template = load_template()
sheets   = sorted(Path('SAMPLESSHEET').glob('*.jpeg'))
print(f'Generating {len(sheets)} result JPGs...')
for p in sheets:
    label = p.stem.replace(' ','_').replace(':','-')
    print(f'  {p.name}...', end=' ', flush=True)
    try:
        res  = scan_image(str(p), template)
        qs   = res['questions']
        meta = res['meta']
        simg = draw_overlay(str(p), template, qs)
        card = draw_card(qs, p.stem, meta)
        out  = combine(simg, card)
        outf = OUT_DIR / f'result_{label}.jpg'
        cv2.imwrite(str(outf), out, [cv2.IMWRITE_JPEG_QUALITY, 92])
        n_ok=sum(1 for q in qs if q['status']=='OK')
        n_mu=sum(1 for q in qs if q['status']=='MULTI')
        n_rv=sum(1 for q in qs if q['status']=='REVIEW')
        n_bl=sum(1 for q in qs if q['status']=='BLANK')
        print(f'OK:{n_ok} MULTI:{n_mu} REVIEW:{n_rv} BLANK:{n_bl}')
    except Exception as e:
        import traceback; traceback.print_exc()
        print(f'ERROR: {e}')
print('Done. Results in scan_results/SAMPLESSHEET/')
