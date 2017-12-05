""" Live plotting of data received by one of the readers """

import sys
import time
import collections
import matplotlib
from matplotlib import pyplot as plt
from ring import Ring

import warnings
warnings.filterwarnings("ignore", ".*GUI is implemented.*")


ops = {"textColor": (230 / 255,) * 3,
       "windowColor": (11 / 255,) * 3,
       "plotBackgroundColor": (22 / 255,) * 3,
       "colorPalette": "2.0"}

if ops["colorPalette"] == "2.0":
  # Set line colors to match those of matplotlib 2.0
  if int(matplotlib.__version__.split('.')[0]) < 2:
    matplotlib.rcParams["axes.color_cycle"] = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]
elif ops["colorPalette"] == "colorBlind":
  matplotlib.rcParams["axes.color_cycle"] = ['#a6cee3', '#1f78b4', '#b2df8a', '#33a02c', '#fb9a99', '#e31a1c', '#fdbf6f', '#ff7f00', '#cab2d6', '#6a3d9a']
elif ops["colorPalette"] == "old":
  print("Not implemented yet")
else:
  print("Unknown colorPalette value")

# Remove matplotlibs default keybindings
for k, v in sorted(plt.rcParams.items()):
  if k.startswith('keymap'):
    plt.rcParams[k] = []


class MissingLabelError(Exception):
  pass


class Plotter(object):
  def __init__(self, reader, ringLength, labels, _ops=ops):
    self.reader = reader
    self.ringLength = ringLength
    self.ops = _ops
    self.fig = plt.figure()
    self.fig.canvas.mpl_connect('key_press_event', self.press)
    self.labels = labels
    self.setUp(False)

    self.lastPlotUpdate = time.time()
    self.freezePlot = False
    self.receivingCommand = False
    self.command = ''

  def setUp(self, discover):
    if discover:
      print("Looking for labels automatically..")
      self.labels = discoverLabels(self.reader)
      print("Found labels: {:}".format(', '.join(self.labels)))

    self.freezePlot = False
    self.rings = {}

    self.fig.patch.set_facecolor(self.ops["windowColor"])
    for i, l in enumerate(self.labels):
      self.initializePlot(i, l)

    print("\nNumber of data points for each label:")
    for l in self.labels:
      print("{:}: {:} ".format(l, self.rings[l].nY))

  def initializePlot(self, i, l):
    # Create subplot
    ax = self.fig.add_subplot(len(self.labels), 1, i + 1, facecolor=self.ops["plotBackgroundColor"])

    # Set up data rings and lines
    packageLength = getLinesPerType(l, self.reader)
    self.rings[l] = Ring(packageLength, self.ringLength)
    self.rings[l].lineSets = []
    for j in range(packageLength):
      if "ls" in self.ops or "linestyle" in self.ops:
        self.rings[l].lineSets.append(ax.plot([], [], label=chr(ord('a') + j))[0])
      else:
        self.rings[l].lineSets.append(ax.plot([], [], label=chr(ord('a') + j))[0])
    self.rings[l].ax = ax

    # Set plot layout and style
    ax.set_title(l, color=self.ops["textColor"])
    ax.legend(loc=2)
    ax.xaxis.label.set_color(self.ops["textColor"])
    # ax.yaxis.label.set_color(self.ops["textColor"])
    ax.tick_params(axis='x', colors=self.ops["textColor"])
    ax.tick_params(axis='y', colors=self.ops["textColor"])

  def update(self):
    self.getData()
    if time.time() - self.lastPlotUpdate > 0.03:
      self.updatePlotData()
      self.lastPlotUpdate = time.time()

  def updatePlotData(self):
    if not self.freezePlot:
      for ring in self.rings.values():
        # Set data for each line
        for j in range(ring.nY):
          ring.lineSets[j].set_data(ring.xs, ring.yData[j, :])

        # Set axis limits. Last value in ylim, 1e-4, is added to suppress warning about collapsed axis from matplotlib after reset
        deltaY = (ring.maxY - ring.minY) * 0.1
        ring.ax.set_ylim(ring.minY - deltaY, ring.maxY + deltaY)
        ring.ax.set_xlim(ring.xs[ring.head] - ring.length, ring.xs[ring.head])
        # Allow for '-' line style by not drawing line from "data[-1] to data[0]"
        ring.looseTail()

      # Draw lines
      plt.pause(0.001)
      # Allow for '-' line style by not drawing line from "data[-1] to data[0]"
      for ring in self.rings.values():
        ring.fixTail()
    else:
      plt.pause(0.001)

  def press(self, event):
    # Combine key presses into command
    if self.receivingCommand:
      if event.key == 'enter':
        self.receivingCommand = False
        print("\nSending '{:}'".format(self.command))
        self.reader.write(self.command + "\r\n")
        self.command = ''
      else:
        self.command += event.key
        sys.stdout.write("\r{:}".format(self.command))
      return

    # Reset y-axes
    if event.key == 'x':
      for ring in self.rings.values():
        ring.reset()

    # Pause plot (data will still be received)
    elif event.key == 'p':
      self.freezePlot = not self.freezePlot

    # Reset and discover labels
    elif event.key == 'r':
      self.fig.clear()
      self.setUp(True)

    # Save current plot window
    elif event.key == 'g':
      self.fig.savefig('{:.0f}.png'.format(time.time()), bbox_inches='tight', facecolor=self.fig.get_facecolor(), edgecolor='none')

    # Start/stop listining command key presses
    elif event.key == 'enter':
      print("listening for message until next enter key press:")
      self.receivingCommand = True

    # Close and quit
    elif event.key == 'q':
      plt.close(event.canvas.figure)
      self.reader.closeConnection()
      sys.exit()

  def getData(self):
    s, data, isNumerical = self.reader()
    if isNumerical and s in self.labels and len(data) == self.rings[s].nY:
      self.rings[s].update(data)
    elif isCommand(s):
      event = FakeKeyEvent(data[0].strip())
      print("Received command in data stream: {}".format(event.key))
      self.press(event)
    else:
      if s:
        if len(data) == 0:
          print(s)
        else:
          print(s, *data)


class FakeKeyEvent(object):
  def __init__(self, key):
    self.key = key


def isCommand(s):
  if s == 'COMMAND':
    return True


def discoverLabels(reader):
  discoverDuration = 1
  print("Discovering labels by looking at packages for {:} second{:}".format(discoverDuration, 's' if discoverDuration != 1 else ''))
  seenLabels = collections.defaultdict(int)
  timeAtStart = time.time()
  while time.time() - timeAtStart < discoverDuration:
    s, data, isNumerical = reader()
    if s:
      if isNumerical:
        seenLabels[s] += 1

  # Expecting any label seen at least twice to be actual label
  minThreshold = 2
  possibleLabels = [label for label, count in seenLabels.items() if count >= minThreshold]
  return sorted(possibleLabels)


def getLinesPerType(label, reader):
  discoverDuration = 1
  seenLabels = collections.defaultdict(int)
  timeAtStart = time.time()
  while time.time() - timeAtStart < discoverDuration:
    s, data, isNumerical = reader()
    if isNumerical:
      seenLabels[s] += 1
      if s == label and 0 < len(data) <= 15:
        return len(data)
  pretty = '\n'.join([k + ': ' + str(v) for k, v in seenLabels.items()])
  raise MissingLabelError("Label: '{:}' not found after looking for it for {:} second{:}\nReceived labels:\n{:}".format(label, discoverDuration, 's' if discoverDuration != 1 else '', pretty))
