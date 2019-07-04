import logging
from base64 import b64decode, b64encode

logger = logging.getLogger(__name__)


def get_finger_print(pubkey, type):
    possible_format, pubkey, comment = (pubkey.split(' ', 2) + [''])[:3]
    pubkey = b64decode(pubkey)

    # resolve key length from the RSA modulus length (doesn't work for elliptic curve keys
    from struct import unpack
    format_len = unpack('>I', pubkey[:4])[0]
    explen = unpack('>I', pubkey[4 + format_len:4 + format_len + 4])[0]
    modlen = unpack('>I', pubkey[4 + format_len + 4 + explen:4 + format_len + 4 + explen + 4])[0]
    keylen = (modlen - 1) * 8

    # this should always be the same as `possible_format`. here it's read from the binary for the academic curiosity
    format_ = pubkey[4:4 + format_len]
    format_ = format_.decode('ascii').split('-', 1)[1].upper()

    from hashlib import sha256, md5

    md5fp = md5(pubkey).hexdigest()
    sha256fp = b64encode(sha256(pubkey).digest())

    logger.info("%d MD5:%s %s (%s)" % (
        keylen,
        ':'.join(md5fp[i:i + 2] for i in range(0, len(md5fp), 2)),
        comment,
        format_,
    ))
    logger.info("%d SHA256:%s %s (%s)" % (
        keylen,
        sha256fp.decode('ascii').rstrip('='),
        comment,
        format_,
    ))
    if type == 'md5':
        return ':'.join(md5fp[i:i + 2] for i in range(0, len(md5fp), 2))
    elif type == 'sha256':
        return sha256fp.decode('ascii').rstrip('=')
    else:
        raise ValueError("type must be md5 or sha256")
