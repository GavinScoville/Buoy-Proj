"""
Master script: Run Airy wave simulations for all surfing locations.
Generates GIFs and results for website integration.
"""

from salish.models.airy_wave_fd_numba import run_wave_simulation
import pandas as pd
from datetime import datetime
from salish.core.config import load_pipeline_config
from salish.paths import BATHYMETRY, SIMULATIONS


def configured_locations():
    """The finite-difference locations listed in config/pipeline.yaml."""
    return load_pipeline_config()["models"]["finite_difference"]["locations"]


# ============================================================================
# RUN ALL SIMULATIONS
# ============================================================================
def run_all_simulations(verbose=True, use_warm_start=True, short_run=False,
                        locations=None, buoy_params=None, create_3d=True):
    """
    Run wave simulations for all locations, collect results.

    Parameters:
    -----------
    verbose : bool
        Print progress messages
    use_warm_start : bool
        Use checkpoint from previous run (warm start)
    short_run : bool
        Use fewer timesteps for quick testing
    locations : list of dict, optional
        Defaults to the locations in config/pipeline.yaml
    buoy_params : dict, optional
        buoy id -> {'h', 'T', 'direction'}, to reuse data already fetched
    create_3d : bool
        Open the interactive PyVista view after each run
    """
    if locations is None:
        locations = configured_locations()
    buoy_params = buoy_params or {}

    results = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"\n{'='*80}")
    print(f"RUNNING ALL WAVE SIMULATIONS - {timestamp}")
    if use_warm_start:
        print(f"Mode: WARM START (using previous checkpoints)")
    if short_run:
        print(f"Mode: SHORT RUN (reduced timesteps for testing)")
    print(f"{'='*80}\n")

    for location in locations:
        output_dir = SIMULATIONS / location['name']

        # Determine parameters
        nsteps = location.get('nsteps', 1000)
        if short_run:
            nsteps = min(200, nsteps)

        checkpoint_file = output_dir / "state_checkpoint.npy" if use_warm_start else None

        try:
            print(f"\nRunning: {location['name']} ({nsteps} steps)")
            print("-" * 70)

            result = run_wave_simulation(
                buoy_id=location['buoy'],
                bathymetry_file=BATHYMETRY / location['bathymetry'],
                output_dir=output_dir,
                previous_state_file=checkpoint_file,
                nsteps=nsteps,
                last_n_frames=50,
                dx=10.0,
                create_3d=create_3d,
                verbose=verbose,
                stability_check=True,
                buoy_params=buoy_params.get(location['buoy']),
                zoom_window=location.get('zoom_window')
            )

            # Add metadata
            result['location'] = location['name']
            result['description'] = location['description']
            result['timestamp'] = timestamp

            results.append(result)

            if result['status'] in ['success', 'completed_with_warning']:
                symbol = "✓" if result['status'] == 'success' else "⚠️ "
                print(f"\n{symbol} {location['name']}: {result['status'].upper()}")
                print(f"    GIF: {result['gif_path']}")
                print(f"    Size: {result['file_size_mb']:.1f} MB")
                print(f"    Runtime: {result['runtime']:.1f}s")
                if 'emergency_checkpoint' in result:
                    print(f"    Emergency checkpoint: {result['emergency_checkpoint']}")
            else:
                print(f"\n✗ {location['name']}: FAILED")
                print(f"    Error: {result.get('error', 'Unknown error')}")

        except Exception as e:
            print(f"\n✗ {location['name']}: EXCEPTION")
            print(f"    Error: {e}\n")
            results.append({
                'location': location['name'],
                'status': 'failed',
                'error': str(e),
                'timestamp': timestamp
            })

    return results


