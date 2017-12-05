import numpy as np

# Integrity checks


def crc(data):
  crc = ord(data[-1])
  data = data[:-1]
  if crc == calcCrc(data):
    return True, data
  else:
    return False, data


def alwaysTrue(data):
  return True, data


# Data conversion funcs


def toFloat(data, dtype=float):
  np.array(list(map(dtype, data)))


# Helper funcs


def calcCrc(s):
  crc = 0
  for c in s:
    crc ^= ord(c)
  return crc
