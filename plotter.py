""" Live plotting of data received by one of the readers """

import sys
import time
import collections
import numpy as np
import matplotlib
from matplotlib import pyplot as plt
from ring import Ring

# Set line colors to match those of matplotlib 2.0
if int(matplotlib.__version__.split('.')[0]) < 2:
    matplotlib.rcParams["axes.color_cycle"] = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]

# Remove matplotlibs default keybindings
for k, v in sorted(plt.rcParams.items()):
    if k.startswith('keymap'):
        plt.rcParams[k] = []


class MissingLabelError(Exception):
    pass


class Plotter(object):
    def __init__(self, labels, reader, ringLength, plotParams={}):
        self.reader = reader
        self.ringLength = ringLength
        self.plotParams = plotParams
        self.fig = plt.figure()
        self.fig.canvas.mpl_connect('key_press_event', self.press)
        self.setUp(labels)

        self.lastPlotUpdate = time.time()
        self.freezePlot = False
        self.receivingCommand = False
        self.command = ''

    def setUp(self, labels):
        if not labels:
            print("No labels specified - Trying to find them automatically..")
            self.labels = discoverLabels(self.reader)
            print("Found labels: {:}".format(', '.join(self.labels)))
        else:
            self.labels = labels

        self.freezePlot = False
        self.rings = {}

        textColor = 230/255
        windowColor = 11/255
        plotBackgroundColor = 22/255

        self.fig.patch.set_facecolor((windowColor,)*3)
        for i, s in enumerate(self.labels):
            ax = self.fig.add_subplot(len(self.labels), 1, i + 1, axisbg=(plotBackgroundColor,)*3)
            packageLength = getLinesPerType(s, self.reader)
            self.rings[s] = Ring(packageLength, self.ringLength)
            self.rings[s].lineSets = []
            for j in range(packageLength):
                if "ls" in self.plotParams or "linestyle" in self.plotParams:
                    self.rings[s].lineSets.append(ax.plot([], [], label=chr(ord('a')+j), **self.plotParams)[0])
                else:
                    self.rings[s].lineSets.append(ax.plot([], [], '.', label=chr(ord('a')+j), **self.plotParams)[0])
            ax.set_title(s, color=(textColor,)*3)
            ax.legend(loc=2)
            ax.xaxis.label.set_color((textColor,)*3)
            # ax.yaxis.label.set_color((textColor,)*3)
            ax.tick_params(axis='x', colors=(textColor,)*3)
            ax.tick_params(axis='y', colors=(textColor,)*3)
            self.rings[s].ax = ax

        print("\nNumber of data points for each label:")
        for s in self.labels:
            print("{:}: {:} ".format(s, self.rings[s].nY))

    def update(self):
        self.getData()
        if time.time() - self.lastPlotUpdate > 0.03:
            self.updatePlotData()
            self.lastPlotUpdate = time.time()

    def updatePlotData(self):
        if not self.freezePlot:
            for ring in self.rings.values():
                for j in range(ring.nY):
                    ring.lineSets[j].set_data(ring.xs, ring.yData[j, :])

                deltaY = (ring.maxY - ring.minY) * 0.1
                # Last value, 1e-4, is added to suppress warning about collapsed axis from matplotlib after reset
                ring.ax.set_ylim(ring.minY - deltaY, ring.maxY + deltaY + 1e-4)
                ring.ax.set_xlim(ring.xs[ring.head] - ring.length, ring.xs[ring.head])
                ring.looseTail()

            for ring in self.rings.values():
                ring.fixTail()
        plt.pause(0.001)

    def press(self, event):
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

        if event.key == 'x':
            for ring in self.rings.values():
                ring.reset()

        elif event.key == 'p':
            self.freezePlot = not self.freezePlot

        elif event.key == 'r':
            self.fig.clear()
            self.setUp([])

        elif event.key == 'g':
            self.fig.savefig('{:.0f}.png'.format(time.time()), bbox_inches='tight', facecolor=self.fig.get_facecolor(), edgecolor='none')

        elif event.key == 'enter':
            print("listening for message until next enter key press:")
            self.receivingCommand = True

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
