import serial
import select
from interpretations import toFloat, alwaysTrue


class Reader(object):
  """ Sets up socket server that data streaming clients can connect to """
  # Use some random port

  def __init__(self, port="/dev/ttyUSB0", baudrate=57600, dataIntegrityFync=alwaysTrue, dataInterpretFunc=toFloat):
    self.port = port
    self.baudrate = baudrate
    self.ser = serial.Serial(port)
    self.ser.baudrate = baudrate
    self.dataInterpretFunc = dataInterpretFunc
    self.dataIntegrityFync = dataIntegrityFync

  def closeConnection(self):
    self.ser.close()

  def write(self, data):
    print('Writing: "{:}"'.format(data.strip()))
    self.ser.write(data.encode("utf-8"))

  def __call__(self, label=None, raw=False):
    """ label: data group label
      raw: if true returns the data as it was read (string)
      dtype: data type that the data is converted to if raw is false """
    while True:
      if select.select([self.ser], [], [], 0.02)[0]:
        rawData = self.ser.readline()
      else:
        rawData = b''

      if raw:
        # return whatever was received
        return rawData

      try:
        decodedData = rawData.decode()
      except UnicodeDecodeError:
        break

      try:
        # Interpret the received data
        dataIsGood, decodedData = self.dataIntegrityFync(decodedData)
        if dataIsGood:
          splittedData = decodedData.split(',')
          if label is None or label == splittedData[0]:
            return splittedData[0], self.dataInterpretFunc(splittedData[1:]), True
      except ValueError:
        return splittedData[0], splittedData[1:], False
      break
    return rawData, [], False


if __name__ == '__main__':
  reader = Reader()

  while True:
    data = reader()
    if data:
      print(data)
