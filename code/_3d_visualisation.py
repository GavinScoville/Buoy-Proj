import pyvista as pv
import rioxarray as riox
import numpy as np
import pandas as pd

import numpy as np
import pyvista as pv


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
    clim2=[-3, 3]
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

    p = pv.Plotter()

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
        show_scalar_bar = True)
    

    p.show_grid(color="white")
    p.set_background(background)

    # Export HTML before calling show() to avoid plotter destruction
    p.export_html("surface_plot.html")
    print("✓ 3D visualization exported to surface_plot.html")

    # Optionally show interactive plot (comment out if headless)
    p.show()
    p.close()
