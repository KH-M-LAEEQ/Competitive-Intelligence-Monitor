import imagehash
from PIL import Image


def compare(old_path: str, new_path: str) -> float:
    """Perceptual-hash distance between two screenshots, normalized to
    0 (identical) .. 1 (maximally different). Cheap and robust to minor
    anti-aliasing/rendering noise, unlike a raw pixel diff.
    """

    old_hash = imagehash.phash(Image.open(old_path))
    new_hash = imagehash.phash(Image.open(new_path))

    max_distance = old_hash.hash.size

    # imagehash's `-` operator returns a numpy integer/float scalar, not a
    # plain Python type — psycopg2 has no adapter for numpy scalars and
    # fails to bind it (it falls back to repr(), producing invalid SQL like
    # "np.float64(0.0)"), so this must be cast before it ever reaches the DB.
    return float(old_hash - new_hash) / max_distance
