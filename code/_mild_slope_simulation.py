"""
Parabolic Mild-Slope Wave Model  (frequency domain, forward-marching)
=====================================================================

Propagates swell from the open Pacific across the Neah Bay bathymetry and
returns the steady-state wave-height field.

WHY THIS FORMULATION
--------------------
The full (elliptic) mild-slope equation of Berkhoff (1972) is

        div( c*cg * grad(eta) )  +  k^2 * c*cg * eta  =  0                (1)

where eta is the complex surface-elevation amplitude, c the phase speed,
cg the group velocity and k the local wavenumber.  Equation (1) is a
Helmholtz problem.  Our domain is ~80 km across and the swell wavelength is
~400 m, so the domain spans ~200 wavelengths.  Direct-solving an indefinite
Helmholtz problem of that size is genuinely hard (catastrophic LU fill-in),
which is why coastal models don't do it.

Instead we use the PARABOLIC APPROXIMATION (Radder 1979; Kirby & Dalrymple
1983 -- the basis of the REF/DIF model).  We split off the rapidly-varying
carrier phase in the propagation direction,

        eta(x,y) = A(x,y) * exp( i * integral_0^x kbar(x') dx' )          (2)

where kbar(x) is a reference wavenumber for that column and A is a SLOWLY
varying complex envelope.  Substituting (2) into (1) and dropping the
d/dx( P dA/dx ) term (the slowly-varying-envelope approximation, which is
exactly what discards back-scattered energy) leaves a first-order equation
in x that we MARCH shoreward:

    dA/dx = -[ d/dx(kbar*P) / (2*kbar*P) ] * A          <- shoaling
            + i * [ (k^2 - kbar^2) / (2*kbar) ] * A     <- refraction
            + i * [ 1/(2*kbar*P) ] * d/dy( P dA/dy )    <- diffraction
            - (w/2) * A                                 <- breaking        (3)

    with P = c*cg.

WHAT THIS BUYS US
  * Unconditionally stable (Crank-Nicolson); there is no CFL condition
    because there is no time axis at all -- x is the marching coordinate.
  * One tridiagonal solve per marching step => O(N) work, O(Ny) memory.
  * Refraction, shoaling and forward diffraction are all retained.

WHAT IT GIVES UP
  * Reflection / back-scatter (waves cannot travel back offshore).
  * Accuracy degrades for propagation more than ~45 deg off the marching
    axis.  Here the swell is 11 deg off-axis, so we are well inside that.
  * In very shallow water the phase term (k^2-kbar^2)/(2*kbar) accumulates
    many radians per step, so PHASE is unreliable there.  AMPLITUDE (which
    is what we care about) is carried by the shoaling and breaking terms
    and stays accurate.

WHY THE AMPLITUDE NO LONGER BLOWS UP
  The shoaling term in (3) integrates exactly to Green's law,
  A ~ cg^(-1/2), i.e. the textbook shoaling coefficient Ks = sqrt(cg0/cg).
  That alone grows without bound as cg -> 0 at the shoreline, so we add the
  physical process that actually stops it in nature: DEPTH-LIMITED BREAKING.
  Waves break once H/h exceeds gamma ~ 0.78, which caps H at gamma*h.
  This is a physical bound, not a clamp.

Run `python3 _mild_slope_simulation.py --validate` to check the scheme
against the analytic shoaling solution on a plane beach before trusting it.
"""

import argparse
import time

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.linalg import solve_banded

from _fetch_buoy_functions import fetch_and_clean_buoy_data

# ---------------------------------------------------------------------------
# Physical constants and model parameters
# ---------------------------------------------------------------------------
G = 9.81            # gravitational acceleration (m/s^2)
GAMMA_BREAK = 0.78  # McCowan depth-limited breaking index, H_max = gamma * h
K_BREAK = 1.0       # breaking dissipation strength, O(1) tuning constant
H_MIN = 0.5         # minimum water depth used in coefficients (m).
                    # As h -> 0, k -> inf and cg -> 0, so the coefficients in
                    # (3) become singular.  Clamping h keeps the march finite;
                    # cells with depth >= 0 are treated as dry regardless.
SPONGE_CELLS = 60   # width of the absorbing layer on the lateral (y) edges


