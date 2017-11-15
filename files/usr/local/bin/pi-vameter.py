#!/usr/bin/python
# ----------------------------------------------------------------------------
# Measure voltage and curent using a Hall-sensor and an ADC.
#
# Author: Bernhard Bablok, Lothar Hiller
# License: GPL3
#
# Website: https://github.com/bablokb/pi-vameter
#
# ----------------------------------------------------------------------------

try:
  import spidev
  have_spi = True
except:
  import math
  have_spi = False
  pass

import os, sys, signal, signal, time, datetime
import subprocess
from argparse import ArgumentParser
from threading import Thread, Event, Lock

import rrdtool

# --- constants   ------------------------------------------------------------

TIMESTAMP_FMT = "%Y-%m-%d %H:%M:%S"
INTERVAL      = 1
KEEP_SEC      = 1           # number of hours to keep seconds-data
KEEP_MIN      = 24          # number of hours to keep minute-data
KEEP_HOUR     = 1           # number of month to keep hour-data
KEEP_DAY      = 12          # number of month to keep day-data

U_MAX         = 12.0        # max voltage
A_MAX         = 5.0         # max current
U_REF         = 3.3
U_FAC         = 5.0/3.0     # this depends on the measurement-circuit
U_RES         = U_REF/1024  # MCP3008 has 10-bit resolution

I_SCALE       = 1000        # scale A to mA

#ADC_BYTES     = [[1,128,0],[0,144,0]]    # MCP3008
ADC_BYTES     = [[0,104,0],[0,120,0]]    # MCP3002
#ADC_BYTES     = [[0,160,0],[0,224,0]]    # MCP3202

# Hall sensor
U_CC       =   5.0    # Volt
CONV_VALUE =   0.185  # V/A      converter value

# --- helper class for options   --------------------------------------------

class Options(object):
  pass

# --- helper class for logging to syslog/stderr   ----------------------------

class Msg(object):
  """ Very basic message writer class """

  # --- constructor   --------------------------------------------------------

  def __init__(self,debug):
    """ Constructor """
    self._debug = debug
    self._lock = Lock()
    try:
      if os.getpgrp() == os.tcgetpgrp(sys.stdout.fileno()):
        self._syslog = False
        self._debug  = True
      else:
        self._syslog = True
    except:
      self._syslog = True

    if self._syslog:
      syslog.openlog("pi-vameter")

  def msg(self,text):
    """ write message to the system log """ 
    if self._debug:
      with self._lock:
        if self._syslog:
          syslog.syslog(text)
        else:
          sys.stderr.write(text)
          sys.stderr.write("\n")
          sys.stderr.flush()

# ----------------------------------------------------------------------------
# ----------------------------------------------------------------------------

# --- initialize SPI-bus   ---------------------------------------------------

def init_spi(simulate):
  """ initialize SPI bus """

  if not simulate:
    spi = spidev.SpiDev()
    spi.open(0,0)
    return spi

# --- read SPI-bus   ---------------------------------------------------------

def read_spi(channel,options):
  """ read a value from the given channel """

  if options.simulate:
    now = datetime.datetime.now().strftime("%s")
    if channel == 0:
      return 1 + math.sin(float(now))
    else:
      return (1 + math.cos(float(now)))/1000.0
  else:
    data = options.spi.xfer(ADC_BYTES[channel])
    return ((data[1]&3) << 8) + data[2]

# --- create database   ------------------------------------------------------

def create_db(options):
  """ create RRD database """

  # create database with averages, minimums and maximums
  options.logger.msg("[info] creating %s" % options.dbfile)
  rrdtool.create(
    options.dbfile,
    "--start", "now",
    "--step", str(INTERVAL),
    "DS:U:GAUGE:%d:0:%f" % (2*INTERVAL,U_MAX),              # voltage
    "DS:I:GAUGE:%d:0:%f" % (2*INTERVAL,A_MAX),              # current
    "DS:P:GAUGE:%d:0:%f" % (2*INTERVAL,U_MAX*A_MAX),        # power

    "RRA:AVERAGE:0.5:1s:%dh" % KEEP_SEC,
    "RRA:AVERAGE:0.5:1m:%dh" % KEEP_MIN,
    "RRA:AVERAGE:0.5:1h:%dM" % KEEP_HOUR,
    "RRA:AVERAGE:0.5:1d:%dM" % KEEP_DAY,

    "RRA:MIN:0.5:1s:%dh" % KEEP_SEC,
    "RRA:MIN:0.5:1m:%dh" % KEEP_MIN,
    "RRA:MIN:0.5:1h:%dM" % KEEP_HOUR,
    "RRA:MIN:0.5:1d:%dM" % KEEP_DAY,

    "RRA:MAX:0.5:1s:%dh" % KEEP_SEC,
    "RRA:MAX:0.5:1m:%dh" % KEEP_MIN,
    "RRA:MAX:0.5:1h:%dM" % KEEP_HOUR,
    "RRA:MAX:0.5:1d:%dM" % KEEP_DAY
    )

  return

