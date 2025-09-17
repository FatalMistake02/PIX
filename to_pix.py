# to_pix.py

from PIL import Image
import sys
import zlib
import multiprocessing


def has_alpha(pixels):
    for r, g, b, a in pixels:
        if a != 255:
            return True
    return False


def rle_encode(data, channels):
    if not data:
        return bytearray()
    result = bytearray()
    i = 0
    while i < len(data):
        pixel = data[i:i+channels]
        run = 1
        while (i + run * channels < len(data) and 
               run < 255 and
               data[i + run * channels:i + (run + 1) * channels] == pixel):
            run += 1
        result.append(run)
        result.extend(pixel)
        i += run * channels
    return result


def png_filter(data, width, height, channels):
    filtered = bytearray()
    row_bytes = width * channels
    for row in range(height):
        start = row * row_bytes
        row_data = data[start:start + row_bytes]
        attempts = []
        none_f = bytearray([0]) + row_data
        attempts.append(none_f)
        if width > 1:
            sub_f = bytearray([1])
            for i in range(len(row_data)):
                if i < channels:
                    sub_f.append(row_data[i])
                else:
                    sub_f.append((row_data[i] - row_data[i - channels]) % 256)
            attempts.append(sub_f)
        if row > 0:
            up_f = bytearray([2])
            prev_row = data[(row - 1) * row_bytes:row * row_bytes]
            for i in range(len(row_data)):
                up_f.append((row_data[i] - prev_row[i]) % 256)
            attempts.append(up_f)
        if row > 0 and width > 1:
            avg_f = bytearray([3])
            prev_row = data[(row - 1) * row_bytes:row * row_bytes]
            for i in range(len(row_data)):
                left = row_data[i - channels] if i >= channels else 0
                up = prev_row[i]
                pred = (left + up) // 2
                avg_f.append((row_data[i] - pred) % 256)
            attempts.append(avg_f)
        if row > 0:
            paeth_f = bytearray([4])
            prev_row = data[(row - 1) * row_bytes:row * row_bytes]
            for i in range(len(row_data)):
                left = row_data[i - channels] if i >= channels else 0
                up = prev_row[i]
                up_left = prev_row[i - channels] if i >= channels else 0
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
                paeth_f.append((row_data[i] - pred) % 256)
            attempts.append(paeth_f)
        best = min(attempts, key=lambda x: sum(abs(b - 128) for b in x[1:]))
        filtered.extend(best)
    return zlib.compress(filtered, level=9)


def png_filter_all(data, width, height, channels):
    row_bytes = width * channels
    none_d, sub_d, up_d, avg_d, paeth_d = bytearray(), bytearray(), bytearray(), bytearray(), bytearray()
    for row in range(height):
        start = row * row_bytes
        row_data = data[start:start + row_bytes]
        none_d.extend([0])
        none_d.extend(row_data)
        sub_d.extend([1])
        for i in range(len(row_data)):
            if i < channels:
                sub_d.append(row_data[i])
            else:
                sub_d.append((row_data[i] - row_data[i - channels]) % 256)
        up_d.extend([2])
        if row == 0:
            up_d.extend(row_data)
        else:
            prev_row = data[(row - 1) * row_bytes:row * row_bytes]
            for i in range(len(row_data)):
                up_d.append((row_data[i] - prev_row[i]) % 256)
        avg_d.extend([3])
        prev_row = data[(row - 1) * row_bytes:row * row_bytes] if row > 0 else bytearray(row_bytes)
        for i in range(len(row_data)):
            left = row_data[i - channels] if i >= channels else 0
            up = prev_row[i]
            pred = (left + up) // 2
            avg_d.append((row_data[i] - pred) % 256)
        paeth_d.extend([4])
        prev_row = data[(row - 1) * row_bytes:row * row_bytes] if row > 0 else bytearray(row_bytes)
        for i in range(len(row_data)):
            left = row_data[i - channels] if i >= channels else 0
            up = prev_row[i]
            up_left = prev_row[i - channels] if i >= channels else 0
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
            paeth_d.append((row_data[i] - pred) % 256)
    filters = {
        "PNG_none": zlib.compress(none_d, level=9),
        "PNG_sub": zlib.compress(sub_d, level=9),
        "PNG_up": zlib.compress(up_d, level=9),
        "PNG_avg": zlib.compress(avg_d, level=9),
        "PNG_paeth": zlib.compress(paeth_d, level=9),
    }
    best = min(filters, key=lambda x: len(filters[x]))
    return (len(filters[best]), 7, filters[best], best)


