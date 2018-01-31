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
  import smbus
  import lcddriver
  have_spi = True
except:
  import math
  have_spi = False

import os, sys, signal, signal, time, datetime
import subprocess, syslog
from argparse import ArgumentParser
from threading import Thread, Event, Lock
import json
import rrdtool

# --- configuration   --------------------------------------------------------

# please change constant ADC
# if your ADC is not in ADC_VALUES, add it and submit a pull-request

ADC = 'MCP3202'
ADC_VALUES = {
  'MCP3002': { 'CMD_BYTES': [[0,104,0],[0,120,0]], 'RESOLUTION': 10},
  'MCP3008': { 'CMD_BYTES': [[1,128,0],[1,144,0]], 'RESOLUTION': 10},
  'MCP3202': { 'CMD_BYTES': [[1,160,0],[1,224,0]], 'RESOLUTION': 12}
  }

# --- constants   ------------------------------------------------------------

# derived values, don't change
ADC_BYTES  = ADC_VALUES[ADC]['CMD_BYTES']
ADC_RES    = 2**ADC_VALUES[ADC]['RESOLUTION']
ADC_MASK   = 2**(ADC_VALUES[ADC]['RESOLUTION']-8) - 1

TIMESTAMP_FMT = "%Y-%m-%d %H:%M:%S"
INTERVAL      = 1
KEEP_SEC      = 1           # number of hours to keep seconds-data
KEEP_MIN      = 24          # number of hours to keep minute-data
KEEP_HOUR     = 1           # number of month to keep hour-data
KEEP_DAY      = 12          # number of month to keep day-data

U_MAX         = 5.6         # max voltage (technically 5.5 with some headroom)
A_MAX         = 5.0         # max current
U_REF         = 3.3
U_FAC         = 5.0/3.0     # this depends on the measurement-circuit
U_RES         = U_REF/ADC_RES

I_SCALE       = 1000        # scale A to mA


# Hall sensor
U_CC       =   5.0    # Volt
CONV_VALUE =   0.185  # V/A      converter value

# output format-templates
LINE0 = "----------------------"
LINE1 = "   I(mA)  U(V)  P(W)"
LINE2 = "{0} {1:4d}  {2:4.2f}  {3:4.2f}"
LINE3 = "max{0:5d}  {1:4.2f}  {2:4.1f}"
LINE4 = "tot {0:02d}:{1:02d}:{2:02d} {3:4.2f} Wh"

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

# --- query output options   -------------------------------------------------

def query_output_opts(options):
  """ query output options """

  if options.out_opt == "auto":
    # check terminal
    try:
      have_term = os.getpgrp() == os.tcgetpgrp(sys.stdout.fileno())
    except:
      have_term = False
    # check 44780
    try:
      options.logger.msg("[debug] checking HD44780")
      bus = smbus.SMBus(1)
      bus.read_byte(0x27)
      have_disp = True
    except:
      have_disp = False

    if have_term and have_disp:
      options.out_opt = "both"
      options.lcd = lcddriver.lcd()
    elif have_term:
      options.out_opt = "term"
    elif have_disp:
      options.out_opt = "44780"
      options.lcd = lcddriver.lcd()
    else:
      options.out_opt = "log"

# --- initialize SPI-bus   ---------------------------------------------------

def init_spi(simulate):
  """ initialize SPI bus """

  if not simulate:
    spi = spidev.SpiDev()
    spi.open(0,0)
    spi.max_speed_hz = 50000
    return spi

# --- read SPI-bus   ---------------------------------------------------------

def read_spi(channel,options):
  """ read a value from the given channel """

  if options.simulate:
    now = datetime.datetime.now().strftime("%s")
    if channel == 0:
      return (5 + 0.5*math.sin(float(now)))/(U_RES*U_FAC)
    else:
      i = 0.5 + 0.5*math.cos(float(now))
      return (U_CC/2 - i*CONV_VALUE)/U_RES
  else:
    cmd_bytes = list(ADC_BYTES[channel])       # use copy, since
    data = options.spi.xfer(cmd_bytes)         # xfer changes the data
    options.logger.msg("[debug] result xfer channel %d: %r" %
                       (channel, str([bin(x) for x in data])))
    options.logger.msg("[debug] result-bits: %r" %
                       bin(((data[1]&ADC_MASK) << 8) + data[2]))
    return ((data[1]&ADC_MASK) << 8) + data[2]

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
    "DS:I:GAUGE:%d:0:%f" % (2*INTERVAL,I_SCALE*A_MAX),      # current
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

  global secs, u_max, i_max, p_max, p_sum

  secs += 1
  u = max(0.0,u_raw*U_RES*U_FAC)
  i = max(0.0,(U_CC/2 - ui_raw*U_RES)/CONV_VALUE)*I_SCALE
  p = u*i/I_SCALE

  u_max  = max(u_max,u)
  i_max  = max(i_max,i)
  p_max  = max(p_max,p)
  p_sum += p             # N.B: unit is Ws

  return (u,i,p)