# --- convert data   ---------------------------------------------------------

def convert_data(u_raw,ui_raw):
  """ convert (scale) data """

  u = max(0.0,u_raw*U_RES*U_FAC)
  i = max(0.0,(U_CC/2 - ui_raw*U_RES)/CONV_VALUE)
  return (u,i,u*i)

# --- display data   ---------------------------------------------------------

def display_data(options,ts,u,i,p):
  """ display current data """

  options.logger.msg("%s: %fV, %fmA, %fW" % (ts.strftime(TIMESTAMP_FMT+".%f"),
                                             u,I_SCALE*i,p))

# --- collect data   ---------------------------------------------------------

def collect_data(options):
  """ collect data in an endless loop """

  # start at (near) full second
  ms       = datetime.datetime.now().microsecond
  poll_int = (1000000 - ms)/1000000.0
  while True:
    if options.stop_event.wait(poll_int):
      break

    # read values of voltage and current from ADC
    ts = datetime.datetime.now()
    u_raw  = read_spi(0,options)
    ui_raw = read_spi(1,options)
    if options.raw:
      (u,i,p) = (u_raw,ui_raw,u_raw*ui_raw)
    else:
      (u,i,p) = convert_data(u_raw,ui_raw)

    # show current data
    display_data(options,ts,u,i,p)

    # update database
    rrdtool.update(options.dbfile,"%s:%f:%f:%f" % (ts.strftime("%s"),u,i,p))

    # set poll_int small enough so that we hit the next interval boundry
    ms = datetime.datetime.now().microsecond
    poll_int = INTERVAL - 1 + (1000000 - ms)/1000000.0

# --- signal-handler   -----------------------------------------------------

def signal_handler(_signo, _stack_frame):
  """ Signal-handler to cleanup threads """

  global data_thread, options
  options.logger.msg("interrupt %d detected, exiting" % _signo)
  return

# --- cmdline-parser   ------------------------------------------------------

def get_parser():
  """ configure cmdline-parser """

  parser = ArgumentParser(add_help=False,
    description='Pi VA-meter')

  parser.add_argument('-D', '--dir', nargs=1,
    metavar='directory', default=os.path.expanduser("~"),
    dest='target_dir',
    help='directory for RRDs and graphics if no database-name is supplied')
  parser.add_argument('-n', '--no-create', action='store_true',
    dest='do_notcreate', default=False,
    help="don't recreate the database")
  parser.add_argument('-r', '--run', action='store_true',
    dest='do_run',
    help='start measurement (default)')
  parser.add_argument('-g', '--graph', nargs='?',
    metavar='graph_opt', default=None, const="UIP",
    dest='do_graph',
    help='create graphic from data for U,I,P (use any combination)')
  parser.add_argument('-p', '--print', action='store_true',
    dest='do_print',
    help='print results')

  parser.add_argument('-R', '--raw', action='store_true',
    dest='raw', default=False,
    help='record raw ADC-values')

  parser.add_argument('-d', '--debug', metavar='debug-mode',
    dest='debug', default=False,
    help='start in debug-mode')
  parser.add_argument('-s', '--simulate', metavar='simulate',
    dest='simulate', default=False,
    help='simulate reads from ADC')
  parser.add_argument('-h', '--help', action='help',
    help='print this help')

  parser.add_argument('dbfile', nargs='?', metavar='database-file',
    default=None, help='RRD database-file')
  return parser

# --- validate and fix options   ---------------------------------------------

def check_options(options):
  """ validate and fix options """

  # add logger
  options.logger   = Msg(options.debug)

  # default database
  if not options.dbfile:
    now            = datetime.datetime.now()
    fname          = now.strftime("%Y%m%d_%H%M%S.rrd")
    options.dbfile = os.path.join(options.target_dir,fname)
  options.logger.msg("[info] Database-file: %s" % options.dbfile)

  # set run-mode as default
  if not options.do_graph and not options.do_print:
    options.do_run = True

  # do not recreate the database if no new run is requested
  if os.path.exists(options.dbfile) and not options.do_run:
    options.do_notcreate = True

  # check if we need to create the database
  if not os.path.exists(options.dbfile) and options.do_notcreate:
      options.logger.msg("[error] database does not exist")
      sys.exit(3)
  if not os.path.exists(options.dbfile) and not options.do_run:
      options.logger.msg("[error] database does not exist")
      sys.exit(3)

  # without real hardware we just simulate
  options.simulate = options.simulate or not have_spi
  options.logger.msg("[info] simulation-mode: %r" % options.simulate)