# ===========================================================================
# STEP 1 -- Wave kinematics from the linear dispersion relation
# ===========================================================================
def wave_numbers(omega, h):
    """
    Solve the linear dispersion relation  omega^2 = g*k*tanh(k*h)  for k.

    There is no closed form, so we use Newton-Raphson on
        f(k) = omega^2 - g*k*tanh(k*h)
    starting from the deep-water root k = omega^2/g.  Five iterations is
    plenty; the function is smooth and monotone in k.

    Returns (k, c, cg):
        k  -- wavenumber        (rad/m)
        c  -- phase speed       = omega/k
        cg -- group velocity    = c/2 * (1 + 2kh/sinh(2kh))
              (this is the speed at which wave ENERGY travels, and it is the
              quantity that controls shoaling)
    """
    h = np.maximum(h, H_MIN)
    k = np.full_like(h, omega**2 / G)

    for _ in range(8):
        kh = k * h
        t = np.tanh(kh)
        f = omega**2 - G * k * t
        df = -G * (t + kh * (1.0 - t * t))
        k = k - f / df

    c = omega / k
    kh = k * h
    # 2kh/sinh(2kh) -> 1 as kh->0 (shallow) and -> 0 as kh->inf (deep).
    # Evaluate it in a way that stays finite for large kh.
    ratio = np.where(kh < 20.0, 2.0 * kh / np.sinh(np.minimum(2.0 * kh, 40.0)), 0.0)
    cg = 0.5 * c * (1.0 + ratio)
    return k, c, cg


# ===========================================================================
# STEP 2 -- One Crank-Nicolson marching step
# ===========================================================================
def march_step(A, dx, dy, kbar_0, kbar_1, k1, P0, P1, wet0, wet1, w, sigma):
    """
    Advance the complex envelope A by one step in x, from column j to j+1,
    by applying Crank-Nicolson to equation (3):

        (A1 - A0)/dx = 1/2 * [ L(A1) + L(A0) ]

    which rearranges to the tridiagonal system

        (I - dx/2 * L) A1  =  (I + dx/2 * L) A0

    The operator L has three pieces, evaluated at the midpoint j+1/2:

      S  (real)      shoaling + breaking dissipation
      D  (imaginary) refraction / phase, from (k^2 - kbar^2)/(2 kbar)
      T  (imaginary) diffraction, the tridiagonal y-operator
                     d/dy( P dA/dy ) / (2 kbar P)

    Because D and T enter as pure imaginary coefficients the scheme is
    unitary in those terms (it rotates phase without changing magnitude),
    and S is non-positive.  Hence the march is unconditionally stable --
    there is no step-size restriction to satisfy.
    """
    ny = A.shape[0]

    # --- Midpoint coefficients ------------------------------------------
    kbar_h = 0.5 * (kbar_0 + kbar_1)
    P_h = 0.5 * (P0 + P1)
    wet = wet0 & wet1

    # Guard the denominators on dry cells; those rows get overwritten below.
    kP_h = np.where(wet, kbar_h * P_h, 1.0)

    # --- S: shoaling + breaking ------------------------------------------
    # d/dx(kbar*P) / (2*kbar*P).  Integrating dA/dx = -S_shoal*A gives
    # A ~ (kbar*P)^(-1/2); since kbar*P = k*c*cg = omega*cg, that is
    # A ~ cg^(-1/2), i.e. exactly Green's law / the shoaling coefficient.
    # sigma is the lateral sponge, carried here as a RATE (1/m) rather than
    # applied as a per-step multiply.  That distinction matters: a per-step
    # multiply compounds with the number of steps, so its total absorption
    # would depend on dx instead of on distance travelled.
    dkP = (kbar_1 * P1 - kbar_0 * P0) / dx
    S = -dkP / (2.0 * kP_h) - 0.5 * w - sigma
    S = np.where(wet, S, 0.0)

    # --- D: refraction / phase -------------------------------------------
    # Local k differs from the column reference kbar wherever the depth
    # differs from the column mean; that phase difference is what bends
    # the wave crests toward shallow water.
    D = np.where(wet, (k1 * k1 - kbar_h * kbar_h) / (2.0 * kbar_h), 0.0)

    # --- T: diffraction ---------------------------------------------------
    # Conservative (flux-form) discretisation of d/dy( P dA/dy ):
    #   [ P_{i+1/2}(A_{i+1}-A_i) - P_{i-1/2}(A_i-A_{i-1}) ] / dy^2
    # Setting the face value P to zero where either neighbour is dry gives a
    # no-flux (fully reflecting) wall at the coastline, which is the correct
    # condition for a solid boundary.
    Pf_up = np.zeros(ny)      # face between i and i+1
    Pf_up[:-1] = np.where(wet[:-1] & wet[1:], 0.5 * (P_h[:-1] + P_h[1:]), 0.0)
    Pf_dn = np.zeros(ny)      # face between i-1 and i
    Pf_dn[1:] = Pf_up[:-1]

    denom = 2.0 * kP_h * dy * dy
    t_up = Pf_up / denom
    t_dn = Pf_dn / denom

    # --- Assemble the tridiagonal system ----------------------------------
    half = 0.5 * dx
    diag_L = S + 1j * (D - t_up - t_dn)
    off_up_L = 1j * t_up
    off_dn_L = 1j * t_dn

    # Right-hand side: (I + dx/2 * L) A0
    rhs = A + half * (diag_L * A)
    rhs[:-1] += half * off_up_L[:-1] * A[1:]
    rhs[1:] += half * off_dn_L[1:] * A[:-1]

    # Left-hand side matrix in scipy banded storage:
    #   ab[0, 1:]  = super-diagonal
    #   ab[1, :]   = diagonal
    #   ab[2, :-1] = sub-diagonal
    ab = np.zeros((3, ny), dtype=complex)
    ab[1] = 1.0 - half * diag_L
    ab[0, 1:] = -half * off_up_L[:-1]
    ab[2, :-1] = -half * off_dn_L[1:]

    # Dry cells: replace the row with the identity and force A = 0.
    dry = ~wet
    if dry.any():
        ab[1, dry] = 1.0
        ab[0, 1:][dry[:-1]] = 0.0
        ab[2, :-1][dry[1:]] = 0.0
        rhs[dry] = 0.0

    return solve_banded((1, 1), ab, rhs)


