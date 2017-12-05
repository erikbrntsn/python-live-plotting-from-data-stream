import sys
from interpretations import toFloat, alwaysTrue


class Reader(object):
  def __init__(self, dataIntegrityFync=alwaysTrue, dataInterpretFunc=toFloat):
    self.dataInterpretFunc = dataInterpretFunc
    self.dataIntegrityFync = dataIntegrityFync

  def closeConnection(self):
    pass

  def write(self, data):
    print("Can not write data to server when using pipe reader.\nMessage: '{:}' has been discarded".format(data))

  def __call__(self, label=None, raw=False):
    """ label: data group label
      raw: if true returns the data as it was read (string) """
    while True:
      rawData = sys.stdin.readline()
      if raw:
        # return whatever was received
        return rawData

      try:
        # Interpret the received data
        dataIsGood, rawData = self.dataIntegrityFync(rawData)
        if dataIsGood:
          splittedData = rawData.split(',')
          if label is None or label == splittedData[0]:
            return splittedData[0], self.dataInterpretFunc(splittedData[1:]), True
      except ValueError:
        if len(splittedData) > 1:
          return splittedData[0], splittedData[1:], False
      return rawData, [], False


if __name__ == '__main__':
  reader = Reader()

  while True:
    s, data, succes = reader()
    print(s, data)
