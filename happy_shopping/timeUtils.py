import time


def millisecond():
    return time.time() * 1000


def millisecond_str():
    return str(int(millisecond()))
