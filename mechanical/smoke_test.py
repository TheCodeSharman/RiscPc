"""End-to-end check that the CAD toolchain is live.

Run it headless to prove build123d and its OpenCascade binding load:

    ./.venv/bin/python smoke_test.py

Or open it in VS Code, press the OCP CAD Viewer's play button in the status
bar to start the viewer, then run the file -- the wedge should appear in the
viewer pane. If it renders, `show()` works for the real models too.
"""

from build123d import *

with BuildPart() as wedge:
    Box(40, 20, 10)
    with Locations((0, 0, 5)):
        Cylinder(6, 10, mode=Mode.SUBTRACT)
    fillet(wedge.edges().filter_by(Axis.Z), radius=3)

if __name__ == "__main__":
    print(f"volume {wedge.part.volume:.1f} mm^3")
    try:
        from ocp_vscode import show

        show(wedge)
    except Exception as exc:  # viewer not running -- headless check still passed
        print(f"viewer not connected ({exc.__class__.__name__}); geometry is fine")
