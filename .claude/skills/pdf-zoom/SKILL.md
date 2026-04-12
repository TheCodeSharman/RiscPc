---
name: pdf-zoom
description: Render a specific page and region of a PDF at high DPI so fine schematic detail can be read. Use when a PDF page is too small to read component values, pin connections, or other fine detail.
---

Render a PDF page at high resolution and crop to a specific region so it can be read clearly.

## Prerequisites

```bash
sudo apt install poppler-utils imagemagick   # Debian/Ubuntu
sudo pacman -S poppler imagemagick           # Arch
brew install poppler imagemagick             # macOS
```

## Steps

1. Render the target page at 300 DPI using `pdftoppm`:
```bash
pdftoppm -r 300 -f <page> -l <page> "path/to/file.pdf" /tmp/pdfzoom
```

2. Convert the PPM to PNG (PPM is uncompressed and too large to read directly):
```bash
convert /tmp/pdfzoom-<page>.ppm /tmp/pdfzoom.png
```

3. Check the image dimensions to work out crop coordinates:
```bash
identify /tmp/pdfzoom.png
```

4. Crop to the region of interest:
```bash
convert /tmp/pdfzoom.png -crop WxH+X+Y /tmp/pdfzoom_crop.png
```

5. Read the cropped image with the Read tool.

## Notes

- Never try to Read the PPM or full PNG directly — both will likely exceed the 256KB size limit
- Always crop to the region of interest before reading
- 300 DPI is sufficient for most schematics; use 600 for very dense layouts
- Crop format is `WxH+X+Y` where X,Y is the top-left corner offset
- For an A1 schematic at 300 DPI the full image is roughly 9934x7016 pixels
- Bottom-left region: try `-crop 2500x1800+0+5200` as a starting point
