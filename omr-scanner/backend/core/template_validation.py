"""
template_validation.py
----------------------
Post-perspective-correction template validation.

Runs AFTER align.py has warped a photographed sheet into the fixed
canonical CANON_W x CANON_H frame AND after scan_omr.grid_correct() has
cross-checked that warp against the sheet's own printed gridlines. Its
single job is to answer one question with evidence, not a guess:

    "Does this corrected image actually match the reference OMR template,
     or did the geometry lock onto the wrong / partial / distorted sheet?"

Rather than run a second, weaker gridline detection of its own (which
would disagree with the alignment the bubbles are actually sampled
against), it consumes ``grid_correct()``'s own robust line-matching
diagnostics - the exact same evidence used to place all 160 bubbles - and
turns them into a single 0-100 ``template_match`` score plus a strict
``valid`` verdict. It verifies:

  1. dimensions   - the warp produced exactly the canonical size the
                    template is defined in.
  2. answer grid  - the sheet's printed row AND column gridlines were
                    matched line-for-line against template.json
                    (grid_correct's ``row_full`` / ``col_solved``).
  3. registration - how tightly the matched gridlines sit on their
                    reference positions (grid_correct's residuals, in
                    canonical pixels) - residual perspective/scale error.
  4. outer border - (informational) the thick printed table border is
                    present as a dark band at the four expected edges.

A capture that fails validation should be REJECTED / retaken rather than
scored, since every bubble coordinate would otherwise be sampled off a
sheet that does not match the template.
"""
import numpy as np

# Residual (canonical px) at/above which registration is considered a
# total loss (score 0); 0px -> score 1. grid_correct only accepts a full
# per-line fit when its max residual is <= 12px, so this is a slightly
# looser normaliser for a graceful score rather than a hard cliff.
REG_TOL_PX = 15.0
# When only an anchor (outer-border-only) fit was possible, or a residual
# is unavailable, registration is treated as this neutral score.
REG_NEUTRAL = 0.6
# Thin band (canonical px) sampled around each expected outer-border line
# when checking (for information only) that the printed border is present.
BORDER_BAND_PX = 22
BORDER_DARK_RATIO = 1.20

# Acceptance gates. Deliberately strict: a rejected-and-retaken capture
# beats a silently mis-sampled one.
MIN_TEMPLATE_MATCH = 70.0


def _border_score(gray, ref_rows, ref_cols):
    """
    Fraction (0..1) of the four outer printed border lines present as a
    distinctly-dark band at their expected canonical position. Purely
    informational (surfaced in the debug detail) - it is NOT part of the
    accept/reject gate, because on many valid real photos the outer border
    sits right at the warped canvas edge and does not read as a strong
    interior dark band.
    """
    if not ref_rows or not ref_cols:
        return 0.0
    h, w = gray.shape[:2]
    darkness = 255.0 - gray.astype(np.float32)
    page_mean = float(darkness.mean()) + 1e-6

    def band_present(center, axis):
        lo = int(max(0, center - BORDER_BAND_PX))
        if axis == "row":
            band = darkness[lo:int(min(h, center + BORDER_BAND_PX)), :]
        else:
            band = darkness[:, lo:int(min(w, center + BORDER_BAND_PX))]
        return band.size > 0 and float(band.mean()) >= page_mean * BORDER_DARK_RATIO

    present = (
        band_present(ref_rows[0], "row") + band_present(ref_rows[-1], "row")
        + band_present(ref_cols[0], "col") + band_present(ref_cols[-1], "col")
    )
    return present / 4.0


def _registration_score(grid_diag):
    """Map grid_correct's matched-line residuals to a 0..1 tightness score."""
    resids = [
        r for r in (grid_diag.get("row_residual_px"), grid_diag.get("col_residual_px"))
        if r is not None
    ]
    if not resids:
        return REG_NEUTRAL
    mean_resid = float(np.mean(resids))
    return float(np.clip(1.0 - mean_resid / REG_TOL_PX, 0.0, 1.0))


def validate_template(warped_gray, template, grid_diag):
    """
    Validate a perspective-corrected grayscale sheet against `template`,
    using scan_omr.grid_correct()'s alignment diagnostics (`grid_diag`).

    Returns a dict:
      {
        "valid": bool,               # overall accept / reject verdict
        "template_match": float,     # 0-100 composite score
        "checks": {
            "dimensions_ok": bool,
            "grid_matched": bool,        # both axes matched by grid_correct
            "row_full": bool,            # every row gridline matched
            "col_solved": bool,          # every column gridline matched
            "row_residual_px": float | None,
            "col_residual_px": float | None,
            "registration_score": float, # 0..1, higher = tighter fit
            "border_score": float,        # 0..1, informational only
        },
        "reasons": [str, ...],       # human-readable failing checks
      }
    """
    grid_diag = grid_diag or {}
    canon_w, canon_h = template["canon_w"], template["canon_h"]
    ref_rows = template.get("ref_row_lines") or []
    ref_cols = template.get("ref_col_lines") or []

    reasons = []

    # 1) dimensions -----------------------------------------------------
    h, w = warped_gray.shape[:2]
    dimensions_ok = (w == canon_w and h == canon_h)
    if not dimensions_ok:
        reasons.append(f"corrected image is {w}x{h}, expected {canon_w}x{canon_h}")

    # 2) answer-grid match (from grid_correct) --------------------------
    matched = bool(grid_diag.get("matched", False))
    row_full = bool(grid_diag.get("row_full", False))
    col_solved = bool(grid_diag.get("col_solved", False))
    if not col_solved:
        reasons.append("column gridlines did not match the template")
    if not matched:
        reasons.append("row gridlines could not be matched against the template")
    elif not row_full:
        reasons.append("row gridlines only anchor-matched (internal rows not all recovered)")

    # 3) registration ---------------------------------------------------
    registration_score = _registration_score(grid_diag)

    # 4) border presence (informational) --------------------------------
    border_score = _border_score(warped_gray, ref_rows, ref_cols)

    # composite 0-100 score ---------------------------------------------
    row_score = 1.0 if row_full else (0.6 if matched else 0.0)
    col_score = 1.0 if col_solved else 0.0
    grid_score = (row_score + col_score) / 2.0
    template_match = 100.0 * (
        0.70 * grid_score
        + 0.20 * registration_score
        + 0.10 * (1.0 if dimensions_ok else 0.0)
    )
    template_match = round(float(template_match), 1)

    valid = (
        dimensions_ok
        and matched
        and col_solved
        and template_match >= MIN_TEMPLATE_MATCH
    )
    if template_match < MIN_TEMPLATE_MATCH:
        reasons.append(f"overall template match {template_match:.0f}% below "
                       f"{MIN_TEMPLATE_MATCH:.0f}% threshold")

    return {
        "valid": bool(valid),
        "template_match": template_match,
        "checks": {
            "dimensions_ok": bool(dimensions_ok),
            "grid_matched": matched,
            "row_full": row_full,
            "col_solved": col_solved,
            "row_residual_px": grid_diag.get("row_residual_px"),
            "col_residual_px": grid_diag.get("col_residual_px"),
            "registration_score": round(registration_score, 3),
            "border_score": round(border_score, 3),
        },
        "reasons": reasons,
    }
