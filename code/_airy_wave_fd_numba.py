"""
Airy wave FD solver with Numba JIT compilation.
Refactored as a reusable function for multi-location simulations.
Includes stability monitoring and warm-start checkpointing.
The idea is to make the airy wave simulation faster and more dependable
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from time import perf_counter
from numba import jit
from collections import deque
import imageio
from io import BytesIO
from PIL import Image
import os

from _fetch_buoy_functions import fetch_and_clean_buoy_data 
from _fetch_buoy_functions import init_from_buoy
from _3d_visualisation import plot_surf_3d

# ============================================================================
# NUMBA-COMPILED KERNEL (module-level, shared across all simulations)
# ============================================================================
@jit(nopython=True)
def fd_step_kernel(f, fd_coeff, damp_coeff, dt, dx):
    """
    One timestep of the finite difference update.
    Numba compiles this to machine code for 2-3x speedup.

    Parameters:
    -----------
    f : 3D array (ny, nx, 3)
        Solution array at three time levels [past, present, future]
    fd_coeff : 2D array (ny, nx)
        Pre-computed fd_coeff = celarity^2 * (dt^2/dx^2)
    damp_coeff : 2D array (ny, nx)
        Pre-computed damping coefficient
    dt, dx : float
        Timestep and grid spacing
    """
    ny, nx = f.shape[0], f.shape[1]

    # Compute Laplacians (5-point stencil)
    for i in range(1, ny-1):
        for j in range(1, nx-1):
            lap_x = f[i-1, j, 1] + f[i+1, j, 1] - 2 * f[i, j, 1]
            lap_y = f[i, j-1, 1] + f[i, j+1, 1] - 2 * f[i, j, 1]

            # Leapfrog finite difference update
            f[i, j, 2] = (
                -f[i, j, 0]
                + 2 * f[i, j, 1]
                + fd_coeff[i, j] * (lap_x + lap_y)
                - (dt**2 / dx) * damp_coeff[i, j] * (f[i, j, 1] - f[i, j, 0])
            )

# ============================================================================
# STABILITY VALIDATION FUNCTIONS
# ============================================================================
def validate_simulation_params(buoy_params, depth, dx, verbose=True):
    """
    Validate simulation parameters before starting.
    Returns (is_valid, message, details)
    """
    h, T, direction = buoy_params['h'], buoy_params['T'], buoy_params['direction']
    details = {}

    # Check 1: Wave height reasonable
    if h < 0.1 or h > 15:
        return False, f"❌ Wave height {h}m unrealistic (need 0.1-15m)", details

    # Check 2: Wave period reasonable
    if T < 2 or T > 30:
        return False, f"❌ Wave period {T}s unrealistic (need 2-30s)", details

    # Check 3: Grid has valid depths
    water_cells = depth < 0
    if not np.any(water_cells):
        return False, f"❌ All land (no water cells)", details
    if np.min(depth[water_cells]) < -5000:
        return False, f"❌ Unrealistic depths (< -5000m)", details

    # Check 4: Wavelength resolution
    L = 9.81 * T**2 / (2 * np.pi)
    ppw = L / dx
    details['wavelength'] = L
    details['ppw'] = ppw

    if ppw < 4:
        return False, f"❌ Too coarse: only {ppw:.1f} PPW (need ≥ 4)", details
    elif ppw < 10 and verbose:
        print(f"⚠️  WARNING: Only {ppw:.1f} PPW (< 10), may have dispersion")

    # Check 5: CFL condition
    c = 9.81 * T / (2 * np.pi)
    celarity_max = c * 1.2
    cfl_theoretical = celarity_max * (0.5 * dx / celarity_max) / dx
    details['cfl'] = cfl_theoretical

    if cfl_theoretical > 1.0:
        return False, f"❌ CFL violation: {cfl_theoretical:.3f} > 1.0", details

    if verbose:
        print(f"✓ All parameter validation checks passed")
        print(f"  Wavelength: {L:.1f}m")
        print(f"  PPW: {ppw:.1f}")
        print(f"  CFL: {cfl_theoretical:.4f}")

    return True, "All checks passed", details


def check_stability(f, dt, dx, celarity, k, threshold=1e3, verbose=False):
    """
    Monitor simulation for instability signs during integration.
    Returns (is_stable, message)
    """

    # Check 1: NaN/Inf
    if np.any(np.isnan(f)):
        return False, f"NaN detected at step {k}"
    if np.any(np.isinf(f)):
        return False, f"Inf detected at step {k}"

    # Check 2: Values too large (runaway growth)
    f_max = np.max(np.abs(f))
    if f_max > threshold:
        return False, f"Runaway growth: max value {f_max:.2e} > threshold {threshold:.2e}"

    # Check 3: CFL condition (double-check)
    cfl = np.max(celarity) * dt / dx
    if cfl > 1.0:
        return False, f"CFL violation at step {k}: {cfl:.3f} > 1.0"

    # Check 4: Energy trend (after warm-up)
    energy = np.sum(f[:, :, 1]**2)
    if k > 100 and energy > 1e10:
        return False, f"Unbounded energy growth at step {k}: {energy:.2e}"

    return True, f"Stable at step {k}"


# ============================================================================
# MAIN SIMULATION FUNCTION
# ============================================================================
def run_wave_simulation(buoy_id, bathymetry_file, output_dir,
                       previous_state_file=None,
                       nsteps=1000, last_n_frames=50, dx=10.0,
                       create_3d=True, verbose=True,
                       stability_check=True):
    """
    Run Airy wave finite-difference simulation with Numba JIT compilation.

    Parameters:
    -----------
    buoy_id : str
        NOAA buoy station ID (e.g., "51202")
    bathymetry_file : str
        Path to .npy file containing bathymetry grid
    output_dir : str
        Directory to save output GIF and results
    previous_state_file : str, optional
        Path to saved state from previous run (warm start)
    nsteps : int
        Number of simulation timesteps (default 1000)
    last_n_frames : int
        Number of final frames to save in GIF (default 50)
    dx : float
        Grid spacing in meters (default 10.0)
    create_3d : bool
        Whether to create 3D visualization (default True)
    verbose : bool
        Print progress messages (default True)
    stability_check : bool
        Monitor for instability during simulation (default True)

    Returns:
    --------
    dict : Simulation results with keys:
        - 'gif_path': Full path to output GIF
        - 'file_size_mb': Size of GIF in MB
        - 'grid_shape': (ny, nx) grid dimensions
        - 'buoy_params': dict with 'h', 'T', 'direction'
        - 'runtime': Total runtime in seconds
        - 'timings': dict with breakdown of timing
        - 'status': 'success' or 'failed'
        - 'error': Error message if failed
    """

    # Create output directory if needed
    os.makedirs(output_dir, exist_ok=True)

    # Timing infrastructure
    timer = {}
    timer['total'] = perf_counter()
    timer['setup'] = perf_counter()

    if verbose:
        print(f"\n{'='*70}")
        print(f"WAVE SIMULATION: {buoy_id}")
        print(f"{'='*70}")

    # ========== INITIALIZATION ==========
    buoy_params = init_from_buoy(buoy_id=buoy_id)
    h = buoy_params['h']/2
    T = buoy_params['T']
    wave_direction = buoy_params['direction']

    # Load bathymetry
    if verbose:
        print(f"Loading bathymetry from {bathymetry_file}...")
    depth = np.load(bathymetry_file).astype(np.float32)

    # ========== VALIDATION ==========
    if verbose:
        print("\nValidating simulation parameters...")
    is_valid, val_msg, val_details = validate_simulation_params(buoy_params, depth, dx, verbose=verbose)
    if not is_valid:
        print(val_msg)
        timer['total'] = perf_counter() - timer['total']
        return {
            'status': 'failed',
            'error': val_msg,
            'runtime': timer['total']
        }

    # Physics constants
    c = 9.8 * T / (2 * np.pi)
    L = c * T
    celarity = np.sqrt((9.8 / (2 * np.pi / L)) * np.tanh(np.abs(depth) * 2 * np.pi / L))
    celarity = np.nan_to_num(celarity, nan=0.0)
    celarity = np.clip(celarity, np.sqrt(9.8 * np.abs(depth)), c)

    dt = 0.5 * dx / np.max(celarity)

    # Pre-compute coefficients
    fd_coeff = celarity.astype(np.float32) ** 2 * (dt ** 2 / (dx ** 2))
    damp_coeff = np.clip(0.05 * L / ((depth**2)+.01), 0, 1).astype(np.float32)

    # Arrays
    land = depth >= 0
    celarity[land] = 0

    x = np.arange(0, depth.shape[1] * dx, dx)
    y = np.arange(0, depth.shape[0] * dx, dx)
    y_wave = np.arange(len(y), 0, -1) * dx
    x_wave = np.arange(len(x), 0, -1) * dx

    # ========== LOAD OR INITIALIZE STATE ==========
    if previous_state_file and os.path.exists(previous_state_file):
        if verbose:
            print(f"Loading previous state from {previous_state_file}...")
        try:
            f = np.load(previous_state_file).astype(np.float32)
            if f.shape != (len(y), len(x), 3):
                raise ValueError(f"State shape {f.shape} doesn't match grid {(len(y), len(x), 3)}")
            if verbose:
                print(f"  ✓ Warm start: using previous state (skipping propagation warm-up)")
        except Exception as e:
            print(f"⚠️  Failed to load previous state: {e}")
            print(f"  Falling back to cold start")
            f = np.zeros((len(y), len(x), 3), dtype=np.float32)
    else:
        f = np.zeros((len(y), len(x), 3), dtype=np.float32)
        if verbose:
            print("Cold start: initializing from zero")

    # Edge conditions
    trans_edge = np.zeros_like(depth, dtype=bool)
    recieve_edge = np.zeros_like(depth, dtype=bool)
    one_wave = 5 * int(np.ceil(L / dx))

    if np.sin(np.deg2rad(wave_direction)) <= 0:
        recieve_edge[:, -one_wave:] = True
        trans_edge[:, 0] = True
    else:
        trans_edge[:, -1] = True
        recieve_edge[:, :one_wave] = True
    if np.cos(np.deg2rad(wave_direction)) < 0:
        trans_edge[0, :] = True
        recieve_edge[-one_wave:, :] = True
    else:
        trans_edge[-1, :] = True
        recieve_edge[:one_wave, :] = True

    damp_coeff[recieve_edge] = 0.5
    damp_coeff = np.nan_to_num(damp_coeff, nan=0.0)

    # Wave parameters
    ang_v = 2 * np.pi / T
    ang_wavenumber = 2 * np.pi / L
    azy = [-np.sin(np.deg2rad(wave_direction)), -np.cos(np.deg2rad(wave_direction))]

    # Initial condition (only if cold start)
    if np.all(f == 0):
        f[1:-1, 1:-1, 1] = (
            f[1:-1, 1:-1, 0]
            + 0.5 * fd_coeff[1:-1, 1:-1] * (
                f[:-2, 1:-1, 0] + f[2:, 1:-1, 0] - 2 * f[1:-1, 1:-1, 0]
                + f[1:-1, :-2, 0] + f[1:-1, 2:, 0] - 2 * f[1:-1, 1:-1, 0]
            )
        )

    timer['setup'] = perf_counter() - timer['setup']
    if verbose:
        print(f"Setup complete: {timer['setup']:.3f}s")

    # ========== MAIN SIMULATION LOOP ==========
    if verbose:
        print(f"Running {nsteps} timesteps ({dx}m resolution, {len(y)}×{len(x)} grid)...\n")

    timer['simulation'] = perf_counter()
    st = 0.0

    # Numba compilation (first call is slow)
    if verbose:
        print("First iteration (Numba compilation)...")
    t0 = perf_counter()
    timer['first_call'] = 0

    # Use deque to keep only last N frames (memory-efficient)
    frame_buffer = deque(maxlen=last_n_frames)
    frame_times = deque(maxlen=last_n_frames)

    try:
        for k in range(nsteps):
            # Generate boundary waveform
            plain_wave = h * np.sin(
                x_wave[None, :] * ang_wavenumber * azy[0]
                + y_wave[:, None] * ang_wavenumber * azy[1]
                + st * ang_v
            ).astype(np.float32)
            f[trans_edge, 2] = plain_wave[trans_edge]

            # Call Numba-compiled kernel
            fd_step_kernel(f, fd_coeff, damp_coeff, dt, dx)

            # Leapfrog shift
            f[:, :, 0] = f[:, :, 1]
            f[:, :, 1] = f[:, :, 2]
            st += dt

            # Collect last N frames
            frame_buffer.append(f[:, :, 2].copy())
            frame_times.append(st)

            if k == 0:
                timer['first_call'] = perf_counter() - t0
                if verbose:
                    print(f"  → First iteration: {timer['first_call']*1000:.1f}ms (includes compilation)\n")

            # Stability check
            if stability_check and k % 50 == 0 and k > 0:
                is_stable, stab_msg = check_stability(f, dt, dx, celarity, k)
                if not is_stable:
                    print(f"\n❌ INSTABILITY DETECTED: {stab_msg}")
                    print(f"   Exiting at step {k}/{nsteps}")
                    # Save emergency checkpoint
                    emergency_file = os.path.join(output_dir, f"state_unstable_step_{k}.npy")
                    np.save(emergency_file, f)
                    print(f"   Emergency checkpoint saved: {emergency_file}")
                    break  # Exit loop gracefully, still create GIF below

    except Exception as e:
        print(f"❌ SIMULATION ERROR at step {k}: {e}")
        # Still try to create GIF with whatever frames we have
        print(f"   Creating GIF with available frames...")
        frames_to_save = list(frame_buffer)
        frame_times = list(frame_times)
        if len(frames_to_save) == 0:
            timer['total'] = perf_counter() - timer['total']
            return {
                'status': 'failed',
                'error': str(e),
                'runtime': timer['total'],
                'step_failed': k
            }

    timer['simulation'] = perf_counter() - timer['simulation']
    frames_to_save = list(frame_buffer)
    frame_times = list(frame_times)

    # ========== CREATE GIF (even on early exit) ==========
    timer['visualization'] = perf_counter()

    if verbose and len(frames_to_save) > 0:
        print(f"\nCreating GIF from {len(frames_to_save)} frames...\n")
    elif len(frames_to_save) == 0:
        print(f"\n⚠️  No frames to save, skipping GIF creation")
        timer['visualization'] = perf_counter() - timer['visualization']
        timer['total'] = perf_counter() - timer['total']
        return {
            'status': 'failed',
            'error': 'No frames collected',
            'runtime': timer['total']
        }

    gif_frames = []
    dpi = 80
    figsize = (10, 5)

    for idx, frame in enumerate(frames_to_save):
        fig = plt.figure(figsize=figsize, dpi=dpi)

        # Main plot
        ax1 = fig.add_subplot(121)
        ax1.imshow(land, origin="lower", cmap="binary", alpha=1)
        alpha_field = np.clip(frame, 0, h) / (h + 0.001)
        alpha_field = np.nan_to_num(alpha_field, nan=0)
        im = ax1.imshow(frame * 2, origin="lower", cmap="viridis_r",
                        vmin=0, vmax=3*h, alpha=alpha_field)
        ax1.set_title(f"Wave Field (t={frame_times[idx]:.1f}s)")
        ax1.set_xlabel("X (grid points)")
        ax1.set_ylabel("Y (grid points)")

        # Zoom plot
        ax2 = fig.add_subplot(122)
        zoom_frame = frame[450:700,500:750]
        im2 = ax2.imshow(zoom_frame, origin="lower", cmap="viridis_r",
                         vmin=-h, vmax=h)
        ax2.set_title("Detailed View")
        ax2.set_xlabel("X (local)")
        ax2.set_ylabel("Y (local)")
        plt.colorbar(im2, ax=ax2, label="Wave height (m)")

        plt.tight_layout()

        # Convert figure to image array
        buf = BytesIO()
        fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight')
        buf.seek(0)
        image = np.array(Image.open(buf).convert('RGB'))
        gif_frames.append(image)

        plt.close(fig)
        buf.close()

        if verbose and (idx + 1) % 10 == 0:
            print(f"  Rendered frame {idx+1}/{len(frames_to_save)}")

    # Save GIF
    gif_path = os.path.join(output_dir, "wave_simulation.gif")
    if verbose:
        print(f"\n  Saving optimized GIF to {gif_path}...")

    imageio.mimsave(
        gif_path,
        gif_frames,
        duration=0.1,  # 100ms per frame = 10 fps
        loop=0  # Loop forever
    )

    file_size_mb = os.path.getsize(gif_path) / (1024**2)
    if verbose:
        print(f"  ✓ Created GIF ({file_size_mb:.1f} MB, {len(gif_frames)} frames, 10 fps)")

    timer['visualization'] = perf_counter() - timer['visualization']

    # ========== SAVE STATE FOR NEXT RUN ==========
    checkpoint_file = os.path.join(output_dir, "state_checkpoint.npy")
    np.save(checkpoint_file, f)
    if verbose:
        print(f"✓ Saved checkpoint for next run: {checkpoint_file}")

    # ========== 3D VISUALIZATION (optional) ==========
    timer['3d'] = perf_counter()
    if create_3d and len(frames_to_save) > 0:
        if verbose:
            print(f"Creating 3D plot...")
        final_depth = depth[450:700,500:750],
        final_wave = frames_to_save[-1][450:700,500:750]
        plot_surf_3d(final_depth, np.asarray(final_wave), z_scale1=1, z_scale2=5,
                    background="white", clim2=[-3, 3])
    timer['3d'] = perf_counter() - timer['3d']

    timer['total'] = perf_counter() - timer['total']

    # Determine status based on whether we completed all steps
    early_exit = k < nsteps - 1 if 'k' in locals() else False
    status = 'completed_with_warning' if early_exit else 'success'

    # ========== RESULTS ==========
    if verbose:
        print("\n" + "="*70)
        print("RESULTS")
        print("="*70)
        print(f"Setup:             {timer['setup']:.3f}s")
        print(f"First iteration:   {timer['first_call']*1000:.1f}ms (Numba compilation)")
        print(f"Total simulation:  {timer['simulation']:.3f}s")
        print(f"  → Per-timestep:  {timer['simulation']/nsteps*1000:.2f}ms")
        print(f"Visualization:     {timer['visualization']:.3f}s")
        if create_3d:
            print(f"3D plotting:       {timer['3d']:.3f}s")
        print(f"TOTAL:             {timer['total']:.3f}s")
        print("="*70)

    result = {
        'status': status,
        'gif_path': gif_path,
        'file_size_mb': file_size_mb,
        'grid_shape': (len(y), len(x)),
        'buoy_params': buoy_params,
        'runtime': timer['total'],
        'checkpoint_file': checkpoint_file,
        'timings': timer
    }

    # Add emergency checkpoint path if instability was detected
    emergency_file = os.path.join(output_dir, f"state_unstable_step_{k if 'k' in locals() else 0}.npy")
    if os.path.exists(emergency_file):
        result['emergency_checkpoint'] = emergency_file

    return result


# ============================================================================
# EXAMPLE: Run single simulation (for backwards compatibility)
# ============================================================================
if __name__ == "__main__":
    result = run_wave_simulation(
        buoy_id="46087",
        bathymetry_file="data/the_dump.npy",
        output_dir="output/the_dump",
        nsteps=2000,
        last_n_frames=50,
        dx=10.0,
        stability_check=True
    )

    if result['status'] == 'success':
        print(f"\n✓ Simulation complete!")
        print(f"  GIF: {result['gif_path']}")
        print(f"  Size: {result['file_size_mb']:.1f} MB")
        print(f"  Grid: {result['grid_shape'][0]} × {result['grid_shape'][1]}")
        print(f"  Runtime: {result['runtime']:.1f}s")
    else:
        print(f"\n✗ Simulation failed!")
        print(f"  Error: {result['error']}")
        if 'emergency_checkpoint' in result:
            print(f"  Emergency checkpoint: {result['emergency_checkpoint']}")
