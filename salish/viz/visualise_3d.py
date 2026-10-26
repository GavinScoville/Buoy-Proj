import os
import platform

import numpy as np
import pyvista as pv


def _ensure_headless_display():
    """On a Linux box with no X display (CI, cron), start a virtual one so
    VTK can create an off-screen render window. No-op everywhere else."""
    if platform.system() == "Linux" and not os.environ.get("DISPLAY"):
        try:
            pv.start_xvfb()
        except OSError:
            pass


def plot_surf_3d(
    array1 = None,
    array2 = None,
    dx=10,
    z_scale1=4,
    z_scale2=4,
    cmap1="Greys_r",
    cmap2="viridis",
    opacity1=1.0,
    opacity2=0.7,
    background="black",
    show_edges=False,
    clim1=[0,100],
    clim2=[-3, 3],
    html_path=None,
    png_path=None,
    window_size=(1600, 1100),
    interactive=False,
):
    """
    Plotting two 2D arrays as warped 3D surfaces in PyVista.

    Parameters
    ----------
    array1, array2 : 2D numpy arrays
        Arrays containing elevation/depth/height values.
    dx : float
        Grid spacing in x and y directions.
    z_scale1, z_scale2 : float
        Vertical exaggeration factors for each array.
    cmap1, cmap2 : str
        Colormaps for each surface.
    h: clim: height to color waves
    opacity1, opacity2 : float
        Opacity of each surface.
    html_path : str or Path, optional
        If given, export an interactive HTML view of the scene here.
    png_path : str or Path, optional
        If given, save a still render of the scene here. The Markdown report
        embeds this, since Markdown cannot render the interactive HTML inline.
    window_size : (int, int)
        Render size in pixels; sets the resolution of the still.
    interactive : bool
        Open a live PyVista window (blocks; needs a display). Default False
        so this is safe to call from an automated pipeline run.
    """

    if array1 is None or array2 is None:
        raise ValueError("array1 and array2 must be provided")

    array1 = np.asarray(array1)
    array2 = np.asarray(array2)

    if array1.shape != array2.shape:
        raise ValueError("array1 and array2 must have the same shape.")

    ny, nx = array1.shape

    x = np.arange(0, nx * dx, dx)
    y = np.arange(0, ny * dx, dx)

    X, Y = np.meshgrid(x, y, indexing="xy")

    def make_surface(values, z_scale):
        Z = np.zeros_like(X)

        mesh = pv.StructuredGrid(X, Y, Z)

        # Important: PyVista expects Fortran order here
        mesh["Elevation"] = values.ravel(order="F")

        topo = mesh.warp_by_scalar(
            scalars="Elevation",
            factor=z_scale
        )

        return topo

    topo1 = make_surface(array1, z_scale1)
    topo2 = make_surface(array2, z_scale2)

    if not interactive:
        _ensure_headless_display()
    p = pv.Plotter(off_screen=not interactive, window_size=list(window_size))

    # Axes and labels have to contrast with whatever background was asked for,
    # or they vanish (white on white was the old default).
    grid_color = "black" if sum(pv.Color(background).float_rgb) > 1.5 else "white"

    p.add_mesh(
        topo1,
        scalars=topo1["Elevation"],
        cmap=cmap1,
        clim=clim1,
        opacity=opacity1,
        show_edges=show_edges,
        name="array1",
        show_scalar_bar = False
    )

    p.add_mesh(
        topo2,
        scalars=topo2["Elevation"],
        cmap=cmap2,
        clim=clim2,
        opacity=opacity2,
        show_edges=show_edges,
        name="array2",
        show_scalar_bar=True,
        scalar_bar_args={"title": "Surface elevation (m)", "color": grid_color,
                         "position_x": 0.25, "position_y": 0.02, "width": 0.5,
                         "height": 0.06})
    

    p.show_grid(color=grid_color)
    p.set_background(background)
    p.camera_position = "iso"
    p.camera.zoom(1.1)

    # Export before calling show() to avoid plotter destruction
    if html_path is not None:
        p.export_html(str(html_path))
        print(f"✓ 3D visualization exported to {html_path}")

    if png_path is not None:
        p.screenshot(str(png_path))
        print(f"✓ 3D still saved to {png_path}")

    if interactive:
        p.show()
    p.close()

    return html_path
