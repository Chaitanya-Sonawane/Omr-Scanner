import cv2, json, sys, numpy as np
from pathlib import Path
sys.path.insert(0, 'files(5)')
from align import align_sheet, load_image, CANON_W, CANON_H

SHEETS_DIR = Path('SAMPLESSHEET')
images = sorted(SHEETS_DIR.glob('*.jpeg')) + sorted(SHEETS_DIR.glob('*.jpg'))
with open('files(5)/template.json') as f:
    tmpl = json.load(f)
radius = tmpl['radius']
r_sample = max(4, int(radius * 0.72))

def sample_darkness(norm, x, y):
    x0,x1 = max(0,x-r_sample), min(norm.shape[1],x+r_sample)
    y0,y1 = max(0,y-r_sample), min(norm.shape[0],y+r_sample)
    patch = norm[y0:y1,x0:x1]
    if patch.size==0: return 0.0
    mask = np.zeros(patch.shape, np.uint8)
    cv2.circle(mask,(patch.shape[1]//2,patch.shape[0]//2),r_sample,255,-1)
    vals = patch[mask==255]
    return float(255-vals.mean()) if vals.size else 0.0

OUT = Path('SAMPLESSHEET_results/diagnostics')
OUT.mkdir(parents=True, exist_ok=True)

def process(img_path, i, zoom_qs=None):
    img = load_image(str(img_path))
    h_orig, w_orig = img.shape[:2]
    warped, quality = align_sheet(img, out_size=(CANON_W, CANON_H))
    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    bg   = cv2.GaussianBlur(gray,(0,0),sigmaX=40)
    norm = np.clip(cv2.divide(gray.astype(np.float32),
                              bg.astype(np.float32)+1e-6)*160,0,255).astype(np.uint8)

    scores = {f'{q}_{o}': sample_darkness(norm,
              int(round(tmpl['bubbles'][f'{q}_{o}']['x'])),
              int(round(tmpl['bubbles'][f'{q}_{o}']['y'])))
              for q in range(1,41) for o in range(1,5)}

    arr  = np.array(list(scores.values()), dtype=np.float32)
    arr8 = np.clip(arr,0,255).astype(np.uint8)
    thr, _ = cv2.threshold(arr8,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    detected = sum(1 for q in range(1,41)
                   if max(scores[f'{q}_{o}'] for o in range(1,5)) >= thr)

    crop = cv2.cvtColor(norm, cv2.COLOR_GRAY2BGR)

    for q in range(1,41):
        for o in range(1,5):
            k = f'{q}_{o}'
            x = int(round(tmpl['bubbles'][k]['x']))
            y = int(round(tmpl['bubbles'][k]['y']))
            d = scores[k]
            is_fill = d >= thr
            col = (0,220,0) if is_fill else (0,0,220)
            th2 = 3 if is_fill else 1
            cv2.circle(crop,(x,y),radius,col,th2)
            if is_fill:
                cv2.circle(crop,(x,y),4,(0,255,0),-1)
            cv2.putText(crop,f"{d:.0f}",(x-20,y-radius-4),
                        cv2.FONT_HERSHEY_SIMPLEX,0.36,(0,0,0),2)
            cv2.putText(crop,f"{d:.0f}",(x-20,y-radius-4),
                        cv2.FONT_HERSHEY_SIMPLEX,0.36,(255,255,80),1)
            lbl = "FILL" if is_fill else "miss"
            lc  = (0,220,0) if is_fill else (60,60,255)
            cv2.putText(crop,lbl,(x-18,y+radius+15),
                        cv2.FONT_HERSHEY_SIMPLEX,0.34,(0,0,0),2)
            cv2.putText(crop,lbl,(x-18,y+radius+15),
                        cv2.FONT_HERSHEY_SIMPLEX,0.34,lc,1)

    # Draw threshold value on a vertical bar for reference
    for cl in tmpl['ref_col_lines']:
        cv2.line(crop,(int(cl),0),(int(cl),CANON_H),(255,150,0),1)
    for rl in tmpl['ref_row_lines']:
        cv2.line(crop,(0,int(rl)),(CANON_W,int(rl)),(255,150,0),1)

    cv2.rectangle(crop,(0,0),(CANON_W,90),(20,20,20),-1)
    cv2.putText(crop,
        f"Sheet {i} | {w_orig}x{h_orig} | {img_path.stat().st_size//1024}KB | align={quality['border_method']} ({quality['border_confidence']})",
        (10,28), cv2.FONT_HERSHEY_SIMPLEX, 0.52,(200,200,200),1)
    cv2.putText(crop,
        f"blur={quality['blur_score']:.0f} | thr={thr:.0f} | range={arr.min():.0f}-{arr.max():.0f} | std={arr.std():.1f} | detected={detected}/40  GREEN=FILL  RED=miss",
        (10,65), cv2.FONT_HERSHEY_SIMPLEX, 0.52,(0,255,255),2)

    cv2.imwrite(str(OUT/f"sheet_{i:02d}_full.jpg"), crop, [cv2.IMWRITE_JPEG_QUALITY,94])

    if zoom_qs:
        y0q = tmpl['ref_row_lines'][2]          # top of data rows
        y1q = tmpl['ref_row_lines'][2 + zoom_qs]
        zoom = crop[int(y0q)-10 : int(y1q)+30, 60:780]
        zoom = cv2.resize(zoom, None, fx=1.7, fy=1.7)
        cv2.imwrite(str(OUT/f"sheet_{i:02d}_zoom_Q1-Q{zoom_qs}.jpg"),
                    zoom, [cv2.IMWRITE_JPEG_QUALITY,95])

    missed = [(q, o, scores[f'{q}_{o}'])
              for q in range(1,41)
              for o in range(1,5)
              if o == max(range(1,5), key=lambda x: scores[f'{q}_{x}'])
              and scores[f'{q}_{o}'] < thr]
    missed_str = [f"Q{q}={scores[f'{q}_{o}']:.0f}" for q,o,_ in missed]
    print(f"Sheet {i}: {w_orig}x{h_orig} {img_path.stat().st_size//1024}KB | "
          f"align={quality['border_method']} | blur={quality['blur_score']:.0f} | "
          f"thr={thr:.0f} | range={arr.min():.0f}-{arr.max():.0f} std={arr.std():.1f} | "
          f"detected={detected}/40  missed={missed_str}")

# Sheets 1–5
for idx in range(5):
    process(images[idx], idx+1)

# Sheets 8 and 9 — with zoomed view of Q1-Q8
for idx in [7, 8]:
    process(images[idx], idx+1, zoom_qs=8)

print(f"\nAll diagnostics saved to {OUT}")
