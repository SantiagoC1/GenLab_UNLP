"""Minimal QR code generator (versions 1 and 2, byte mode, error correction level L).

Enough for short texts such as coupon codes. It exists because the backend has no QR library
and adding a dependency needs the team's approval. The output is a standard QR code: it follows
the layout described in ISO/IEC 18004 with the fixed mask 0.
"""

# version -> (size, data codewords, error correction codewords, remainder bits, alignment centers)
_VERSIONS = {
    1: (21, 19, 7, 0, ()),
    2: (25, 34, 10, 7, (6, 18)),
}
MAX_BYTES = 32  # capacity of version 2-L in byte mode
_FORMAT_BITS_L = 1


def _gf_tables() -> tuple[list[int], list[int]]:
    exp, log = [0] * 512, [0] * 256
    value = 1
    for i in range(255):
        exp[i] = value
        log[value] = i
        value <<= 1
        if value & 0x100:
            value ^= 0x11D
    for i in range(255, 512):
        exp[i] = exp[i - 255]
    return exp, log


_EXP, _LOG = _gf_tables()


def _gf_mul(a: int, b: int) -> int:
    return 0 if a == 0 or b == 0 else _EXP[_LOG[a] + _LOG[b]]


def _reed_solomon(data: list[int], degree: int) -> list[int]:
    generator = [1]
    for i in range(degree):
        nxt = [0] * (len(generator) + 1)
        for j, coefficient in enumerate(generator):
            nxt[j] ^= coefficient
            nxt[j + 1] ^= _gf_mul(coefficient, _EXP[i])
        generator = nxt
    remainder = [0] * degree
    for byte in data:
        factor = byte ^ remainder[0]
        remainder = remainder[1:] + [0]
        for i in range(degree):
            remainder[i] ^= _gf_mul(generator[i + 1], factor)
    return remainder


def _codewords(payload: bytes, version: int) -> list[int]:
    _, data_cw, ec_cw, _, _ = _VERSIONS[version]
    bits = "0100" + format(len(payload), "08b") + "".join(format(b, "08b") for b in payload)
    bits += "0" * min(4, data_cw * 8 - len(bits))
    bits += "0" * (-len(bits) % 8)
    data = [int(bits[i : i + 8], 2) for i in range(0, len(bits), 8)]
    pad = (0xEC, 0x11)
    while len(data) < data_cw:
        data.append(pad[(len(data) - len(bits) // 8) % 2])
    return data + _reed_solomon(data, ec_cw)


def _format_bits() -> int:
    data = _FORMAT_BITS_L << 3 | 0  # error correction level L, mask 0
    remainder = data
    for _ in range(10):
        remainder = (remainder << 1) ^ ((remainder >> 9) * 0x537)
    return (data << 10 | remainder) ^ 0x5412


def encode(text: str) -> list[list[bool]]:
    """Returns the QR matrix (True is a dark module), without the quiet zone."""
    payload = text.encode("utf-8")
    version = 1 if len(payload) <= 17 else 2
    if len(payload) > MAX_BYTES:
        raise ValueError(f"El texto es demasiado largo para el QR ({MAX_BYTES} bytes como máximo).")
    size, _, _, remainder_bits, alignment = _VERSIONS[version]
    modules = [[False] * size for _ in range(size)]
    function = [[False] * size for _ in range(size)]

    def put(x: int, y: int, dark: bool) -> None:
        modules[y][x] = dark
        function[y][x] = True

    for i in range(size):  # timing patterns
        put(6, i, i % 2 == 0)
        put(i, 6, i % 2 == 0)
    for cx, cy in ((3, 3), (size - 4, 3), (3, size - 4)):  # finder patterns with separators
        for dy in range(-4, 5):
            for dx in range(-4, 5):
                x, y = cx + dx, cy + dy
                if 0 <= x < size and 0 <= y < size:
                    put(x, y, max(abs(dx), abs(dy)) not in (2, 4))
    for cx in alignment:  # alignment patterns, except the ones that would overlap a finder
        for cy in alignment:
            if (cx, cy) in ((6, 6), (6, alignment[-1]), (alignment[-1], 6)):
                continue
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    put(cx + dx, cy + dy, max(abs(dx), abs(dy)) != 1)

    bits = _format_bits()

    def bit(i: int) -> bool:
        return (bits >> i) & 1 == 1

    for i in range(6):
        put(8, i, bit(i))
    put(8, 7, bit(6))
    put(8, 8, bit(7))
    put(7, 8, bit(8))
    for i in range(9, 15):
        put(14 - i, 8, bit(i))
    for i in range(8):
        put(size - 1 - i, 8, bit(i))
    for i in range(8, 15):
        put(8, size - 15 + i, bit(i))
    put(8, size - 8, True)  # always dark

    data = _codewords(payload, version)
    total_bits = len(data) * 8 + remainder_bits
    index = 0
    for right in range(size - 1, 0, -2):
        if right == 6:
            right = 5
        for vertical in range(size):
            for j in range(2):
                x = right - j
                y = size - 1 - vertical if ((right + 1) & 2) == 0 else vertical
                if not function[y][x] and index < total_bits:
                    if index < len(data) * 8:
                        modules[y][x] = (data[index >> 3] >> (7 - (index & 7))) & 1 == 1
                    index += 1
    for y in range(size):  # mask 0
        for x in range(size):
            if not function[y][x] and (x + y) % 2 == 0:
                modules[y][x] = not modules[y][x]
    return modules


def to_svg(modules: list[list[bool]], quiet_zone: int = 4) -> str:
    size = len(modules)
    cells = "".join(
        f"M{x + quiet_zone},{y + quiet_zone}h1v1h-1z"
        for y, row in enumerate(modules)
        for x, dark in enumerate(row)
        if dark
    )
    total = size + 2 * quiet_zone
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total} {total}" '
        'shape-rendering="crispEdges"><rect width="100%" height="100%" fill="#fff"/>'
        f'<path d="{cells}" fill="#000"/></svg>'
    )
