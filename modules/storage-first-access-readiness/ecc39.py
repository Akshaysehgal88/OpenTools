"""Owned shortened even-parity Hamming SECDED (39,32), interleaved positions."""

PROFILE = "opentools.hamming39_32.interleaved-even.v1"
POSITIONS = tuple(position for position in range(1, 39) if position & (position - 1))
PARITY_POSITIONS = (1, 2, 4, 8, 16, 32)
DATA_MASKS = tuple(sum(1 << bit for bit, position in enumerate(POSITIONS) if position & check) for check in PARITY_POSITIONS)


def bounded(value, bits):
    if type(value) is not int or not 0 <= value < 1 << bits:
        raise ValueError("Expected unsigned " + str(bits) + "-bit integer")


def encode(data):
    bounded(data, 32)
    # Calculate check bits from data-column masks, then scatter to physical slots.
    bits = {position: (data >> bit) & 1 for bit, position in enumerate(POSITIONS)}
    for position, matrix in zip(PARITY_POSITIONS, DATA_MASKS):
        bits[position] = (data & matrix).bit_count() & 1
    word = sum(value << (position - 1) for position, value in bits.items())
    return word | ((word.bit_count() & 1) << 38)


def decode(word):
    bounded(word, 39)
    # A set physical bit contributes its one-based column to the syndrome.
    syndrome = 0
    for position in range(1, 39):
        if word & (1 << (position - 1)):
            syndrome ^= position
    odd = word.bit_count() & 1
    corrected = word
    ce, ue = False, False
    if odd:
        if syndrome == 0:
            corrected ^= 1 << 38;ce = True
        elif syndrome <= 38:
            corrected ^= 1 << (syndrome - 1);ce = True
        else:
            ue = True
    elif syndrome:
        ue = True
    data = sum(((corrected >> (position - 1)) & 1) << bit for bit, position in enumerate(POSITIONS))
    return {"data": data, "correctable": ce, "uncorrectable": ue, "syndrome": syndrome, "overall_odd": bool(odd), "corrected_codeword": corrected}


def systematic(word):
    """Permutation for the pinned reference; not a different code family."""
    bounded(word, 39)
    result = sum(((word >> (position - 1)) & 1) << bit for bit, position in enumerate(POSITIONS))
    result |= sum(((word >> (position - 1)) & 1) << (32 + bit) for bit, position in enumerate(PARITY_POSITIONS))
    return result | (((word >> 38) & 1) << 38)
