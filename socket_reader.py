import socket
import numpy as np
import select
from interpretations import toFloat, alwaysTrue


class Reader(object):
  """ Connects to a socket server that streams data """

  def __init__(self, host, port, dataIntegrityFync=alwaysTrue, dataInterpretFunc=toFloat):
    self.soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print("Connecting to {} at {}".format(host, port))
    self.soc.connect((host, port))
    print("Connected")
    self.dataInterpretFunc = dataInterpretFunc
    self.dataIntegrityFync = dataIntegrityFync

  def closeConnection(self):
    self.soc.close()

  def write(self, data):
    self.soc.sendall(data.encode())

  def __call__(self, label=None, raw=False):
    """ label: data group label
      raw: if true returns the data as it was read (string)
      dtype: data type that the data is converted to if raw is false """
    rawData = ''
    while True:
      # Read one byte at a time
      try:
        if select.select([self.soc], [], [], 0.5)[0]:
          data = self.soc.recv(1)
          char = data.decode()
        else:
          break
      except UnicodeDecodeError:
        break
      if not char:
        # Connection closed or broken
        print("Connection lost/closed")
        self.closeConnection()
        break

      # We expect the data to be terminated with "\r\n"
      if char == '\r':
        continue
      # End of package - return result
      elif char == '\n':

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
          return splittedData[0], splittedData[1:], False
        break
      else:
        rawData += char
    return rawData if raw else rawData, [], False


if __name__ == '__main__':
  import sys
  if len(sys.argv) == 1:
    print("Usage: <host address> <host port>")
    sys.exit()

  host = sys.argv[1]
  port = int(sys.argv[2])
  reader = Reader(host, port)

  while True:
    print(reader(raw=True))
    sys.stdout.flush()