def compress_worker(task):
    method, data, args = task
    w, h, c = args

    if method == "raw":
        return (len(data), 0, data, "raw")

    elif method == "rle":
        rle_d = rle_encode(data, c)
        comp = zlib.compress(rle_d, level=9)
        return (len(comp), 1, comp, "rle")

    elif method == "zlib":
        comp = zlib.compress(data, level=9)
        return (len(comp), 2, comp, "zlib")

    elif method.startswith("zlib_"):
        strat_map = {
            "zlib_default": zlib.Z_DEFAULT_STRATEGY,
            "zlib_filtered": zlib.Z_FILTERED,
            "zlib_huffman": zlib.Z_HUFFMAN_ONLY
        }
        if method not in strat_map:
            return (float('inf'), -1, None, method)
        try:
            compressor = zlib.compressobj(level=9, strategy=strat_map[method])
            comp = compressor.compress(data) + compressor.flush()
            return (len(comp), 3, comp, method)
        except Exception:
            return (float('inf'), -1, None, method)

    elif method == "png_row":
        comp = png_filter(data, w, h, c)
        return (len(comp), 6, comp, "png_row")

    elif method == "png_all":
        return png_filter_all(data, w, h, c)

    elif method == "rle+png_row":
        rle_d = rle_encode(data, c)
        comp = png_filter(rle_d, w, h, c)
        return (len(comp), 8, comp, "rle+png_row")

    elif method == "rle+png_all":
        rle_d = rle_encode(data, c)
        return png_filter_all(rle_d, w, h, c)

    elif method == "png_row+zlib":
        comp = png_filter(data, w, h, c)
        comp2 = zlib.compress(comp, level=9)
        return (len(comp2), 9, comp2, "png_row+zlib")

    elif method == "png_all+zlib":
        _, _, comp, _ = png_filter_all(data, w, h, c)
        comp2 = zlib.compress(comp, level=9)
        return (len(comp2), 10, comp2, "png_all+zlib")

    elif method == "palette":
        pixels = list(Image.frombytes("RGBA" if c == 4 else "RGB", (w, h), data).getdata())
        unique = len(set(pixels))
        palette = list(set(pixels))
        palette_bytes = bytearray()
        for col in palette:
            palette_bytes.extend([col[0], col[1], col[2]] + ([col[3]] if c == 4 else []))
        color_map = {col: i for i, col in enumerate(palette)}
        indices = bytearray([color_map[p] for p in pixels])
        pal_data = bytearray([len(palette)]) + palette_bytes + indices
        comp = zlib.compress(pal_data, level=9)
        return (len(comp), 5, comp, f"palette_{unique}")

    return (float('inf'), -1, None, "error")



def save_pix(input_file, output_file):
    img = Image.open(input_file).convert("RGBA")
    w, h = img.size
    pixels = list(img.getdata())
    use_alpha = has_alpha(pixels)
    c = 4 if use_alpha else 3
    data = bytearray()
    for r, g, b, a in pixels:
        data.extend([r, g, b] + ([a] if use_alpha else []))
    tasks = [
        ("raw", data, (w, h, c)),
        ("rle", data, (w, h, c)),
        ("zlib", data, (w, h, c)),
        ("zlib_default", data, (w, h, c)),
        ("zlib_filtered", data, (w, h, c)),
        ("zlib_huffman", data, (w, h, c)),
        ("png_row", data, (w, h, c)),
        ("png_all", data, (w, h, c))
    ]
    if len(set(pixels)) <= 256:
        tasks.append(("palette", data, (w, h, c)))
    with multiprocessing.Pool() as pool:
        results = pool.map(compress_worker, tasks)
    results = [r for r in results if r[0] != float('inf')]
    results.sort(key=lambda x: x[0])
    if not results:
        print("Error: no method succeeded.")
        return
    chosen_size, t, chosen, name = results[0]
    with open(output_file, "wb") as f:
        f.write(b"PX")
        f.write(w.to_bytes(2, "little"))
        f.write(h.to_bytes(2, "little"))
        flags = t | (0x10 if use_alpha else 0x00)
        f.write(bytes([flags]))
        f.write(chosen)
    orig = w * h * (4 if use_alpha else 3)
    ratio = (orig - chosen_size) / orig * 100
    print(f"Saved: {output_file}")
    print(f"Method: {name} (type={t})")
    print(f"Size: {chosen_size:,} bytes")
    print(f"Alpha: {'yes' if use_alpha else 'no'}")
    print(f"Ratio: {ratio:.2f}%")


# List of all methods that compress_worker can handle
ALL_METHODS = [
    "raw", "rle", "zlib", "zlib_default", "zlib_filtered", "zlib_huffman",
    "png_row", "png_all", "rle+png_row", "rle+png_all", "png_row+zlib",
    "png_all+zlib", "palette"
]

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python to_pix.py input.png output.pix [--scm METHOD] [--list]")
        sys.exit(1)

    if "--list" in sys.argv:
        print("Available methods:")
        for m in ALL_METHODS:
            print(f"  {m}")
        sys.exit(0)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    if "--scm" in sys.argv:
        idx = sys.argv.index("--scm")
        if idx + 1 >= len(sys.argv):
            print("Error: --scm flag requires a method name")
            sys.exit(1)
        method_name = sys.argv[idx + 1]
        if method_name not in ALL_METHODS:
            print(f"Error: unknown method '{method_name}'")
            print("Use --list to see available methods")
            sys.exit(1)

        # Load image and build data
        img = Image.open(input_file).convert("RGBA")
        w, h = img.size
        pixels = list(img.getdata())
        use_alpha = has_alpha(pixels)
        c = 4 if use_alpha else 3
        data = bytearray()
        for r, g, b, a in pixels:
            data.extend([r, g, b] + ([a] if use_alpha else []))

        # Run chosen method
        size, t, comp, name = compress_worker((method_name, data, (w, h, c)))
        if size == float("inf"):
            print(f"Error: method {method_name} failed.")
            sys.exit(1)

        with open(output_file, "wb") as f:
            f.write(b"PX")
            f.write(w.to_bytes(2, "little"))
            f.write(h.to_bytes(2, "little"))
            flags = t | (0x08 if use_alpha else 0x00)
            f.write(bytes([flags]))
            f.write(comp)
        orig = w * h * (4 if use_alpha else 3)
        ratio = (orig - size) / orig * 100
        print(f"Saved: {output_file}")
        print(f"Method: {name} (type={t})")
        print(f"Size: {size:,} bytes")
        print(f"Alpha: {'yes' if use_alpha else 'no'}")
        print(f"Ratio: {ratio:.2f}%")
    else:
        save_pix(input_file, output_file)
