# 16-bit PNG Film Grain Synthesizer for Termux

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python](https://img.shields.io/badge/Python-3.x-blue.svg)
![Platform](https://img.shields.io/badge/Platform-Termux-green.svg)

A lightweight Python script designed to apply film grain to **16-bit PNG images** on memory-constrained Android environments (via Termux) without losing bit depth or breaking ICC color profiles (e.g., ProPhoto RGB).

---

## Key Features

- **Full 16-bit & Color Profile Preservation**: Bypasses Pillow's 16-bit RGB encoding limitations using `pypng` and manually injects the original `iCCP` chunk back into the output PNG.
- **Low Memory Footprint (OOM Prevention)**: Uses chunk-based processing and `float32` arrays to run reliably on Termux and low-RAM devices without triggering Out-Of-Memory (OOM) kills.
- **Physically Inspired Film Grain Model**:
  - **Luminance Masking**: Applies grain primarily to midtones, reflecting real photographic silver-halide film behavior.
  - **Grain Clustering**: Uses Gaussian filtering to simulate realistic film grain clusters rather than raw digital noise.
  - **Color Grain Control**: Allows tuning between monochromatic film emulsion noise and color noise.

---

## Installation

Run the following commands in your Termux terminal:

> [!TIP]
> Installing `numpy` and `pillow` via `pkg` uses pre-compiled binary packages, preventing C-compiler build errors on Android.

```bash
# Install pre-built packages (recommended for Termux)
pkg install python python-numpy python-pillow

# Install pure Python dependencies
pip install scipy pypng imageio
```

## Usage

```bash
python spektra_grain_light.py <input.png> <output.png> [amount] [size] [color_grain]
```

### Command Examples

```bash
# Standard Grain
python spektra_grain_light.py input.png output_grain.png 0.03 1.2 0.1

# Natural / Moderate Grain
python spektra_grain_light.py input.png output_natural.png 0.015 0.6 0.1

# Ultra-Fine / Subtle Grain (Fine-grain film look)
python spektra_grain_light.py input.png output_fine.png 0.008 0.5 0.0
```

## Parameters

| Parameter | Default | Description |
|---|---|---|
| `amount` | `0.015` | Grain Intensity. Controls noise contrast. Lower values (0.008 - 0.015) result in a subtle, natural film look. |
| `size` | `0.6` | Grain Size. Gaussian blur sigma ($\sigma$). Controls grain cluster size (0.4 - 0.6 recommended for fine grain). |
| `color_grain` | `0.1` | Color Noise Ratio. Set to 0.0 for pure monochromatic emulsion grain. |

## Technical Details

- **Chunk Processing with Border Padding**:
  Images are sliced into horizontal strips during processing. To avoid edge artifacts from Gaussian filtering at chunk boundaries, a dynamic overlap padding ($\text{pad} = 4 \times \text{grain\_size}$) is applied and trimmed after filtering.
- **Luminance-Based Grain Masking**:
  Midtone response is calculated via a parabolic luminance curve:
  $$M = 4.0 \times L \times (1.0 - L)$$
  where $L$ represents normalized pixel luminosity ($0.0 \le L \le 1.0$).

## License

This project is licensed under the MIT License.
```
