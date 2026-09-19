import sys
import zlib
import struct
import numpy as np
import png
from PIL import Image
from scipy.ndimage import gaussian_filter

def embed_icc_profile(png_path, icc_profile, profile_name=b"ProPhoto RGB"):
    if not icc_profile:
        return
    with open(png_path, "rb") as f:
        png_bytes = f.read()
    if not png_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return

    compressed_icc = zlib.compress(icc_profile)
    chunk_data = profile_name + b"\x00\x00" + compressed_icc
    chunk_type = b"iCCP"
    crc = zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF
    iccp_chunk = struct.pack(">I", len(chunk_data)) + chunk_type + chunk_data + struct.pack(">I", crc)
    
    ihdr_end = 33
    new_png_bytes = png_bytes[:ihdr_end] + iccp_chunk + png_bytes[ihdr_end:]
    with open(png_path, "wb") as f:
        f.write(new_png_bytes)

def load_16bit_png(input_path):
    reader = png.Reader(filename=input_path)
    w, h, pixels, meta = reader.asDirect()
    bitdepth = meta['bitdepth']
    planes = meta['planes']
    rows = [np.array(row, dtype=np.uint16) for row in pixels]
    arr = np.vstack(rows)
    if bitdepth == 8:
        arr = arr.astype(np.uint16) * 257
    return arr.reshape((h, w, planes))

def save_16bit_png(output_path, array_uint16):
    h, w, c = array_uint16.shape
    flat_rows = array_uint16.reshape(h, w * c)
    has_alpha = (c == 4)
    is_grey = (c == 1)
    with open(output_path, "wb") as f:
        writer = png.Writer(width=w, height=h, bitdepth=16, greyscale=is_grey, alpha=has_alpha)
        writer.write(f, flat_rows)

def apply_spektra_grain(input_path, output_path, grain_amount=0.015, grain_size=0.6, color_grain=0.1, chunk_height=400):
    print(f"Settings -> Amount: {grain_amount}, Size: {grain_size}, Color noise: {color_grain}")
    
    with Image.open(input_path) as img_meta:
        icc_profile = img_meta.info.get('icc_profile')
    
    arr_uint16 = load_16bit_png(input_path)
    h, w, c = arr_uint16.shape
    
    output_uint16 = np.empty_like(arr_uint16)
    pad = int(np.ceil(grain_size * 4.0)) if grain_size > 0 else 0
    scaling_factor = np.float32(1.0 + (grain_size * 0.5))
    
    for y_start in range(0, h, chunk_height):
        y_end = min(y_start + chunk_height, h)
        y_pad_start = max(0, y_start - pad)
        y_pad_end = min(h, y_end + pad)
        
        chunk_arr = arr_uint16[y_pad_start:y_pad_end].astype(np.float32) / 65535.0
        c_h, c_w, _ = chunk_arr.shape
        
        r, g, b = chunk_arr[:, :, 0], chunk_arr[:, :, 1], chunk_arr[:, :, 2]
        lum = 0.2222 * r + 0.7066 * g + 0.0713 * b
        
        midtone_mask = 4.0 * lum * (1.0 - lum)
        np.clip(midtone_mask, 0.0, 1.0, out=midtone_mask)
        
        mono_noise = np.random.normal(0, grain_amount, (c_h, c_w)).astype(np.float32)
        if grain_size > 0:
            mono_noise = gaussian_filter(mono_noise, sigma=grain_size)
            
        color_channels = min(c, 3)
        color_noise = np.random.normal(0, grain_amount * color_grain, (c_h, c_w, color_channels)).astype(np.float32)
        if grain_size > 0:
            for i in range(color_channels):
                color_noise[:, :, i] = gaussian_filter(color_noise[:, :, i], sigma=grain_size)
                
        if c > 3:
            full_color_noise = np.zeros((c_h, c_w, c), dtype=np.float32)
            full_color_noise[:, :, :3] = color_noise
            color_noise = full_color_noise

        total_noise = mono_noise[:, :, None] + color_noise
        total_noise *= midtone_mask[:, :, None]
        total_noise *= scaling_factor
        
        chunk_arr += total_noise
        np.clip(chunk_arr, 0.0, 1.0, out=chunk_arr)
        
        valid_y_start = y_start - y_pad_start
        valid_y_end = valid_y_start + (y_end - y_start)
        
        chunk_valid = chunk_arr[valid_y_start:valid_y_end]
        output_uint16[y_start:y_end] = (chunk_valid * 65535.0).round().astype(np.uint16)
        
        print(f"Progress: {min(y_end, h)} / {h} rows completed", end="\r")

    print("\nSaving...")
    save_16bit_png(output_path, output_uint16)
    
    if icc_profile:
        embed_icc_profile(output_path, icc_profile)
        
    print(f"Saved successfully: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python spektra_grain_light.py input.png output.png [amount] [size] [color_grain]")
    else:
        amount = float(sys.argv[3]) if len(sys.argv) > 3 else 0.015
        size = float(sys.argv[4]) if len(sys.argv) > 4 else 0.6
        color = float(sys.argv[5]) if len(sys.argv) > 5 else 0.1
        apply_spektra_grain(sys.argv[1], sys.argv[2], grain_amount=amount, grain_size=size, color_grain=color)