# --- collect data   ---------------------------------------------------------

def get_data(options):
  """ run collector-thread """

  # setup signal handlers
  signal.signal(signal.SIGTERM,signal_handler)
  signal.signal(signal.SIGINT,signal_handler)

  # create and start collector-thread
  options.stop_event  = Event()
  options.spi = init_spi(options.simulate)
  data_thread = Thread(target=collect_data,args=(options,))
  options.logger.msg("[info] starting data-collection")
  data_thread.start()

  # wait for signal
  signal.pause()

  # stop data-collection
  options.logger.msg("[info] terminating data-collection")
  options.stop_event.set()
  data_thread.join()

# --- fetch data   -----------------------------------------------------------

def fetch_data(options):
  """ fetch data and delete NaNs """

  first = rrdtool.first(options.dbfile)
  last  = rrdtool.last(options.dbfile)

  time_span, titles, values = rrdtool.fetch(options.dbfile,"AVERAGE",
                                            "--start", str(first),
                                            "--end", str(last),
                                            "--resolution", "1")
  # extract valid values
  ts_start, ts_end, ts_res = time_span
  times = range(ts_start, ts_end, ts_res)
  result = zip(times, values)
  return titles, [v for v in result if v[1] != (None,None,None)]

# --- print data   -----------------------------------------------------------

def print_data(options):
  """ print collected data """
  title, result = fetch_data(options)

  # print data
  for ts,(u,i,p) in result:
    ts = datetime.datetime.fromtimestamp(ts).strftime(TIMESTAMP_FMT)
    u = 0 if not u else u
    i = 0 if not i else i
    p = 0 if not p else p
    if I_SCALE == 1000:
      # we display mA
      format = "%s: %s=%6.4fV, %s=%6.0fmA, %s=%6.4fW"
    else:
      format = "%s: %s=%6.4fV, %s=%6.3fA, %s=%6.4fW"
    print(format % (ts, title[0],u, title[1],I_SCALE*i, title[2],p))

# --- graph data   -----------------------------------------------------------

def graph_data(options):
  """ create graphical representation of data """

  # fetch data (to find first true data-point)
  _, data = fetch_data(options)
  first = data[0][0]  - 5
  last  = data[-1][0] + 5

  for graph_type in options.do_graph:
    imgfile = os.path.splitext(options.dbfile)[0] + "-%s.png" % graph_type
    options.logger.msg("[info] creating image-file: %s" % imgfile)

    gdef     = "DEF:%s=%s:%s:AVERAGE" %  (graph_type,options.dbfile,graph_type)
    vdef_avg = "VDEF:%savg=%s,AVERAGE" % (graph_type,graph_type)
    vdef_max = "VDEF:%smax=%s,MAXIMUM" % (graph_type,graph_type)
    if graph_type == 'U':
      vlabel   = "U (V)"
      line     = "LINE2:%s#0000FF:%savg" % (graph_type,graph_type)
      info_avg = "GPRINT:Uavg:U Avg \t%6.2lf V"
      info_max = "GPRINT:Umax:U Max \t%6.2lf V\c"
    elif graph_type == 'I':
      vlabel   = "I (A)"
      line     = "LINE2:%s#00FF00:%savg" % (graph_type,graph_type)
      info_avg = "GPRINT:Iavg:I Avg \t%6.3lf A"
      info_max = "GPRINT:Imax:I Max \t%6.3lf A\c"
    else:
      vlabel   = "P (W)"
      line     = "LINE2:%s#FF0000:%savg" % (graph_type,graph_type)
      info_avg = "GPRINT:Pavg:P Avg \t%6.2lf W"
      info_max = "GPRINT:Pmax:P Max \t%6.2lf W\c"

    args = ["rrdtool", "graph", imgfile,
                "--start", str(first),
                "--end",   str(last),
                "--vertical-label=%s" % vlabel,
                "--width", "800",
                "--height", "600",
                "--title", "Pi-VA-Meter",
                "--left-axis-format", "%6.2lf",
                "--units-exponent", "0",
                gdef,
                vdef_avg,
                vdef_max,
                line,
                "COMMENT:\s",
                info_avg,
                info_max]

    rrdtool.graph(imgfile,args[3:])
  
# --- main program   ---------------------------------------------------------

if __name__ == '__main__':
  # parse commandline-arguments
  opt_parser = get_parser()
  options    = opt_parser.parse_args(namespace=Options)
  check_options(options)

  # initialize database
  if not options.do_notcreate:
    create_db(options)

  # collect data
  if options.do_run:
    get_data(options)

  # create output
  if options.do_print:
    print_data(options)
  if options.do_graph:
    graph_data(options)

  sys.exit(0)