# --- convert seconds to hh:mm:ss   ------------------------------------------

def convert_secs(secs):
  """ convert seconds to a readable representation """
  m, s = divmod(secs,60)
  h, m = divmod(m,60)
  return (h,m,s)

# --- display data   ---------------------------------------------------------

def display_data(options,ts,u,i,p):
  """ display current data """

  global secs, u_max, i_max, p_max, p_sum

  if options.out_opt == "none":
    return
  elif options.out_opt == "log":
    options.logger.msg("%s: %fV, %fmA, %fW" % (ts.strftime(TIMESTAMP_FMT+".%f"),
                                             u,i,p))
    return

  (h,m,s) = convert_secs(secs)

  if options.out_opt == "term" or options.out_opt == "both":
    print("\033c")
    print(LINE0)
    print("|%s|" % LINE1)
    print("|%s|" % LINE2.format("now",int(i),u,p))
    print("|%s|" % LINE3.format(int(i_max),u_max,p_max))
    print("|%s|" % LINE4.format(h,m,s,p_sum/3600.0))
    print(LINE0)
  if options.out_opt == "44780" or options.out_opt == "both":
    options.lcd.lcd_display_string(LINE1, 1)
    options.lcd.lcd_display_string(LINE2.format("now",int(i),u,p), 2)
    options.lcd.lcd_display_string(LINE3.format(int(i_max),u_max,p_max), 3)
    options.lcd.lcd_display_string(LINE4.format(h,m,s,p_sum/3600.0),4)

# --- collect data   ---------------------------------------------------------

def collect_data(options):
  """ collect data in an endless loop """

  # glocal accumulators
  global secs, u_max, i_max, p_max, p_sum
  secs  = 0
  u_max = 0.0
  i_max = 0.0
  p_max = 0.0
  p_sum = 0.0

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
      options.logger.msg("[debug] converted data (u,i,p): %r,%r,%r" % (u,i,p))

    # show current data
    display_data(options,ts,u,i,p)

    # update database
    rrdtool.update(options.dbfile,"%s:%f:%f:%f" % (ts.strftime("%s"),u,i,p))

    # set poll_int small enough so that we hit the next interval boundry
    ms = datetime.datetime.now().microsecond
    poll_int = INTERVAL - 1 + (1000000 - ms)/1000000.0

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

# --- summarize data   -------------------------------------------------------

def sum_data(options):
  """ summarize collected data """

  # check if summary-file exists and is newer than database
  sumfile = os.path.splitext(options.dbfile)[0] + ".summary"
  if os.path.exists(sumfile) and (
    os.path.getmtime(options.dbfile) <= os.path.getmtime(sumfile)):
    # summary is current
    f = open(sumfile,"r")
    result = json.load(f)
    f.close()
    return result
  else:
    options.logger.msg("[info] creating summary-file: %s" % sumfile)

  # create summary
  try:
    first = result_data[0][0]
    last  = result_data[-1][0]
  except:
    options.logger.msg("[error] no data in database: %s" % options.dbfile)
    sys.exit(3)

  # extract avg and max values
  I_def = "DEF:I=%s:I:AVERAGE" %  options.dbfile
  I_avg = "VDEF:I_avg=I,AVERAGE"
  I_max = "VDEF:I_max=I,MAXIMUM"

  U_def = "DEF:U=%s:U:AVERAGE" %  options.dbfile
  U_avg = "VDEF:U_avg=U,AVERAGE"
  U_max = "VDEF:U_max=U,MAXIMUM"

  P_def = "DEF:P=%s:P:AVERAGE" %  options.dbfile
  P_avg = "VDEF:P_avg=P,AVERAGE"
  P_max = "VDEF:P_max=P,MAXIMUM"

  args = ["rrdtool", "graphv",options.dbfile,
          "--start", str(first),
          "--end",   str(last),
          I_def, I_avg, I_max,
          U_def, U_avg, U_max,
          P_def, P_avg, P_max,
          "PRINT:I_avg:%6.0lf",
          "PRINT:I_max:%6.0lf",
          "PRINT:U_avg:%6.2lf",
          "PRINT:U_max:%6.2lf",
          "PRINT:P_avg:%6.2lf",
          "PRINT:P_max:%6.2lf"
         ]
  info = rrdtool.graphv(options.dbfile,args[3:])
  summary = {
    "ts_start": first,
    "ts_end":   last,
    "I_avg": int(info['print[0]']),
    "I_max": int(info['print[1]']),
    "U_avg": float(info['print[2]']),
    "U_max": float(info['print[3]']),
    "P_avg": float(info['print[4]']),
    "P_max": float(info['print[5]']),
    "P_tot": round((last-first+1)*float(info['print[4]'])/3600,2)
    }

  # write results to file
  f = open(sumfile,"w")
  json.dump(summary,f,indent=2,sort_keys=True)
  f.close()

  return summary

# --- print summary   --------------------------------------------------------