# ============================================================================
# SUMMARY REPORT
# ============================================================================
def generate_report(results):
    """Generate summary report of all simulations."""

    print(f"\n{'='*80}")
    print(f"SIMULATION SUMMARY")
    print(f"{'='*80}\n")

    # Convert to DataFrame for easy viewing
    df = pd.DataFrame(results)

    # Success summary (including early exits)
    if 'status' in df.columns:
        successful = df[df['status'].isin(['success', 'completed_with_warning'])]
    else:
        successful = df

    print(f"Completed simulations: {len(successful)}")
    print(f"\n{'Location':<20} {'Status':<20} {'Size (MB)':<12} {'Runtime (s)':<12}")
    print("-" * 65)

    for _, row in successful.iterrows():
        if 'gif_path' in row:
            status_str = row.get('status', 'unknown')
            print(f"{row.get('location', 'Unknown'):<20} {status_str:<20} {row['file_size_mb']:<12.1f} {row['runtime']:<12.1f}")

    # Failure summary
    if 'status' in df.columns:
        failed = df[df['status'] == 'failed']
        if len(failed) > 0:
            print(f"\nFailed simulations: {len(failed)}")
            for _, row in failed.iterrows():
                print(f"  ✗ {row['location']}: {row.get('error', 'Unknown error')}")

    # Total stats
    print(f"\nTotal runtime: {sum(r.get('runtime', 0) for r in results):.1f}s")
    print(f"Total GIF size: {sum(r.get('file_size_mb', 0) for r in results):.1f} MB")
    print("="*80)


# ============================================================================
# WEBSITE INTEGRATION
# ============================================================================
def generate_website_markdown(results):
    """Generate Markdown snippet for website integration."""

    output = "# Wave Simulation Results\n\n"

    for result in results:
        # Include both successful and early-exit runs
        if 'gif_path' in result and result['status'] in ['success', 'completed_with_warning']:
            output += f"## {result['location']}\n\n"
            output += f"**Description:** {result.get('description', 'N/A')}\n\n"
            output += f"![{result['location']} Wave Simulation]({result['gif_path']})\n\n"
            output += f"- **Size:** {result['file_size_mb']:.1f} MB\n"
            output += f"- **Grid:** {result['grid_shape'][0]}×{result['grid_shape'][1]} points\n"
            output += f"- **Wave Height:** {result['buoy_params']['h']:.2f} m\n"
            output += f"- **Wave Period:** {result['buoy_params']['T']:.1f} s\n"
            output += f"- **Direction:** {result['buoy_params']['direction']:.0f}°\n"
            output += f"- **Runtime:** {result['runtime']:.1f} seconds\n\n"

    # Save to file
    with open(SIMULATIONS / "results.md", "w") as f:
        f.write(output)

    print(f"\n✓ Website Markdown saved to: {SIMULATIONS / 'results.md'}")
    return output


# ============================================================================
# MAIN
# ============================================================================
if __name__ == "__main__":
    import sys

    # Parse arguments
    use_warm_start = '--cold' not in sys.argv
    short_run = '--short' in sys.argv
    verbose = '--quiet' not in sys.argv

    if '--help' in sys.argv:
        print("""
Usage: python run_all_simulations.py [options]

Options:
  --warm   : Use warm start from previous checkpoint (default: True)
  --cold   : Cold start (ignore previous checkpoints)
  --short  : Use reduced timesteps for quick testing
  --quiet  : Suppress verbose output
  --help   : Show this message

Examples:
  python run_all_simulations.py           # Warm start, full run
  python run_all_simulations.py --cold    # Cold start, full run
  python run_all_simulations.py --short   # Warm start, reduced timesteps
        """)
        sys.exit(0)

    # Run all simulations
    results = run_all_simulations(
        verbose=verbose,
        use_warm_start=use_warm_start,
        short_run=short_run
    )

    # Generate report
    generate_report(results)

    # Generate website markdown
    markdown = generate_website_markdown(results)

    print(f"\n✓ All simulations complete!")
    print(f"Results saved to {SIMULATIONS}/")

    # Print usage tips
    if use_warm_start:
        print(f"\n💡 Tip: For faster updates, use: python run_all_simulations.py")
    else:
        print(f"\n💡 Tip: For next time, use warm start: python run_all_simulations.py --warm")
