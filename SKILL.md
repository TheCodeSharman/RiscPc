# Skills & Techniques

## Reading high-resolution sections of PDF schematics

PDF pages rendered by the built-in tool are fixed resolution and can be too small to read fine detail (e.g. A1 schematics shrunk to a PDF page).

**Technique:** Render the PDF at high DPI with `pdftoppm`, convert to PNG, crop to the area of interest, then read the cropped image.

```bash
# Render page 1 at 300 DPI
pdftoppm -r 300 -f 1 -l 1 "path/to/file.pdf" /tmp/output

# Convert PPM to PNG (PPM is too large to read directly)
convert /tmp/output-1.ppm /tmp/output.png

# Check dimensions to work out crop coordinates
identify /tmp/output.png

# Crop to area of interest (adjust offsets/size to taste)
# convert input -crop WxH+X+Y output
convert /tmp/output.png -crop 2500x1800+0+5200 /tmp/output_crop.png
```

Then read `/tmp/output_crop.png` with the Read tool.

**Notes:**
- 300 DPI is usually enough; use 600 for very dense schematics
- PPM files are uncompressed and will be too large to read directly — always convert to PNG first
- The full PNG may also be too large (>256KB limit) — always crop to the region of interest
- Crop coordinates: `WxH+X+Y` where X,Y is the top-left corner of the crop region
- For bottom-left of an A1 schematic at 300 DPI, Y offset ~5200 worked well