def print_summary(options):
  """ print summary of collected data """

  global result_summary
  i_avg = result_summary["I_avg"]
  u_avg = result_summary["U_avg"]
  p_avg = result_summary["P_avg"]
  i_max = result_summary["I_max"]
  u_max = result_summary["U_max"]
  p_max = result_summary["P_max"]
  p_tot = result_summary["P_tot"]
  secs  = result_summary["ts_end"]-result_summary["ts_start"]+1
  (h,m,s) = convert_secs(secs)

  print(LINE0)
  print("|%s|" % LINE1)
  print("|%s|" % LINE2.format("avg",i_avg,u_avg,p_avg))
  print("|%s|" % LINE3.format(i_max,u_max,p_max))
  print("|%s|" % LINE4.format(h,m,s,p_tot))
  print(LINE0)

# --- print data   -----------------------------------------------------------

def print_data(options):
  """ print collected data """

  # print data
  for ts,(u,i,p) in result_data:
    ts = datetime.datetime.fromtimestamp(ts).strftime(TIMESTAMP_FMT)
    u = 0 if not u else u
    i = 0 if not i else i
    p = 0 if not p else p
    if I_SCALE == 1000:
      # we display mA
      format = "%s: %s=%4.2fV, %s=%4.0fmA, %s=%4.2fW"
    else:
      format = "%s: %s=%6.4fV, %s=%6.3fA, %s=%6.4fW"
    print(format % (ts, result_title[0],u, result_title[1],i, result_title[2],p))

# --- graph data   -----------------------------------------------------------

def graph_data(options):
  """ create graphical representation of data """

  # extend first and last datapoint a bit for a nice graphical rep
  first = result_data[0][0]  - 5
  last  = result_data[-1][0] + 5

  for graph_type in options.do_graph:
    imgfile = os.path.splitext(options.dbfile)[0] + "-%s.png" % graph_type
    options.logger.msg("[info] creating image-file: %s" % imgfile)

    gdef     = "DEF:%s=%s:%s:AVERAGE" %  (graph_type,options.dbfile,graph_type)
    vdef_avg = "VDEF:%savg=%s,AVERAGE" % (graph_type,graph_type)
    vdef_max = "VDEF:%smax=%s,MAXIMUM" % (graph_type,graph_type)
    vlow     = None
    vhigh    = None
    if graph_type == 'U':
      vlabel   = "U (V)"
      line     = "LINE2:%s#0000FF:%savg" % (graph_type,graph_type)
      info_avg = "GPRINT:Uavg:U Avg \t%6.2lf V"
      info_max = "GPRINT:Umax:U Max \t%6.2lf V\c"
      vlow     = "0.0"
      vhigh    = "6.0"
    elif graph_type == 'I':
      if I_SCALE == 1:
        vlabel   = "I (A)"
        info_avg = "GPRINT:Iavg:I Avg \t%6.3lf A"
        info_max = "GPRINT:Imax:I Max \t%6.3lf A\c"
      else:
        vlabel   = "I (mA)"
        info_avg = "GPRINT:Iavg:I Avg \t%6.0lf mA"
        info_max = "GPRINT:Imax:I Max \t%6.0lf mA\c"
      line     = "LINE2:%s#00FF00:%savg" % (graph_type,graph_type)
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
                "--height", "400",
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
    if not vlow is None:
      args.extend(["--lower-limit",vlow])
    if not vhigh is None:
      args.extend(["--upper-limit",vhigh])

    rrdtool.graph(imgfile,args[3:])
  
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
    metavar='directory', default=[os.path.expanduser("~")],
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
  parser.add_argument('-S', '--summary', action='store_true',
    dest='do_sum',
    help='print summary')

  parser.add_argument('-O', '--output', nargs='?',
    metavar='opt', default='auto', const="auto",
    dest='out_opt',
    help='output-mode for measurements (auto|44780|term|both|log|none)')
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
    options.dbfile = os.path.join(options.target_dir[0],fname)
  options.logger.msg("[info] Database-file: %s" % options.dbfile)

  # set run-mode as default
  if not options.do_graph and not options.do_print and not options.do_sum:
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

# --- main program   ---------------------------------------------------------

if __name__ == '__main__':
  # parse commandline-arguments
  opt_parser = get_parser()
  options    = opt_parser.parse_args(namespace=Options)
  check_options(options)

  # query output options
  query_output_opts(options)

  # initialize database
  if not options.do_notcreate:
    create_db(options)

  # collect data
  if options.do_run:
    options.logger.msg("[debug] ADC: %s" % ADC)
    options.logger.msg("[debug] ADC resolution: %s" % ADC_RES)
    options.logger.msg("[debug] ADC command-bytes: %r" % ADC_BYTES)
    options.logger.msg("[debug] ADC mask: %r" % bin(ADC_MASK))
    get_data(options)

  # we always create a summary if it does not yet exist
  result_title,result_data = fetch_data(options)
  result_summary           = sum_data(options)

  # create output
  if options.do_print:
    print_data(options)
  if options.do_sum:
    print_summary(options)
  if options.do_graph:
    graph_data(options)

  sys.exit(0)
