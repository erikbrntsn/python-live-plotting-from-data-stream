""" Live plotting of data received by one of the readers """

import sys
import time
import collections
import numpy as np
import matplotlib
from matplotlib import pyplot as plt

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
    def __init__(self, labels, reader, n, plotParams):
        self.reader = reader
        self.n = n
        self.plotParams = plotParams
        self.fig = plt.figure()
        self.fig.canvas.mpl_connect('key_press_event', self.press)
        if labels:
            self.setUp(labels)
        else:
            self.labels = labels

        self.lastPlotUpdate = time.time()
        self.lastStatus = time.time()
        self.freezePlot = False
        self.receivingCommand = False
        self.command = ''

    def setUp(self, labels):
        if not labels:
            print("No labels specified - Trying to find them automatically..")
            self.labels = self.discoverLabels()
            print("Found labels: {:}".format(', '.join(self.labels)))
        else:
            self.labels = labels

        self.c = 0
        self.freezePlot = False
        self.N = 0

        self.axs = {}
        self.lineSets = {}
        self.rings = {}
        self.xs = {}
        self.indexes = {}
        self.min_ = {}
        self.max_ = {}
        self.ls = {}
        self.dataRate = {}

        self.fig.canvas.mpl_connect('key_press_event', self.press)
        maxTries = 10
        self.fig.patch.set_facecolor((11/255, 11/255, 11/255))
        for i, s in enumerate(self.labels):
            ax = self.fig.add_subplot(len(self.labels), 1, i + 1, axisbg=(22/255,)*3)
            ax.set_xlim(0, self.n)
            ax.set_ylim(-2, 2)
            ax.xaxis.label.set_color((230/255,)*3)
            # ax.yaxis.label.set_color((230/255,)*3)
            ax.tick_params(axis='x', colors=(230/255,)*3)
            ax.tick_params(axis='y', colors=(230/255,)*3)
            self.axs[s] = ax
            self.lineSets[s] = []
            for i in range(maxTries):
                length = self.getLinesPerType(s, self.reader)
                if length is not None:
                    self.ls[s] = length
                    break
            for j in range(self.ls[s]):
                self.lineSets[s].append(ax.plot([], [], label=chr(ord('a')+j), **self.plotParams)[0])
            ax.set_title(s, color=(230/255,)*3)
            ax.legend(loc=2)
            self.axs[s] = ax

        self.reset()

        print("\nNumber of data points in each label:")
        print(self.ls)

    def update(self):
        self.getData()
        if time.time() - self.lastPlotUpdate > 0.03:
            self.updatePlotData()
            self.lastPlotUpdate = time.time()
        if time.time() - self.lastStatus > 1:
            rates = ""
            total = 0
            for l in self.labels:
                rates = rates + "{:}: {:}, ".format(l, self.dataRate[l])
                total += self.dataRate[l]
                self.dataRate[l] = 0
            # if total:
            #     print(rates + "Total: {:}".format(total))
            self.lastStatus = time.time()

    def updatePlotData(self):
        if not self.freezePlot:
            tails = {}
            for s in self.labels:
                for j in range(self.ls[s]):
                    self.lineSets[s][j].set_data(self.xs[s], self.rings[s][:, j])

                # It seems very inefficient doing the limit checks like this, here, instead of doing it when we receive the data
                change = False
                if self.rings[s].min() < self.min_[s]:
                    self.min_[s] = self.rings[s].min()
                    change = True

                if self.rings[s].max() > self.max_[s]:
                    self.max_[s] = self.rings[s].max()
                    change = True

                if change:
                    delta = (self.max_[s] - self.min_[s]) * 0.1
                    self.axs[s].set_ylim(self.min_[s] - delta, self.max_[s] + delta)

                self.axs[s].set_xlim(self.indexes[s] - self.n, self.indexes[s])

                # Set the current head to None (Nan) to avoid drawing a line from head to tail and thus across the entire plot
                # Store the current head in order not to loose the data
                tails[s] = self.rings[s][self.N, :].copy()
                self.rings[s][self.N, :] = None

            plt.pause(0.001)

            # Set the current head back to its actual value
            # This check is a little awkward, but it is possible that the labels changed as plt.pause was called and they will thereby differ from the tails keys
            if list(tails.keys()) == self.labels:
                for s in tails.keys():
                    self.rings[s][self.N, :] = tails[s].copy()
            else:
                self.reset()

    def reset(self):
        for s in self.labels:
            if list(self.rings.keys()) == self.labels:
                # The current head will be None/nan due to the updatePlotData method - use previous head instead
                self.rings[s] = np.zeros((self.n, self.ls[s])) + self.rings[s][(self.N - 1) % self.n, :]
            else:
                self.rings[s] = np.zeros((self.n, self.ls[s]))
            self.xs[s] = np.zeros(self.n)
            self.indexes[s] = 0
            self.min_[s] = float('inf')
            self.max_[s] = -float('inf')
            self.dataRate[s] = 0

    def press(self, event):
        if self.receivingCommand:
            if event.key == 'enter':
                self.receivingCommand = False
                print("Sending '{:}'".format(self.command))
                self.reader.write(self.command + "\r\n")
                self.command = ''
            else:
                self.command += event.key
            return

        if event.key == 'x':
            self.reset()

        elif event.key == 'p':
            self.freezePlot = not self.freezePlot

        elif event.key == 'r':
            self.fig.clear()
            self.setUp([])

        elif event.key == 'g':
            self.fig.savefig('{:.0f}.png'.format(time.time()), bbox_inches='tight')

        elif event.key == 'enter':
            print("listening for message until next enter key press:")
            self.receivingCommand = True

        elif event.key == 'q':
            plt.close(event.canvas.figure)
            self.reader.closeConnection()
            sys.exit()

    def getData(self):
        s, data, isNumerical = self.reader()
        if isNumerical and s in self.labels and len(data) == self.ls[s]:
            self.N = self.indexes[s] % self.n
            self.rings[s][self.N, :] = data
            self.xs[s][self.N] = self.indexes[s]
            self.indexes[s] += 1
            self.dataRate[s] += 1
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
        return s, data

    def getLinesPerType(self, label, reader):
        maxTries = 100
        seenLabels = collections.defaultdict(int)
        for _ in range(maxTries):
            s, data, isNumerical = self.reader()
            if isNumerical:
                seenLabels[s] += 1
                if s == label and 0 < len(data) <= 15:
                    return len(data)
        pretty = '\n'.join([k + ': ' + str(v) for k, v in seenLabels.items()])
        raise MissingLabelError("Label: '{:}' not found after receiving {:} data packages\nReceived labels:\n{:}".format(label, maxTries, pretty))

    def discoverLabels(self):
        # There must be a smarter/prettier way - but it does seem to be pretty robust
        maxTries = 100
        print("Discovering labels by looking at the first {} packages...".format(maxTries))
        seenLabels = collections.defaultdict(int)
        for _ in range(maxTries):
            s, data, isNumerical = self.reader()
            if s:
              if isNumerical:
                seenLabels[s] += 1
            else:
                # time.sleep(0.05)
                pass

        # Good for noisy data for equal data rates:
        # possibleLabels = [('dummy', 1)] + sorted(seenLabels.items(), key=lambda x: x[1])
        # diffs = []
        # for i in range(len(possibleLabels)-1):
        #     diffs.append(possibleLabels[i+1][1] - possibleLabels[i][1])
        # threshold = np.argmax(diffs) + 1
        # return sorted(list(zip(*possibleLabels))[0][threshold:])

        # Good for not too noisy data for different data rates
        maxExpectedLabels = 10
        threshold = maxTries / maxExpectedLabels
        possibleLabels = [l for l, s in seenLabels.items() if s >= threshold]
        return sorted(possibleLabels)


class FakeKeyEvent(object):
    def __init__(self, key):
        self.key = key


def isCommand(s):
    if s == 'COMMAND':
        return True
