#!/bin/python3
import numpy as np
import time
import sys


class MissingArgument(Exception):
  pass


if len(sys.argv) == 1:
  raise MissingArgument("\n\nUsage:writer.py <channel (socket/pipe)>\n")
else:
  channel = sys.argv[1]

if channel == 'socket':
  import socket
  class SocWriter(object):
    def __init__(self):
      self.host = ''
      self.port = 50007
      self.soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      defaultAddress = True
      while True:
        try:
          # Try to get the default port
          self.soc.bind((self.host, self.port))
          break
        except OSError:
          # The default port was not given to us by the OS. Choose new port. This can
          # happen if the connection is not closed properly. The port is usually
          # released within a few minutes after improper termination.
          defaultAddress = False
          self.port += 1
      if not defaultAddress:
        print("Assigned port {:}".format(self.port))
      print("Writer socket at {}".format(self.soc.getsockname()))
      self.soc.listen(1)
      self.conn, self.addr = self.soc.accept()

    def send(self, data):
      self.conn.sendall((data + '\n').encode())

  writer = SocWriter()

else:
  class StdoutWriter(object):
    def send(self, data):
      print(data)
      try:
        sys.stdout.flush()
      except BrokenPipeError:
        exit()
  writer = StdoutWriter()

t = 0
nx = 5
ny = 3
nz = 1
refTime = time.time()

slowRate = 30
lastSlowPrint = 0
while True:
  # if time.time() - refTime > 3:
    # Test restting of figure and labels - press r
    # x2 = np.sin(t*0.01 + np.array([i/3 for i in range(3)])*np.pi)
    # writer.send("qwe,{:}".format(','.join(["{:0.4f}".format(val) for val in x2])))
    # y2 = np.exp(-(x2[:2]))
    # writer.send("asd,{:}".format(','.join(["{:0.4f}".format(val) for val in y2])))
    # if time.time() - lastSlowPrint > 1/slowRate:
    #     z2 = np.random.rand(1)
    #     writer.send("123,{:}".format(','.join(["{:0.4f}".format(val) for val in z2])))
    #     lastSlowPrint = time.time()
    # t += 1
  # else:
  x = np.sin(t*0.01 + np.array([i/nx for i in range(nx)])*np.pi)
  writer.send("SinData,{:}".format(','.join(["{:0.4f}".format(val) for val in x])))
  y = np.exp(-(x[:ny]))
  writer.send("SomethingElse,{:}".format(','.join(["{:0.4f}".format(val) for val in y])))
  if time.time() - lastSlowPrint > 1/slowRate:
    z = np.random.rand(1)
    writer.send("0,{:}".format(','.join(["{:0.4f}".format(val) for val in z])))
    lastSlowPrint = time.time()
  t += 1
  time.sleep(0.01)
