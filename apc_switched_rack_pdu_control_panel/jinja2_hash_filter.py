import hashlib

def get_hash(data, hashtype='sha1'):
    try:
        h = hashlib.new(hashtype)
    except Exception as e:
        # hash is not supported?
        raise AttributeError(f'No hashing function named {hashtype}') from e

    h.update(data.encode("utf-8"))
    return h.hexdigest()
