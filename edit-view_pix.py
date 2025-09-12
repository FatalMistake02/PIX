import sys, os, subprocess, tempfile, time
from from_pix import load_pix
from to_pix import save_pix

def fast_load_pix(filename):
    with open(filename, "rb") as f:
        magic = f.read(2)
        if magic != b"PX":
            raise ValueError("Not a pix file")

        width = int.from_bytes(f.read(2), "little")
        height = int.from_bytes(f.read(2), "little")
        flags = f.read(1)[0]
        
        compression = flags & 0x07
        has_alpha = bool(flags & 0x08)
        channels = 4 if has_alpha else 3

        compressed_data = f.read()
        pixels = []

        if compression == 0:
            for i in range(0, len(compressed_data), channels):
                if has_alpha:
                    pixels.append(tuple(compressed_data[i:i+4]))
                else:
                    pixels.append(tuple(compressed_data[i:i+3]) + (255,))

        elif compression in [2, 3]:
            import zlib
            raw_bytes = zlib.decompress(compressed_data)
            for i in range(0, len(raw_bytes), channels):
                if has_alpha:
                    pixels.append(tuple(raw_bytes[i:i+4]))
                else:
                    pixels.append(tuple(raw_bytes[i:i+3]) + (255,))
        else:
            return None

        from PIL import Image
        img = Image.new("RGBA", (width, height))
        img.putdata(pixels)
        return img

def fast_save_pix(png_file, pix_file):
    from PIL import Image
    import zlib
    
    img = Image.open(png_file).convert("RGBA")
    width, height = img.size
    pixels = list(img.getdata())
    
    use_alpha = any(a != 255 for r, g, b, a in pixels)
    channels = 4 if use_alpha else 3
    
    pixel_bytes = bytearray()
    for r, g, b, a in pixels:
        pixel_bytes.extend([r, g, b] + ([a] if use_alpha else []))
    
    methods = [
        (len(pixel_bytes), 0, pixel_bytes),
        (len(zlib.compress(pixel_bytes, level=6)), 2, zlib.compress(pixel_bytes, level=6))
    ]
    
    chosen_size, compression_type, chosen_data = min(methods, key=lambda x: x[0])
    
    with open(pix_file, "wb") as f:
        f.write(b"PX")
        f.write(width.to_bytes(2, "little"))
        f.write(height.to_bytes(2, "little"))
        flags = compression_type | (0x08 if use_alpha else 0x00)
        f.write(bytes([flags]))
        f.write(chosen_data)

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
            print(f"Fast load successful in {time.time() - start_time:.2f}s")
    except:
        pass

if img is None:
    img = load_pix(pix_file)
    print(f"Full load completed in {time.time() - start_time:.2f}s")

tmp_dir = tempfile.gettempdir()
base_name = os.path.splitext(os.path.basename(pix_file))[0]
tmp_png = os.path.join(tmp_dir, f"{base_name}_edit.png")

img.save(tmp_png, "PNG", compress_level=1) 
print(f"Temporary PNG created: {tmp_png}")

print("Opening image editor...")
try:
    if sys.platform.startswith("win"):
        os.startfile(tmp_png)
    elif sys.platform.startswith("darwin"):
        subprocess.run(["open", tmp_png], check=True)
    else:
        subprocess.run(["xdg-open", tmp_png], check=True)
    
    print("Image editor opened successfully")
except (subprocess.CalledProcessError, OSError, AttributeError) as e:
    print(f"Could not open editor automatically: {e}")
    print(f"Please manually open and edit: {tmp_png}")

input("\nPress Enter after you finish editing and save the PNG...")

if not os.path.exists(tmp_png):
    print(f"Error: {tmp_png} not found. Make sure you saved your edits.")
    sys.exit(1)


print("Converting back to pix...")
save_start = time.time()

if fast_mode:
    try:
        fast_save_pix(tmp_png, pix_file)
        print(f"Fast save completed in {time.time() - save_start:.2f}s")
    except:
        print("Fast save failed, using full compression...")
        save_pix(tmp_png, pix_file)
else:
    save_pix(tmp_png, pix_file)


try:
    os.remove(tmp_png)
    print(f"Cleaned up temporary file")
except OSError:
    print(f"Warning: Could not delete {tmp_png}")

print(f"Successfully saved edits back to {pix_file}")


try:
    file_size = os.path.getsize(pix_file)
    print(f"Final pix size: {file_size:,} bytes")
except:
    pass