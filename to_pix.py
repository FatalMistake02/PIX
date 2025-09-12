from PIL import Image
import sys, zlib

def has_meaningful_alpha(pixels):
    """Check if image has meaningful alpha data (not all 255)"""
    for r, g, b, a in pixels:
        if a != 255:
            return True
    return False

def run_length_encode(data, channels):
    """RLE encoding optimized for pixel data"""
    if not data:
        return bytearray()
    
    result = bytearray()
    i = 0
    while i < len(data):
        current_pixel = data[i:i+channels]
        run_length = 1
        
        while (i + run_length * channels < len(data) and 
               run_length < 255 and
               data[i + run_length * channels:i + (run_length + 1) * channels] == current_pixel):
            run_length += 1
        
        result.append(run_length)
        result.extend(current_pixel)
        i += run_length * channels
    
    return result

def predictive_encode(pixels, channels):
    """Predictive encoding using multiple prediction methods"""
    if not pixels:
        return bytearray()
    
    methods = []
    
    delta_bytes = bytearray()
    prev = tuple([0] * channels)
    for i in range(0, len(pixels), channels):
        current = pixels[i:i+channels]
        deltas = [(current[j] - prev[j]) % 256 for j in range(channels)]
        delta_bytes.extend(deltas)
        prev = current
    methods.append(('simple_delta', delta_bytes))
    
    avg_bytes = bytearray()
    for i in range(0, len(pixels), channels):
        current = pixels[i:i+channels]
        if i == 0:
            avg_bytes.extend(current)
        else:
            prev = pixels[i-channels:i]
            predicted = [(current[j] - prev[j]) % 256 for j in range(channels)]
            avg_bytes.extend(predicted)
    methods.append(('avg_prediction', avg_bytes))
    
    paeth_bytes = bytearray()
    width_in_pixels = int((len(pixels) / channels) ** 0.5)  
    
    for i in range(0, len(pixels), channels):
        current = pixels[i:i+channels]
        pixel_index = i // channels
        row = pixel_index // width_in_pixels
        col = pixel_index % width_in_pixels
        
        if row == 0 and col == 0:
            paeth_bytes.extend(current)
        elif row == 0:
            left = pixels[i-channels:i]
            predicted = [(current[j] - left[j]) % 256 for j in range(channels)]
            paeth_bytes.extend(predicted)
        elif col == 0:
            above_index = (pixel_index - width_in_pixels) * channels
            if above_index >= 0:
                above = pixels[above_index:above_index+channels]
                predicted = [(current[j] - above[j]) % 256 for j in range(channels)]
                paeth_bytes.extend(predicted)
            else:
                paeth_bytes.extend(current)
        else:
            left = pixels[i-channels:i]
            above_index = (pixel_index - width_in_pixels) * channels
            if above_index >= 0:
                above = pixels[above_index:above_index+channels]
                predicted = [(current[j] - ((left[j] + above[j]) // 2)) % 256 for j in range(channels)]
                paeth_bytes.extend(predicted)
            else:
                predicted = [(current[j] - left[j]) % 256 for j in range(channels)]
                paeth_bytes.extend(predicted)
    
    methods.append(('paeth_prediction', paeth_bytes))
    
    best_method = None
    best_size = float('inf')
    best_data = None
    
    for method_name, data in methods:
        compressed = zlib.compress(data, level=9)
        if len(compressed) < best_size:
            best_size = len(compressed)
            best_data = compressed
            best_method = method_name
    
    return best_data, best_method

def save_pix(input_file, output_file):
    img = Image.open(input_file).convert("RGBA")
    width, height = img.size
    pixels = list(img.getdata())
    
    use_alpha = has_meaningful_alpha(pixels)
    channels = 4 if use_alpha else 3
    
    print(f"Processing {width}x{height} image using {'RGBA' if use_alpha else 'RGB'} format")

    pixel_bytes = bytearray()
    for r, g, b, a in pixels:
        pixel_bytes.extend([r, g, b] + ([a] if use_alpha else []))

    compression_methods = []
    
    raw_size = len(pixel_bytes)
    compression_methods.append((raw_size, 0, pixel_bytes, "raw"))
    
    rle_data = run_length_encode(pixel_bytes, channels)
    rle_compressed = zlib.compress(rle_data, level=9)  
    compression_methods.append((len(rle_compressed), 1, rle_compressed, "RLE+zlib"))
    
    zlib_data = zlib.compress(pixel_bytes, level=9)
    compression_methods.append((len(zlib_data), 2, zlib_data, "zlib"))
    
    for strategy, strategy_name in [(zlib.Z_DEFAULT_STRATEGY, "default"), 
                                   (zlib.Z_FILTERED, "filtered"),
                                   (zlib.Z_HUFFMAN_ONLY, "huffman")]:
        try:
            compressor = zlib.compressobj(level=9, strategy=strategy)
            compressed = compressor.compress(pixel_bytes) + compressor.flush()
            compression_methods.append((len(compressed), 3, compressed, f"zlib_{strategy_name}"))
        except:
            pass  
    
    try:
        pred_data, pred_method = predictive_encode(pixel_bytes, channels)
        compression_methods.append((len(pred_data), 4, pred_data, f"predictive_{pred_method}"))
    except:
        pass  
    
    unique_colors = len(set(pixels))
    if unique_colors <= 256:  
        palette = list(set(pixels))
        palette_bytes = bytearray()
        for color in palette:
            palette_bytes.extend([color[0], color[1], color[2]] + ([color[3]] if use_alpha else []))
        
        color_to_index = {color: i for i, color in enumerate(palette)}
        indices = bytearray([color_to_index[pixel] for pixel in pixels])
        
        palette_data = bytearray([len(palette)]) + palette_bytes + indices
        palette_compressed = zlib.compress(palette_data, level=9)
        compression_methods.append((len(palette_compressed), 5, palette_compressed, f"palette_{unique_colors}_colors"))

    compression_methods.sort(key=lambda x: x[0])
    chosen_size, compression_type, chosen_data, method_name = compression_methods[0]

    with open(output_file, "wb") as f:
        f.write(b"PX")                             
        f.write(width.to_bytes(2, "little"))      
        f.write(height.to_bytes(2, "little"))      
        flags = compression_type | (0x08 if use_alpha else 0x00)  
        f.write(bytes([flags]))                       
        f.write(chosen_data)                 

    original_size = width * height * (4 if use_alpha else 3)
    compression_ratio = (original_size - chosen_size) / original_size * 100
    
    print(f"Saved as: {output_file}")
    print(f"Method: {method_name} (type={compression_type})")
    print(f"Size: {chosen_size:,} bytes")
    print(f"Alpha channel: {'used' if use_alpha else 'not needed'}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python to_pix.py input.png output.pix")
    else:
        save_pix(sys.argv[1], sys.argv[2])