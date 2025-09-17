# Convert from PIX to PNG

from PIL import Image
import sys, zlib

def run_length_decode(data, channels, pixel_count):
    """Decode RLE data back to pixels"""
    result = bytearray()
    i = 0
    pixels_decoded = 0
    
    while i < len(data) and pixels_decoded < pixel_count:
        run_length = data[i]
        i += 1
        pixel_data = data[i:i+channels]
        i += channels
        
        for _ in range(run_length):
            result.extend(pixel_data)
            pixels_decoded += 1
            if pixels_decoded >= pixel_count:
                break
    
    return result

def predictive_decode(data, channels, width, height, method_hint="simple_delta"):
    pixel_count = width * height
    result = bytearray()
    
    if method_hint == "simple_delta":
        prev = tuple([0] * channels)
        for i in range(0, len(data), channels):
            deltas = data[i:i+channels]
            current = tuple((deltas[j] + prev[j]) % 256 for j in range(channels))
            result.extend(current)
            prev = current
    
    elif method_hint == "avg_prediction":
        for i in range(0, len(data), channels):
            current_data = data[i:i+channels]
            if i == 0:
                result.extend(current_data)
            else:
                prev = result[i-channels:i]
                decoded = [(current_data[j] + prev[j]) % 256 for j in range(channels)]
                result.extend(decoded)
    
    elif method_hint.startswith("paeth"):
        for i in range(0, len(data), channels):
            current_data = data[i:i+channels]
            pixel_index = i // channels
            row = pixel_index // width
            col = pixel_index % width
            
            if row == 0 and col == 0:
                result.extend(current_data)
            elif row == 0:
                left_start = (pixel_index - 1) * channels
                left = result[left_start:left_start+channels]
                decoded = [(current_data[j] + left[j]) % 256 for j in range(channels)]
                result.extend(decoded)
            elif col == 0:
                above_start = (pixel_index - width) * channels
                above = result[above_start:above_start+channels]
                decoded = [(current_data[j] + above[j]) % 256 for j in range(channels)]
                result.extend(decoded)
            else:
                left_start = (pixel_index - 1) * channels
                above_start = (pixel_index - width) * channels
                left = result[left_start:left_start+channels]
                above = result[above_start:above_start+channels]
                decoded = [(current_data[j] + ((left[j] + above[j]) // 2)) % 256 for j in range(channels)]
                result.extend(decoded)
    
    else:
        return predictive_decode(data, channels, width, height, "simple_delta")
    
    return result

def png_filter_decode(compressed_data, width, height, channels):
    filtered_data = zlib.decompress(compressed_data)
    
    pixel_bytes = bytearray()
    bytes_per_row = width * channels
    filtered_pos = 0
    
    for row in range(height):
        if filtered_pos >= len(filtered_data):
            break
            
        filter_type = filtered_data[filtered_pos]
        filtered_pos += 1
        
        row_data = filtered_data[filtered_pos:filtered_pos + bytes_per_row]
        filtered_pos += bytes_per_row
        
        if len(row_data) < bytes_per_row:
            row_data = row_data + bytearray([0] * (bytes_per_row - len(row_data)))
        
        reconstructed_row = bytearray()
        
        if filter_type == 0:  
            reconstructed_row = row_data
            
        elif filter_type == 1:  
            for i in range(len(row_data)):
                if i < channels:
                    reconstructed_row.append(row_data[i])
                else:
                    left = reconstructed_row[i - channels]
                    reconstructed_row.append((row_data[i] + left) % 256)
                    
        elif filter_type == 2:  
            if row > 0:
                prev_row_start = (row - 1) * bytes_per_row
                prev_row = pixel_bytes[prev_row_start:prev_row_start + bytes_per_row]
                for i in range(len(row_data)):
                    up = prev_row[i] if i < len(prev_row) else 0
                    reconstructed_row.append((row_data[i] + up) % 256)
            else:
                reconstructed_row = row_data
                
        elif filter_type == 3: 
            prev_row = bytearray()
            if row > 0:
                prev_row_start = (row - 1) * bytes_per_row
                prev_row = pixel_bytes[prev_row_start:prev_row_start + bytes_per_row]
                
            for i in range(len(row_data)):
                left = reconstructed_row[i - channels] if i >= channels else 0
                up = prev_row[i] if i < len(prev_row) else 0
                avg = (left + up) // 2
                reconstructed_row.append((row_data[i] + avg) % 256)
                
        elif filter_type == 4:  
            prev_row = bytearray()
            if row > 0:
                prev_row_start = (row - 1) * bytes_per_row
                prev_row = pixel_bytes[prev_row_start:prev_row_start + bytes_per_row]
                
            for i in range(len(row_data)):
                left = reconstructed_row[i - channels] if i >= channels else 0
                up = prev_row[i] if i < len(prev_row) else 0
                up_left = prev_row[i - channels] if i >= channels and i < len(prev_row) else 0
                
                p = left + up - up_left
                pa = abs(p - left)
                pb = abs(p - up)
                pc = abs(p - up_left)
                
                if pa <= pb and pa <= pc:
                    pred = left
                elif pb <= pc:
                    pred = up
                else:
                    pred = up_left
                    
                reconstructed_row.append((row_data[i] + pred) % 256)
        else:
            reconstructed_row = row_data
        
        pixel_bytes.extend(reconstructed_row)
    
    return pixel_bytes

def load_pix(filename):
    with open(filename, "rb") as f:
        magic = f.read(2)
        if magic != b"PX":
            raise ValueError("Not a pix file")

        width = int.from_bytes(f.read(2), "little")
        height = int.from_bytes(f.read(2), "little")
        flags = f.read(1)[0]
        
        compression = flags & 0x0F  
        has_alpha = bool(flags & 0x10)  
        channels = 4 if has_alpha else 3
        pixel_count = width * height

        print(f"Loading: {width}x{height}, {'RGBA' if has_alpha else 'RGB'}, compression={compression}")

        compressed_data = f.read()
        pixels = []

        if compression == 0: 
            for i in range(0, len(compressed_data), channels):
                if has_alpha:
                    r, g, b, a = compressed_data[i:i+4]
                    pixels.append((r, g, b, a))
                else:
                    r, g, b = compressed_data[i:i+3]
                    pixels.append((r, g, b, 255))

        elif compression == 1:  
            decompressed = zlib.decompress(compressed_data)
            raw_bytes = run_length_decode(decompressed, channels, pixel_count)
            
            for i in range(0, len(raw_bytes), channels):
                if has_alpha:
                    r, g, b, a = raw_bytes[i:i+4]
                    pixels.append((r, g, b, a))
                else:
                    r, g, b = raw_bytes[i:i+3]
                    pixels.append((r, g, b, 255))

        elif compression in [2, 3]:  
            raw_bytes = zlib.decompress(compressed_data)
            for i in range(0, len(raw_bytes), channels):
                if has_alpha:
                    r, g, b, a = raw_bytes[i:i+4]
                    pixels.append((r, g, b, a))
                else:
                    r, g, b = raw_bytes[i:i+3]
                    pixels.append((r, g, b, 255))

        elif compression == 4:  
            decompressed = zlib.decompress(compressed_data)
            raw_bytes = predictive_decode(decompressed, channels, width, height, "simple_delta")
            
            for i in range(0, len(raw_bytes), channels):
                if has_alpha:
                    r, g, b, a = raw_bytes[i:i+4]
                    pixels.append((r, g, b, a))
                else:
                    r, g, b = raw_bytes[i:i+3]
                    pixels.append((r, g, b, 255))

        elif compression == 5:  
            decompressed = zlib.decompress(compressed_data)
            palette_size = decompressed[0]
            palette_bytes_size = palette_size * channels
            
            palette = []
            for i in range(palette_size):
                start = 1 + i * channels
                if has_alpha:
                    r, g, b, a = decompressed[start:start+4]
                    palette.append((r, g, b, a))
                else:
                    r, g, b = decompressed[start:start+3]
                    palette.append((r, g, b, 255))
            
            indices_start = 1 + palette_bytes_size
            for i in range(indices_start, len(decompressed)):
                if i - indices_start < pixel_count:
                    palette_index = decompressed[i]
                    if palette_index < len(palette):
                        pixels.append(palette[palette_index])

        elif compression == 6:  
            raw_bytes = png_filter_decode(compressed_data, width, height, channels)
            for i in range(0, len(raw_bytes), channels):
                if has_alpha:
                    r, g, b, a = raw_bytes[i:i+4]
                    pixels.append((r, g, b, a))
                else:
                    r, g, b = raw_bytes[i:i+3]
                    pixels.append((r, g, b, 255))

        elif compression == 7:  
            raw_bytes = png_filter_decode(compressed_data, width, height, channels)
            for i in range(0, len(raw_bytes), channels):
                if has_alpha:
                    r, g, b, a = raw_bytes[i:i+4]
                    pixels.append((r, g, b, a))
                else:
                    r, g, b = raw_bytes[i:i+3]
                    pixels.append((r, g, b, 255))

        elif compression == 8:  
            rle_data = png_filter_decode(compressed_data, width, height, channels)
            raw_bytes = run_length_decode(rle_data, channels, pixel_count)
            
            for i in range(0, len(raw_bytes), channels):
                if has_alpha:
                    r, g, b, a = raw_bytes[i:i+4]
                    pixels.append((r, g, b, a))
                else:
                    r, g, b = raw_bytes[i:i+3]
                    pixels.append((r, g, b, 255))

        elif compression == 9:   
            png_compressed = zlib.decompress(compressed_data)
            raw_bytes = png_filter_decode(png_compressed, width, height, channels)
            
            for i in range(0, len(raw_bytes), channels):
                if has_alpha:
                    r, g, b, a = raw_bytes[i:i+4]
                    pixels.append((r, g, b, a))
                else:
                    r, g, b = raw_bytes[i:i+3]
                    pixels.append((r, g, b, 255))

        elif compression == 10:  
            png_compressed = zlib.decompress(compressed_data)
            raw_bytes = png_filter_decode(png_compressed, width, height, channels)
            
            for i in range(0, len(raw_bytes), channels):
                if has_alpha:
                    r, g, b, a = raw_bytes[i:i+4]
                    pixels.append((r, g, b, a))
                else:
                    r, g, b = raw_bytes[i:i+3]
                    pixels.append((r, g, b, 255))

        else:
            raise ValueError(f"Unsupported compression type: {compression}")

    while len(pixels) < pixel_count:
        pixels.append((0, 0, 0, 255))  
    pixels = pixels[:pixel_count]

    img = Image.new("RGBA", (width, height))
    img.putdata(pixels)
    return img

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python from_pix.py input.pix output.png")
    else:
        img = load_pix(sys.argv[1])
        img.save(sys.argv[2])