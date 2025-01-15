import sys

IS_PY3 = sys.version_info[0] >= 3

def _b(s):
    """string to byte conversion (utf-8)"""
    if IS_PY3:
        return s.encode('utf-8')
    else:
        return s

def _s(b):
    """byte to string conversion (utf-8)"""
    if IS_PY3:
        return b.decode('utf-8') if hasattr(b, 'decode') else b
    else:
        return b