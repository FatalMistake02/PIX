# editor_pix.py

import sys, os, subprocess, tempfile, time, zlib
from from_pix import load_pix
from to_pix import save_pix
from PIL import Image

def png_filter_encode_fast(pixel_bytes, width, height, channels):
    filtered_data = bytearray()
    bytes_per_row = width * channels
    for row in range(height):
        row_start = row * bytes_per_row
        row_data = pixel_bytes[row_start:row_start + bytes_per_row]
        
        if row == 0:
            filtered_row = bytearray([0]) + row_data
        else:
            prev_row_start = (row - 1) * bytes_per_row
            prev_row = pixel_bytes[prev_row_start:prev_row_start + bytes_per_row]
            up_filtered = bytearray([2])
            for i in range(len(row_data)):
                pred = prev_row[i]
                up_filtered.append((row_data[i] - pred) % 256)
            filtered_row = up_filtered
        
        filtered_data.extend(filtered_row)
    
    return zlib.compress(filtered_data, level=6)

def png_filter_decode_fast(compressed_data, width, height, channels):
    filtered_data = zlib.decompress(compressed_data)
    pixel_bytes = bytearray()
    bytes_per_row = width * channels
    pos = 0
    
    for row in range(height):
        filter_type = filtered_data[pos]
        pos += 1
        row_data = filtered_data[pos:pos+bytes_per_row]
        pos += bytes_per_row
        
        if filter_type == 0:  
            reconstructed = row_data
        elif filter_type == 2 and row > 0: 
            prev_row_start = (row-1)*bytes_per_row
            prev_row = pixel_bytes[prev_row_start:prev_row_start+bytes_per_row]
            reconstructed = bytearray()
            for i in range(len(row_data)):
                up = prev_row[i]
                reconstructed.append((row_data[i]+up)%256)
        else:
            reconstructed = row_data
        
        pixel_bytes.extend(reconstructed)
    
    return pixel_bytes

def fast_load_pix(filename):
    with open(filename, "rb") as f:
        if f.read(2) != b"PX":
            raise ValueError("Not a valid .pix file")
        width = int.from_bytes(f.read(2), "little")
        height = int.from_bytes(f.read(2), "little")
        flags = f.read(1)[0]
        compression = flags & 0x0F
        has_alpha = bool(flags & 0x10)
        channels = 4 if has_alpha else 3
        compressed_data = f.read()
    
    pixels = []
    
    if compression == 0: 
        raw_bytes = compressed_data
    elif compression == 2: 
        raw_bytes = zlib.decompress(compressed_data)
    elif compression == 6: 
        raw_bytes = png_filter_decode_fast(compressed_data, width, height, channels)
    else:
        raise ValueError(f"Unsupported fast compression type: {compression}")

    for i in range(0, len(raw_bytes), channels):
        pixel_tuple = tuple(raw_bytes[i:i+channels])
        if not has_alpha:
            pixel_tuple += (255,)
        pixels.append(pixel_tuple)

    img = Image.new("RGBA", (width, height))
    img.putdata(pixels)
    return img

def fast_save_pix(png_file, pix_file):
    img = Image.open(png_file).convert("RGBA")
    width, height = img.size
    pixels = list(img.getdata())
    use_alpha = any(a!=255 for r,g,b,a in pixels)
    channels = 4 if use_alpha else 3
    
    data = bytearray()
    for r,g,b,a in pixels:
        data.extend([r,g,b] + ([a] if use_alpha else []))
    
    methods = [
        (len(data), 0, data),
        (len(zlib.compress(data, level=6)), 2, zlib.compress(data, level=6)),
        (len(png_filter_encode_fast(data, width, height, channels)), 6, png_filter_encode_fast(data, width, height, channels))
    ]
    
    chosen_size, t, chosen_data = min(methods, key=lambda x: x[0])
    
    with open(pix_file, "wb") as f:
        f.write(b"PX")
        f.write(width.to_bytes(2, "little"))
        f.write(height.to_bytes(2, "little"))
        flags = t | (0x08 if use_alpha else 0x00)
        f.write(bytes([flags]))
        f.write(chosen_data)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python pix_editor.py my_image.pix [--fast]")
        sys.exit(1)

    pix_file = sys.argv[1]
    fast_mode = "--fast" in sys.argv
    print(f"Loading {pix_file}..." + (" (fast mode)" if fast_mode else ""))

    start_time = time.time()
    img = None

    if fast_mode:
        try:
            img = fast_load_pix(pix_file)
            if img:
                print(f"Fast load successful in {time.time()-start_time:.2f}s")
        except ValueError as e:
            print(f"Fast load failed: {e}. Falling back to full load...")
        except FileNotFoundError:
            print(f"Error: {pix_file} not found.")
            sys.exit(1)

    if img is None:
        try:
            img = load_pix(pix_file)
            print(f"Full load completed in {time.time()-start_time:.2f}s")
        except (ValueError, FileNotFoundError) as e:
            print(f"Error: Could not load file. {e}")
            sys.exit(1)

    tmp_dir = tempfile.gettempdir()
    base_name = os.path.splitext(os.path.basename(pix_file))[0]
    tmp_png = os.path.join(tmp_dir, f"{base_name}_edit.png")

    try:
        img.save(tmp_png, "PNG", compress_level=1)
        print(f"Temporary PNG created: {tmp_png}")
        print("Opening image editor...")
        
        if sys.platform.startswith("win"):
            editor_process = subprocess.Popen(["mspaint", tmp_png])
            editor_process.wait()
        elif sys.platform.startswith("darwin"):
            subprocess.run(["open", "-W", tmp_png], check=True)
        else:
            subprocess.run(["xdg-open", tmp_png], check=True)
        print("Editor closed, continuing...")
    except FileNotFoundError:
        input(f"No default editor found. Please edit {tmp_png} manually, then press Enter to continue...")
    except subprocess.CalledProcessError:
        input(f"Editor process failed. Please edit {tmp_png} manually, then press Enter to continue...")
    except Exception as e:
        input(f"An error occurred: {e}. Please edit {tmp_png} manually, then press Enter to continue...")

    if not os.path.exists(tmp_png):
        print(f"Error: {tmp_png} not found. Make sure you saved your edits.")
        sys.exit(1)

    print("Converting back to pix...")
    save_start = time.time()

    if fast_mode:
        try:
            fast_save_pix(tmp_png, pix_file)
            print(f"Fast save completed in {time.time()-save_start:.2f}s")
        except Exception as e:
            print(f"Fast save failed: {e}. Using full compression...")
            save_pix(tmp_png, pix_file)
    else:
        save_pix(tmp_png, pix_file)

    try:
        os.remove(tmp_png)
        print("Temporary PNG cleaned up")
    except Exception as e:
        print(f"Warning: Could not remove temporary file. {e}")

    try:
        print(f"Successfully saved edits back to {pix_file}")
        print(f"Final pix size: {os.path.getsize(pix_file):,} bytes")
    except Exception:
        pass