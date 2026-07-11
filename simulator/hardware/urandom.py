try:
    from random import getrandbits, randint, random, randrange, seed, choice
except ImportError:
    pass


def randbytes(n):
    return bytes(getrandbits(8) for _ in range(int(n)))