# ===========================================================================
# STEP 3 -- The full shoreward march
# ===========================================================================
def run_model(depth, dx, dy, H0, T, theta_deg, cap_ratio=2.0, progress=True,
              sponge_strength=0.02):
    """
    March the envelope A from the offshore boundary (x = 0, column 0) to the
    far side of the domain, one column at a time.

    depth      2-D array, NEGATIVE under water, positive on land
    theta_deg  incident direction measured from the +x marching axis,
               positive toward +y
    cap_ratio  explicit guardrail on H / H0 (see note in the summary)

    Returns a dict with the wave-height field and breaking diagnostics.
    """
    ny, nx = depth.shape
    omega = 2.0 * np.pi / T

    h = np.where(depth < 0.0, -depth, 0.0)   # still-water depth, >= 0
    wet_all = depth < 0.0

    # Output field: significant wave height H = 2|A|, float32 to keep the
    # full-resolution result in a reasonable amount of memory.
    Hfield = np.zeros((ny, nx), dtype=np.float32)

    # Column-0 kinematics and the initial envelope.
    k0, c0, cg0 = wave_numbers(omega, h[:, 0])
    wet0 = wet_all[:, 0]
    kbar_0 = k0[wet0].mean() if wet0.any() else omega**2 / G

    # A plane wave at angle theta to the marching axis is
    #   eta = a * exp( i k (x cos(theta) + y sin(theta)) ),
    # so after factoring out the carrier the envelope at x = 0 carries the
    # alongshore phase ramp exp( i kbar sin(theta) y ).
    y = np.arange(ny) * dy
    theta = np.deg2rad(theta_deg)
    A = (H0 / 2.0) * np.exp(1j * kbar_0 * np.sin(theta) * y)
    A[~wet0] = 0.0

    Hfield[:, 0] = 2.0 * np.abs(A)
    P0 = c0 * cg0

    # Absorbing sponge on the lateral (y) edges.  The outermost faces carry
    # a no-flux condition, which is a perfectly reflecting wall, so without
    # a sponge any energy that refracts sideways would bounce back in.
    #
    # sigma is a damping RATE (1/m) folded into the operator, scaled by the
    # wavenumber so it absorbs over a comparable number of wavelengths at
    # any period.  The raised-cosine profile keeps the onset smooth; a sharp
    # sponge edge acts like a diffracting knife edge and radiates ripples
    # back into the interior.  Width is capped at a fraction of the grid so
    # the two tapers can never overlap on a narrow domain.
    ns = int(min(SPONGE_CELLS, max(1, ny // 8)))
    sigma = np.zeros(ny)
    if sponge_strength > 0.0:
        ramp = np.linspace(0.0, 1.0, ns)
        taper = 0.5 * (1.0 - np.cos(np.pi * ramp))   # smooth 0 -> 1
        prof = sponge_strength * kbar_0
        sigma[:ns] = prof * taper[::-1]
        sigma[-ns:] = prof * taper

    n_break_cells = 0
    n_cap_cells = 0
    n_wet_cells = 0
    t_start = time.time()

    for j in range(nx - 1):
        if progress and j % 500 == 0:
            print(f"    column {j:5d}/{nx}   ({100.0*j/nx:4.1f}%)")

        hj1 = h[:, j + 1]
        wet1 = wet_all[:, j + 1]
        k1, c1, cg1 = wave_numbers(omega, hj1)
        P1 = c1 * cg1
        kbar_1 = k1[wet1].mean() if wet1.any() else kbar_0

        # --- Breaking dissipation rate -----------------------------------
        # Evaluated from the CURRENT height (lagged), which is standard and
        # stable because the dissipation varies slowly compared with the
        # step size.  w ramps up smoothly once H exceeds gamma*h, so the
        # wave is damped back toward the saturated value rather than being
        # discontinuously chopped.
        Hnow = 2.0 * np.abs(A)
        with np.errstate(divide="ignore", invalid="ignore"):
            beta = np.where(wet1, Hnow / np.maximum(GAMMA_BREAK * hj1, 1e-6), 0.0)
        w = K_BREAK * kbar_1 * np.maximum(0.0, beta * beta - 1.0)

        A = march_step(A, dx, dy, kbar_0, kbar_1, k1, P0, P1,
                       wet_all[:, j], wet1, w, sigma)

        A[~wet1] = 0.0

        # --- Saturation: enforce the breaking limit exactly ---------------
        # The dissipation term above does nearly all the work; this is a
        # backstop that guarantees H never exceeds the physical breaking
        # height even if the march momentarily overshoots between steps.
        Hnew = 2.0 * np.abs(A)
        Hbreak = GAMMA_BREAK * hj1
        over = wet1 & (Hnew > Hbreak)
        if over.any():
            A[over] *= Hbreak[over] / Hnew[over]
            n_break_cells += int(over.sum())

        # --- Explicit guardrail on total amplification --------------------
        # NOTE: unlike breaking, this is NOT physics -- it is a hard cap.
        # It is instrumented so we can report how often it actually binds.
        # If it never binds, the breaking term alone bounded the solution.
        Hnew = 2.0 * np.abs(A)
        cap = cap_ratio * H0
        hot = wet1 & (Hnew > cap)
        if hot.any():
            A[hot] *= cap / Hnew[hot]
            n_cap_cells += int(hot.sum())

        n_wet_cells += int(wet1.sum())
        Hfield[:, j + 1] = 2.0 * np.abs(A)

        kbar_0, P0 = kbar_1, P1

    return {
        "H": Hfield,
        "elapsed": time.time() - t_start,
        "n_break_cells": n_break_cells,
        "n_cap_cells": n_cap_cells,
        "n_wet_cells": n_wet_cells,
    }


# ===========================================================================
# STEP 4 -- Directional spreading
# ===========================================================================
def spreading_weights(n, s):
    """
    Build a discrete directional spectrum using the standard cosine-power
    form  D(theta) ~ cos^(2s)( (theta - theta0) / 2 ).

    WHY THIS MATTERS HERE
    ---------------------
    A single unidirectional wave train produces CAUSTICS: places where
    refracted rays cross and the predicted amplitude spikes.  Real swell is
    never unidirectional -- it arrives with a directional spread of order
    +/-15-20 deg -- and neighbouring directions focus at DIFFERENT points,
    so in nature the caustic is smeared out.  Modelling one direction only
    therefore over-predicts peak wave height at focal spots, sometimes by
    several times.  This is a limitation of the assumption, not of the
    numerics.

    Because the model is linear, the components are independent and their
    ENERGIES add, so we march each direction separately and combine as
        H_total = sqrt( sum_i weight_i * H_i^2 ).

    Larger s = narrower spread.  s ~ 20 is representative of swell;
    s ~ 5-10 is more like wind sea.  n = 1 recovers the unidirectional case.

    Returns (offsets_deg, weights) with weights summing to 1.
    """
    if n <= 1:
        return np.array([0.0]), np.array([1.0])

    # Circular standard deviation of the cos^(2s) distribution.
    sigma = np.degrees(np.sqrt(2.0 / (s + 1.0)))
    half = min(2.0 * sigma, 60.0)          # sample out to ~2 sigma
    offs = np.linspace(-half, half, n)

    w = np.cos(np.deg2rad(offs) / 2.0) ** (2.0 * s)
    return offs, w / w.sum()


# ===========================================================================
# VALIDATION -- analytic shoaling on a plane beach
# ===========================================================================
def validate():
    """
    Check the marching scheme against theory on a case with a known answer.

    Setup: a beach whose depth varies only in x (200 m -> 3 m), normally
    incident waves, no alongshore variation.  With no refraction and no
    diffraction, equation (3) reduces to pure shoaling, whose exact
    solution is Green's law:

        H(x) / H0  =  sqrt( cg(0) / cg(x) )       (the shoaling coefficient)

    If the discretisation is right, the marched result must reproduce this
    to within truncation error.  Depths are kept deep enough that the
    breaking limiter never activates, so we are testing the shoaling term
    in isolation.
    """
    print("=" * 70)
    print("VALIDATION -- plane beach, normal incidence, shoaling only")
    print("=" * 70)

    # The domain is made wide in y so the lateral sponge stays far from the
    # centreline where we sample the profile.
    nx, ny = 2000, 400
    dx = dy = 10.0
    T, H0 = 12.0, 1.0
    omega = 2.0 * np.pi / T

    # Depth 200 m -> 3 m, constant alongshore. Deep enough that
    # H stays well below gamma*h, so no breaking contaminates the test.
    prof = np.linspace(200.0, 3.0, nx)
    depth = -np.tile(prof, (ny, 1))

    # The sponge is switched off for this test.  With uniform alongshore
    # depth, a uniform envelope and no-flux lateral walls, the diffraction
    # operator annihilates the (constant) transverse profile exactly, so the
    # solution must stay uniform in y and the only thing that can change the
    # amplitude is the shoaling term -- which is precisely what we want to
    # measure against Green's law.
    out = run_model(depth, dx, dy, H0, T, theta_deg=0.0,
                    cap_ratio=1e9, progress=False, sponge_strength=0.0)

    # Analytic shoaling coefficient
    _, _, cg = wave_numbers(omega, prof)
    H_exact = H0 * np.sqrt(cg[0] / cg)

    mid = ny // 2
    H_num = out["H"][mid, :]

    err = np.abs(H_num - H_exact) / H_exact
    print(f"  grid                : {ny} x {nx} at dx = {dx:.0f} m")
    print(f"  depth range         : {prof[0]:.0f} m -> {prof[-1]:.0f} m")
    print(f"  breaking activations: {out['n_break_cells']}  (expect 0)")
    print()
    print(f"  {'x (km)':>8} {'h (m)':>8} {'H numeric':>11} {'H exact':>10} {'rel err':>9}")
    for idx in [0, nx // 4, nx // 2, 3 * nx // 4, nx - 1]:
        print(f"  {idx*dx/1000:8.2f} {prof[idx]:8.1f} "
              f"{H_num[idx]:11.4f} {H_exact[idx]:10.4f} {err[idx]:9.2e}")
    print()
    print(f"  max relative error  : {err.max():.3e}")
    print(f"  final shoaling gain : {H_num[-1]/H0:.4f}  "
          f"(theory {H_exact[-1]/H0:.4f})")

    ok = err.max() < 1e-3
    print()
    print("  RESULT: " + ("PASS" if ok else "FAIL"))
    print("=" * 70)
    return ok


# ===========================================================================
# Buoy input
# ===========================================================================
def get_buoy_params(buoy_id="46087"):
    """
    Pull the most recent complete (height, period, direction) record.

    NDBC fields:
      WVHT -- significant wave height Hs (m)
      DPD  -- dominant wave period (s)
      MWD  -- mean wave direction, degrees clockwise from true north,
              given as the direction the waves are coming FROM.
    """
    try:
        df = fetch_and_clean_buoy_data(buoy_id)
        if df is None or df.empty:
            raise ValueError("empty dataframe")
        for idx in range(len(df) - 1, -1, -1):
            row = df.iloc[idx]
            hs, tp, mwd = row.get("WVHT"), row.get("DPD"), row.get("MWD")
            if pd.notna(hs) and pd.notna(tp) and pd.notna(mwd):
                return float(hs), float(tp), float(mwd)
        raise ValueError("no complete wave record found")
    except Exception as exc:
        print(f"    warning: buoy fetch failed ({exc}); using defaults")
        return 2.0, 12.0, 260.0


def incident_angle_from_mwd(mwd_deg):
    """
    Convert an NDBC mean wave direction into an angle relative to the +x
    marching axis.

    Grid orientation (confirmed from _clean_bathymetric.py, which builds the
    grid as lon_min + arange(...) and lat_min + arange(...)):
        +x = east, +y = north, and the open Pacific is the x = 0 edge.

    MWD is the direction waves come FROM, clockwise from true north, so the
    direction of TRAVEL is mwd - 180.  A travel bearing b has components
        east  = sin(b),  north = cos(b)
    and the angle off the +x (east) axis is atan2(north, east).
    """
    bearing = np.deg2rad(mwd_deg - 180.0)
    east, north = np.sin(bearing), np.cos(bearing)
    return np.degrees(np.arctan2(north, east)), east


# ===========================================================================
# Main
# ===========================================================================
def main():
    ap = argparse.ArgumentParser(description="Parabolic mild-slope wave model")
    ap.add_argument("--validate", action="store_true",
                    help="run the analytic plane-beach check and exit")
    ap.add_argument("--subsample", type=int, default=2,
                    help="grid coarsening factor (1 = full 10 m resolution)")
    ap.add_argument("--buoy", default="46087", help="NDBC buoy id")
    ap.add_argument("--cap", type=float, default=2.0,
                    help="hard guardrail on H/H0")
    ap.add_argument("--spread", type=int, default=9,
                    help="number of directional components (1 = unidirectional)")
    ap.add_argument("--spread-s", type=float, default=20.0,
                    help="cos^2s spreading exponent; higher = narrower "
                         "(~20 swell, ~8 wind sea)")
    args = ap.parse_args()

    if args.validate:
        raise SystemExit(0 if validate() else 1)

    print("=" * 70)
    print("PARABOLIC MILD-SLOPE WAVE MODEL -- Neah Bay")
    print("=" * 70)

    # --- Bathymetry ------------------------------------------------------
    depth_full = np.load("data/salish_sea_bathymetry.npy")
    s = max(1, args.subsample)
    depth = np.ascontiguousarray(depth_full[::s, ::s], dtype=np.float64)
    dx = dy = 10.0 * s
    ny, nx = depth.shape

    print(f"\n[1] Bathymetry")
    print(f"    full resolution : {depth_full.shape} at 10 m")
    print(f"    working grid    : {depth.shape} at {dx:.0f} m")
    print(f"    domain          : {nx*dx/1000:.1f} km (E-W) x {ny*dy/1000:.1f} km (N-S)")
    print(f"    depth range     : {depth.min():.1f} m to {depth.max():.1f} m")
    print(f"    wet fraction    : {100.0*(depth < 0).mean():.1f}%")
    print(f"    offshore edge   : x=0 column is {100.0*(depth[:, 0] < 0).mean():.0f}% water, "
          f"mean depth {depth[:, 0][depth[:, 0] < 0].mean():.0f} m")

    # --- Buoy ------------------------------------------------------------
    Hs, T, mwd = get_buoy_params(args.buoy)
    theta_deg, east_comp = incident_angle_from_mwd(mwd)

    print(f"\n[2] Incident sea state (NDBC {args.buoy})")
    print(f"    Hs              : {Hs:.2f} m")
    print(f"    period          : {T:.1f} s")
    print(f"    MWD (from)      : {mwd:.0f} deg true")
    print(f"    travel bearing  : {(mwd-180)%360:.0f} deg true")
    print(f"    angle off +x    : {theta_deg:+.1f} deg")

    if east_comp <= 0:
        print("    WARNING: this swell travels westward, away from the shore")
        print("             the model marches toward. Results are not meaningful.")

    # --- Kinematics summary ---------------------------------------------
    omega = 2.0 * np.pi / T
    print(f"\n[3] Wave kinematics")
    print(f"    deep-water wavelength : {2*np.pi*G/omega**2:.0f} m")
    print(f"    deep-water phase speed: {G*T/(2*np.pi):.1f} m/s")
    print(f"    deep-water group speed: {G*T/(4*np.pi):.1f} m/s")
    print(f"    domain spans          : ~{nx*dx/(2*np.pi*G/omega**2):.0f} wavelengths")

    # --- March -----------------------------------------------------------
    offs, wts = spreading_weights(args.spread, args.spread_s)
    print(f"\n[4] Marching shoreward ({nx} columns, tridiagonal solve each)")
    if len(offs) > 1:
        print(f"    directional spectrum: {len(offs)} components, cos^2s with s={args.spread_s:.0f}")
        print(f"    spanning {offs[0]:+.1f} to {offs[-1]:+.1f} deg about the mean direction")
    else:
        print("    unidirectional (no spreading) -- expect over-focused caustics")

    # Energy accumulator.  The model is linear, so components superpose in
    # ENERGY (H^2), not in height.
    energy = np.zeros(depth.shape, dtype=np.float32)
    t0 = time.time()
    n_break = n_wet = 0

    # The parabolic approximation loses accuracy beyond ~45 deg off the
    # marching axis, so drop any spectral component outside that cone and
    # renormalise the remaining weights.  Silently marching a 60-deg
    # component would quietly contaminate the result.
    keep = np.abs(theta_deg + offs) <= 45.0
    if not keep.all():
        print(f"    dropping {int((~keep).sum())} component(s) beyond 45 deg "
              f"off-axis (outside parabolic validity)")
        offs, wts = offs[keep], wts[keep]
        wts = wts / wts.sum()

    for i, (off, wt) in enumerate(zip(offs, wts)):
        # Each component carries its own share of the total energy, so its
        # height is Hs * sqrt(weight).
        Hc = Hs * np.sqrt(wt)
        print(f"    component {i+1}/{len(offs)}: {theta_deg+off:+6.1f} deg, "
              f"weight {wt:.3f}")
        # No cap on individual components; the cap and the breaking
        # saturation are applied to the combined field below, since those
        # are properties of the total sea state rather than of one
        # spectral component.
        r = run_model(depth, dx, dy, Hc, T, theta_deg + off,
                      cap_ratio=1e9, progress=False)
        energy += r["H"] ** 2
        n_break += r["n_break_cells"]
        n_wet = r["n_wet_cells"]

    H = np.sqrt(energy)
    elapsed = time.time() - t0

    wet = depth < 0
    h_depth = np.where(wet, -depth, 0.0)

    # --- Depth-limited breaking on the combined sea state -----------------
    # Breaking is nonlinear, so it acts on the total height rather than on
    # each component separately. H cannot exceed gamma * h.
    Hbreak = (GAMMA_BREAK * h_depth).astype(np.float32)
    over = wet & (H > Hbreak)
    n_break_total = int(over.sum())
    H[over] = Hbreak[over]

    # --- Explicit guardrail ------------------------------------------------
    cap = args.cap * Hs
    hot = wet & (H > cap)
    n_cap_total = int(hot.sum())
    H[hot] = cap

    Hw = H[wet]
    print(f"    done in {elapsed:.1f} s")

    # --- Results ---------------------------------------------------------
    print(f"\n[5] Wave height field")
    print(f"    offshore Hs        : {Hs:.2f} m")
    print(f"    max Hs in domain   : {Hw.max():.2f} m")
    print(f"    max amplification  : {Hw.max()/Hs:.2f}x")
    print(f"    mean Hs (wet)      : {Hw.mean():.2f} m")
    print(f"    95th pct Hs        : {np.percentile(Hw, 95):.2f} m")

    n_tot = int(wet.sum())
    frac_break = 100.0 * n_break_total / max(n_tot, 1)
    frac_cap = 100.0 * n_cap_total / max(n_tot, 1)
    print(f"\n[6] What bounded the solution")
    print(f"    depth-limited breaking (H <= {GAMMA_BREAK}h) bound {frac_break:.3f}% of wet cells")
    print(f"    hard {args.cap:.1f}x guardrail bound            {frac_cap:.3f}% of wet cells")
    if n_cap_total == 0:
        print("    -> the guardrail never engaged. Directional spreading and")
        print("       breaking bounded the field on their own, so the limit")
        print("       you are seeing is physical rather than clipped.")
    else:
        print("    -> the guardrail still engaged on the cells above. Those are")
        print("       clipped values, not physical ones. Widening the spread")
        print("       (--spread-s lower) will smear the remaining caustics.")

    plot(depth, H, Hs, T, mwd, dx, dy, args.cap)

    print("\n" + "=" * 70)
    print("DONE")
    print("=" * 70)


def plot(depth, H, Hs, T, mwd, dx, dy, cap):
    """Render the wave field alongside the bathymetry and kinematics."""
    print(f"\n[7] Plotting")

    # Downsample for rendering; contouring 10^7 cells is pointless at
    # figure resolution and very slow.
    target = 1200
    s = max(1, max(depth.shape) // target)
    d = depth[::s, ::s]
    h = H[::s, ::s]
    ny, nx = d.shape
    xk = np.arange(nx) * dx * s / 1000.0
    yk = np.arange(ny) * dy * s / 1000.0
    wet = d < 0

    omega = 2.0 * np.pi / T
    _, c, cg = wave_numbers(omega, np.where(wet, -d, H_MIN))

    fig, axes = plt.subplots(2, 2, figsize=(17, 12))

    # Wave height
    ax = axes[0, 0]
    hm = np.ma.array(h, mask=~wet)
    im = ax.pcolormesh(xk, yk, hm, cmap="turbo", shading="auto",
                       vmin=0, vmax=min(cap * Hs, hm.max()))
    ax.contour(xk, yk, d, levels=[0], colors="k", linewidths=0.6)
    ax.set_title(f"Significant wave height (m)\n"
                 f"offshore Hs={Hs:.2f} m, T={T:.0f} s, from {mwd:.0f}°")
    fig.colorbar(im, ax=ax, label="Hs (m)")

    # Amplification
    ax = axes[0, 1]
    amp = np.ma.array(h / Hs, mask=~wet)
    im = ax.pcolormesh(xk, yk, amp, cmap="magma", shading="auto", vmin=0, vmax=cap)
    ax.contour(xk, yk, d, levels=[0], colors="w", linewidths=0.6)
    ax.set_title(f"Amplification  Hs / Hs_offshore\n(colour saturates at the {cap:.0f}x guardrail)")
    fig.colorbar(im, ax=ax, label="Hs / Hs0")

    # Bathymetry
    ax = axes[1, 0]
    dm = np.ma.array(d, mask=~wet)
    im = ax.pcolormesh(xk, yk, dm, cmap="Blues_r", shading="auto")
    ax.contour(xk, yk, d, levels=[0], colors="k", linewidths=0.6)
    ax.set_title("Bathymetry (m, negative = below sea level)")
    fig.colorbar(im, ax=ax, label="depth (m)")

    # Group velocity -- the field that drives shoaling
    ax = axes[1, 1]
    cgm = np.ma.array(cg, mask=~wet)
    im = ax.pcolormesh(xk, yk, cgm, cmap="viridis", shading="auto")
    ax.contour(xk, yk, d, levels=[0], colors="w", linewidths=0.6)
    ax.set_title("Group velocity $c_g$ (m/s)\nshoaling gain goes as $c_g^{-1/2}$")
    fig.colorbar(im, ax=ax, label="c_g (m/s)")

    for ax in axes.ravel():
        ax.set_xlabel("east (km)")
        ax.set_ylabel("north (km)")
        ax.set_aspect("equal")

    fig.tight_layout()
    fig.savefig("plots/mild_slope_simulation.png", dpi=140, bbox_inches="tight")
    plt.close(fig)
    print("    saved plots/mild_slope_simulation.png")


if __name__ == "__main__":
    main()
