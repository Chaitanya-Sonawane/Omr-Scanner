/**
 * quality.js
 * ----------
 * All frame-quality math lives here as pure functions over an OpenCV.js
 * `cv` namespace. Nothing here talks to the DOM, the camera, or the
 * network - it only looks at pixels and returns numbers, so it's easy to
 * reason about and re-tune independently of the UI/camera plumbing.
 *
 * The sheet-detection strategy deliberately mirrors backend/core/align.py
 * (adaptive-threshold -> contour -> 4-point approx -> aspect-ratio
 * scoring, with a minAreaRect fallback) so that "looks good to the
 * frontend" reliably predicts "will align cleanly on the backend" -
 * without re-implementing align.py's actual warp or bubble logic, which
 * never runs here.
 */
const OMRQuality = (() => {

  // Loaded once from /api/config so this never drifts from template.json.
  let TARGET_ASPECT = 1400 / 2200;

  function setTargetAspect(a) { TARGET_ASPECT = a; }

  // ---- tunables (analysis runs on a downscaled ~480px-wide frame) ----
  const CFG = {
    minAreaFrac: 0.30,       // sheet must fill at least this much of the frame
    maxAreaFrac: 0.97,       // above this, corners are likely clipped
    idealAreaFrac: [0.45, 0.90],
    aspectTolerance: 0.14,   // relative error allowed vs TARGET_ASPECT
    cornerAngleTolDeg: 18,   // how rectangular the quad must look
    centerTolFrac: 0.10,     // centroid offset allowed, as frac of frame dim
    edgeMarginFrac: 0.015,   // corner must be at least this far from frame edge (else "clipped")
    minSharpness: 35,        // Laplacian variance floor on the downscaled analysis frame
    minBrightness: 55,
    maxBrightness: 225,
    maxGlareFrac: 0.035,     // fraction of ROI pixels blown out (>=250)
    maxMotion: 9.0,          // mean abs frame-diff floor for "hold steady"
  };

  function order4(pts) {
    // pts: [{x,y}] length 4 -> [tl, tr, br, bl]
    const sum = pts.map(p => p.x + p.y);
    const diff = pts.map(p => p.x - p.y);
    const tl = pts[sum.indexOf(Math.min(...sum))];
    const br = pts[sum.indexOf(Math.max(...sum))];
    const tr = pts[diff.indexOf(Math.max(...diff))];
    const bl = pts[diff.indexOf(Math.min(...diff))];
    return [tl, tr, br, bl];
  }

  function dist(a, b) { return Math.hypot(a.x - b.x, a.y - b.y); }

  function cornerAnglesOk(q, tolDeg) {
    for (let i = 0; i < 4; i++) {
      const a = q[(i + 3) % 4], b = q[i], c = q[(i + 1) % 4];
      const v1 = { x: a.x - b.x, y: a.y - b.y };
      const v2 = { x: c.x - b.x, y: c.y - b.y };
      const n1 = Math.hypot(v1.x, v1.y), n2 = Math.hypot(v2.x, v2.y);
      if (n1 < 1e-3 || n2 < 1e-3) return false;
      const cosA = Math.min(1, Math.max(-1, (v1.x * v2.x + v1.y * v2.y) / (n1 * n2)));
      const angDeg = Math.acos(cosA) * 180 / Math.PI;
      if (Math.abs(angDeg - 90) > tolDeg) return false;
    }
    return true;
  }

  function quadAspect(q) {
    const [tl, tr, br, bl] = q;
    const w = (dist(tl, tr) + dist(bl, br)) / 2;
    const h = (dist(tl, bl) + dist(tr, br)) / 2;
    return w / Math.max(h, 1e-6);
  }

  function quadArea(q) {
    let area = 0;
    for (let i = 0; i < 4; i++) {
      const a = q[i], b = q[(i + 1) % 4];
      area += a.x * b.y - b.x * a.y;
    }
    return Math.abs(area) / 2;
  }

  /**
   * Detects the sheet's outer quadrilateral in a grayscale cv.Mat.
   * Returns { quad: [{x,y}x4], method, aspectErr } or null.
   */
  function detectSheetQuad(cv, grayMat) {
    const w = grayMat.cols, h = grayMat.rows;
    const frameArea = w * h;

    const blurred = new cv.Mat();
    cv.GaussianBlur(grayMat, blurred, new cv.Size(5, 5), 0);

    const thresh = new cv.Mat();
    cv.adaptiveThreshold(blurred, thresh, 255, cv.ADAPTIVE_THRESH_GAUSSIAN_C, cv.THRESH_BINARY_INV, 35, 12);
    const kernel = cv.Mat.ones(5, 5, cv.CV_8U);
    cv.dilate(thresh, thresh, kernel, new cv.Point(-1, -1), 2);

    const tryFind = (mat) => {
      const contours = new cv.MatVector();
      const hierarchy = new cv.Mat();
      cv.findContours(mat, contours, hierarchy, cv.RETR_LIST, cv.CHAIN_APPROX_SIMPLE);

      let best = null; // {score, quad, method}
      const n = Math.min(contours.size(), 25);
      for (let i = 0; i < n; i++) {
        const c = contours.get(i);
        const area = cv.contourArea(c);
        const frac = area / frameArea;
        if (frac < CFG.minAreaFrac || frac > 0.995) { c.delete(); continue; }

        const peri = cv.arcLength(c, true);
        const approx = new cv.Mat();
        cv.approxPolyDP(c, approx, 0.02 * peri, true);

        let quad = null, method = null;
        if (approx.rows === 4 && cv.isContourConvex(approx)) {
          const pts = [];
          for (let k = 0; k < 4; k++) pts.push({ x: approx.data32S[k * 2], y: approx.data32S[k * 2 + 1] });
          const ordered = order4(pts);
          if (cornerAnglesOk(ordered, CFG.cornerAngleTolDeg)) { quad = ordered; method = 'contour_4pt'; }
        }
        if (!quad) {
          const rect = cv.minAreaRect(c);
          const box = cv.RotatedRect.points(rect);
          const pts = box.map(p => ({ x: p.x, y: p.y }));
          const ordered = order4(pts);
          if (cornerAnglesOk(ordered, 30)) { quad = ordered; method = 'min_area_rect'; }
        }
        approx.delete(); c.delete();

        if (quad) {
          const aspectErr = Math.abs(quadAspect(quad) / TARGET_ASPECT - 1);
          const score = aspectErr + (method === 'min_area_rect' ? 0.08 : 0);
          if (!best || score < best.score) best = { score, quad, method, aspectErr, frac };
        }
      }
      contours.delete(); hierarchy.delete();
      return best;
    };

    let result = tryFind(thresh);

    if (!result) {
      const edges = new cv.Mat();
      cv.Canny(blurred, edges, 40, 120);
      cv.dilate(edges, edges, kernel, new cv.Point(-1, -1), 2);
      result = tryFind(edges);
      edges.delete();
    }

    blurred.delete(); thresh.delete(); kernel.delete();
    return result; // null if nothing plausible found
  }

  function laplacianVariance(cv, grayMat, roiRect) {
    let target = grayMat;
    let roiMat = null;
    if (roiRect) {
      roiMat = grayMat.roi(roiRect);
      target = roiMat;
    }
    const lap = new cv.Mat();
    cv.Laplacian(target, lap, cv.CV_64F);
    const mean = new cv.Mat(), stddev = new cv.Mat();
    cv.meanStdDev(lap, mean, stddev);
    const variance = Math.pow(stddev.data64F[0], 2);
    lap.delete(); mean.delete(); stddev.delete();
    if (roiMat) roiMat.delete();
    return variance;
  }

  function boundingRectClamped(cv, quad, w, h) {
    // Takes `cv` explicitly rather than reaching for window.cv, so this
    // stays correct if OMRQuality is ever used against a `cv` instance
    // that isn't the global (e.g. a future worker/offscreen context).
    const xs = quad.map(p => p.x), ys = quad.map(p => p.y);
    const x = Math.max(0, Math.floor(Math.min(...xs)));
    const y = Math.max(0, Math.floor(Math.min(...ys)));
    const x2 = Math.min(w, Math.ceil(Math.max(...xs)));
    const y2 = Math.min(h, Math.ceil(Math.max(...ys)));
    return new cv.Rect(x, y, Math.max(1, x2 - x), Math.max(1, y2 - y));
  }

  function brightnessAndGlare(cv, grayMat, roiRect) {
    const roiMat = roiRect ? grayMat.roi(roiRect) : grayMat;
    const mean = new cv.Mat(), stddev = new cv.Mat();
    cv.meanStdDev(roiMat, mean, stddev);
    const brightness = mean.data64F[0];

    // glare fraction: pixels essentially blown out
    const hist = new cv.Mat();
    const srcVec = new cv.MatVector(); srcVec.push_back(roiMat);
    cv.calcHist(srcVec, [0], new cv.Mat(), hist, [32], [0, 256]);
    let total = 0, blown = 0;
    for (let i = 0; i < 32; i++) {
      const v = hist.data32F[i];
      total += v;
      if (i >= 31) blown += v; // top bin ~= 248-255
    }
    const glareFrac = total > 0 ? blown / total : 0;

    mean.delete(); stddev.delete(); hist.delete(); srcVec.delete();
    if (roiRect) roiMat.delete();
    return { brightness, glareFrac };
  }

  function motionScore(cv, grayMat, prevGrayMat) {
    if (!prevGrayMat) return 0;
    const diff = new cv.Mat();
    cv.absdiff(grayMat, prevGrayMat, diff);
    const mean = new cv.Mat(), stddev = new cv.Mat();
    cv.meanStdDev(diff, mean, stddev);
    const score = mean.data64F[0];
    diff.delete(); mean.delete(); stddev.delete();
    return score;
  }

  /**
   * Full per-frame analysis. `grayMat` is a cv.Mat (CV_8UC1) of the
   * downscaled analysis frame. Returns a flat metrics object consumed by
   * guidance.js - no UI or camera concerns here.
   */
  function analyzeFrame(cv, grayMat, prevGrayMat) {
    const w = grayMat.cols, h = grayMat.rows;
    const found = detectSheetQuad(cv, grayMat);

    const metrics = {
      sheetFound: !!found,
      method: found ? found.method : null,
      quad: found ? found.quad : null,
      areaFrac: found ? quadArea(found.quad) / (w * h) : 0,
      aspectErr: found ? found.aspectErr : null,
      frameW: w, frameH: h,
    };

    if (found) {
      const cx = found.quad.reduce((s, p) => s + p.x, 0) / 4;
      const cy = found.quad.reduce((s, p) => s + p.y, 0) / 4;
      metrics.centerOffsetFrac = Math.hypot((cx - w / 2) / w, (cy - h / 2) / h);

      const rectAngleOk = cornerAnglesOk(found.quad, CFG.cornerAngleTolDeg);
      metrics.skewed = !rectAngleOk;

      const margin = CFG.edgeMarginFrac;
      metrics.clipped = found.quad.some(p =>
        p.x < w * margin || p.x > w * (1 - margin) ||
        p.y < h * margin || p.y > h * (1 - margin)
      );

      const roi = boundingRectClamped(cv, found.quad, w, h);
      metrics.sharpness = laplacianVariance(cv, grayMat, roi);
      const bg = brightnessAndGlare(cv, grayMat, roi);
      metrics.brightness = bg.brightness;
      metrics.glareFrac = bg.glareFrac;
    } else {
      metrics.sharpness = laplacianVariance(cv, grayMat, null);
      const bg = brightnessAndGlare(cv, grayMat, null);
      metrics.brightness = bg.brightness;
      metrics.glareFrac = bg.glareFrac;
      metrics.centerOffsetFrac = null;
      metrics.skewed = null;
      metrics.clipped = false;
    }

    metrics.motion = motionScore(cv, grayMat, prevGrayMat);
    return metrics;
  }

  return { CFG, setTargetAspect, analyzeFrame, detectSheetQuad, laplacianVariance, brightnessAndGlare, boundingRectClamped };
})();
