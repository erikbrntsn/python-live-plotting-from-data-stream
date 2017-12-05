#!/usr/bin/env python3
import argparse
from plot_lib import Plotter

parent_parser = argparse.ArgumentParser(description="Tool for continuously plotting data", add_help=False)
parent_parser.add_argument("-n", "--n_points", type=int, default=1000, help="Number of packages of each type to plot (x-axis width)")
parent_parser.add_argument("-l", "--labels", type=str, default=[], help="List of package labels to plot")

parser = argparse.ArgumentParser(add_help=False)
subparsers = parser.add_subparsers(dest="subparser")
# Workaround for sub_parser bug
# http://stackoverflow.com/q/23349349
subparsers.required = True

socket_parser = subparsers.add_parser('socket', parents=[parent_parser], help="Use socket connection for acquiring data for the plot")
socket_parser.add_argument("host", type=str, help="Address of remote")
socket_parser.add_argument("port", type=int, help="Port on remote")

socket_parser = subparsers.add_parser('serial', parents=[parent_parser], help="Use serial connection for acquiring data for the plot")
socket_parser.add_argument("serial_port", help="Path/to/device")
socket_parser.add_argument("baudrate", help="Device baudrate")

socket_parser = subparsers.add_parser('pipe', parents=[parent_parser], help="Use pipe connection for acquiring data for the plot")

args = parser.parse_args()


def startSocketPlotter(args):
  import socket_reader
  reader = socket_reader.Reader(host=args.host, port=args.port)
  return Plotter(reader=reader, ringLength=args.n_points, labels=[])


def startSerialPlotter(args):
  import serial_reader
  reader = serial_reader.Reader(port=args.serial_port, baudrate=args.baudrate)
  return Plotter(reader=reader, ringLength=args.n_points, labels=[])


def startPipePlotter(args):
  import pipe_reader
  reader = pipe_reader.Reader()
  return Plotter(reader=reader, ringLength=args.n_points, labels=[])


# Start plotter with data over socket connection
if args.subparser == "socket":
  plotter = startSocketPlotter(args)

# Start plotter with data over serial connection
elif args.subparser == "serial":
  plotter = startSerialPlotter(args)

# Start plotter with data through pipe
elif args.subparser == "pipe":
  plotter = startPipePlotter(args)

while True:
  plotter.update()
