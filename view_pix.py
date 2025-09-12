from PIL import Image
import sys, zlib, os, time, tempfile, subprocess

def fast_load_pix(filename):
    """Optimized pix loader for viewing - prioritizes speed over compatibility"""
    with open(filename, "rb") as f:
        header = f.read(7)
        if header[:2] != b"PX":
            raise ValueError("Not a pix file")

        width = int.from_bytes(header[2:4], "little")
        height = int.from_bytes(header[4:6], "little")
        flags = header[6]
        
        compression = flags & 0x07
        has_alpha = bool(flags & 0x08)
        pixel_count = width * height

        print(f"Loading {width}x{height} {'RGBA' if has_alpha else 'RGB'} image (compression={compression})")

        compressed_data = f.read()
        
        if compression == 0:  
            if has_alpha:
                pixels = [tuple(compressed_data[i:i+4]) for i in range(0, len(compressed_data), 4)]
            else:
                pixels = [tuple(compressed_data[i:i+3]) + (255,) for i in range(0, len(compressed_data), 3)]

        elif compression in [2, 3]:  
            raw_bytes = zlib.decompress(compressed_data)
            if has_alpha:
                pixels = [tuple(raw_bytes[i:i+4]) for i in range(0, len(raw_bytes), 4)]
            else:
                pixels = [tuple(raw_bytes[i:i+3]) + (255,) for i in range(0, len(raw_bytes), 3)]

        elif compression == 4:  
            delta_bytes = zlib.decompress(compressed_data)
            
            if has_alpha:
                pixels = []
                prev = [0, 0, 0, 0]
                for i in range(0, len(delta_bytes), 4):
                    prev[0] = (delta_bytes[i] + prev[0]) & 255
                    prev[1] = (delta_bytes[i+1] + prev[1]) & 255
                    prev[2] = (delta_bytes[i+2] + prev[2]) & 255
                    prev[3] = (delta_bytes[i+3] + prev[3]) & 255
                    pixels.append(tuple(prev))
            else:
                pixels = []
                prev = [0, 0, 0]
                for i in range(0, len(delta_bytes), 3):
                    prev[0] = (delta_bytes[i] + prev[0]) & 255
                    prev[1] = (delta_bytes[i+1] + prev[1]) & 255
                    prev[2] = (delta_bytes[i+2] + prev[2]) & 255
                    pixels.append(tuple(prev) + (255,))

        elif compression == 1: 
            decompressed = zlib.decompress(compressed_data)
            pixels = []
            i = 0
            channels = 4 if has_alpha else 3
            
            while i < len(decompressed) and len(pixels) < pixel_count:
                run_length = decompressed[i]
                pixel_data = tuple(decompressed[i+1:i+1+channels])
                if not has_alpha:
                    pixel_data += (255,)
                
                pixels.extend([pixel_data] * run_length)
                i += 1 + channels

        elif compression == 5: 
            decompressed = zlib.decompress(compressed_data)
            palette_size = decompressed[0]
            channels = 4 if has_alpha else 3
            
            palette = []
            for i in range(palette_size):
                start = 1 + i * channels
                pixel = tuple(decompressed[start:start+channels])
                if not has_alpha:
                    pixel += (255,)
                palette.append(pixel)
            
            indices_start = 1 + palette_size * channels
            pixels = [palette[decompressed[i]] for i in range(indices_start, min(len(decompressed), indices_start + pixel_count))]

        else:
            raise ValueError(f"Unsupported compression type: {compression}")

        pixels = pixels[:pixel_count]  
        while len(pixels) < pixel_count:  
            pixels.append((0, 0, 0, 255))

    return pixels, width, height

def view_pix(filename, show_info=False):
    """View pix file with optimized loading"""
    if not os.path.exists(filename):
        print(f"Error: File '{filename}' not found")
        return

    try:
        start_time = time.time()
        
        pixels, width, height = fast_load_pix(filename)
        load_time = time.time() - start_time
        
        img = Image.new("RGBA", (width, height))
        img.putdata(pixels)
        
        total_time = time.time() - start_time
        
        if show_info:
            file_size = os.path.getsize(filename)
            pixel_count = width * height
            print(f"File: {os.path.basename(filename)}")
            print(f"Size: {file_size:,} bytes")
            print(f"Dimensions: {width}x{height} ({pixel_count:,} pixels)")
            print(f"Load time: {load_time:.3f}s")
            print(f"Total time: {total_time:.3f}s")
            print(f"Speed: {pixel_count/total_time:,.0f} pixels/second")
            print("-" * 40)
        
        img.show()
        
    except Exception as e:
        print(f"Error loading {filename}: {e}")

def batch_view_pix(filenames):
    """View multiple pix files"""
    pix_files = []
    for filename in filenames:
        if filename.lower().endswith('.pix'):
            if os.path.exists(filename):
                pix_files.append(filename)
            else:
                print(f"Warning: {filename} not found")
        else:
            print(f"Warning: {filename} is not a pix file")
    
    if not pix_files:
        print("No valid pix files found")
        return
    
    print(f"Viewing {len(pix_files)} pix file(s)...")
    for filename in pix_files:
        view_pix(filename, show_info=True)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python view_pix.py image.pix              # View single image")
        print("  python view_pix.py *.pix                  # View multiple images")
        print("  python view_pix.py image.pix --info       # Show detailed info")
    else:
        filenames = []
        show_info = False
        
        for arg in sys.argv[1:]:
            if arg == "--info":
                show_info = True
            else:
                filenames.append(arg)
        
        if len(filenames) == 1:
            view_pix(filenames[0], show_info)
        else:
            batch_view_pix(filenames)