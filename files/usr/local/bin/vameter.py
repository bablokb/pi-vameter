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

import os, sys, signal, signal, time, datetime, traceback
import subprocess, syslog
from argparse import ArgumentParser
from threading import Thread, Event, Lock
import json, rrdtool, statistics, ConfigParser

# --- read configuration-value   ---------------------------------------------

def get_config(parser,section,option,default):
  """ read a single configuration value """
  if parser.has_section(section):
    try:
      value = parser.get(section,option)
    except:
      value = default
  else:
    value = default
  return value

# --- read configuration   ---------------------------------------------------

def get_configuration():
  """ read complete configuration """

  global ADC, U_CC_2, CONV_VALUE

  parser = ConfigParser.RawConfigParser()
  parser.read('/etc/vameter.conf')

  ADC        = get_config(parser,'ADC','ADC','MCP3202')
  U_CC_2     = float(get_config(parser,'HALL','U_CC_2','2.5'))
  CONV_VALUE = float(get_config(parser,'HALL','CONV_VALUE','0.185'))

# --- constants   ------------------------------------------------------------

get_configuration()

# if your ADC is not in ADC_VALUES, add it and submit a pull-request

ADC_VALUES = {
  'MCP3002': { 'CMD_BYTES': [[0,104,0],[0,120,0]], 'RESOLUTION': 10},
  'MCP3008': { 'CMD_BYTES': [[1,128,0],[1,144,0]], 'RESOLUTION': 10},
  'MCP3202': { 'CMD_BYTES': [[1,160,0],[1,224,0]], 'RESOLUTION': 12}
  }

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

# output format-templates
LINE0  = "----------------------"

LINE1  = "   I(mA)  U(V)  P(W)"
LINE2  = "{0} {1:4d}  {2:4.2f}  {3:4.2f}"
LINE3  = "max{0:5d}  {1:4.2f}  {2:4.1f}"
LINE4  = "tot {0:02d}:{1:02d}:{2:02d} {3:5.2f}Wh"

LINE1V = "     UI(V)     U(V) "
LINE2V = "{0} {1:6.4f}   {2:6.4f} "
LINE3V = "max {0:6.4f}   {1:6.4f} "
LINE4V = "tot {0:02d}:{1:02d}:{2:02d}        "

# --- helper class for options   --------------------------------------------

class Options(object):
  pass

# --- helper class for logging to syslog/stderr   ----------------------------

class Msg(object):
  """ Very basic message writer class """

  MSG_LEVELS={
    "TRACE":0,
    "DEBUG":1,
    "INFO":2,
    "WARN":3,
    "ERROR":4,
    "NONE":5
    }

  # --- constructor   --------------------------------------------------------

  def __init__(self,level,sysl):
    """ Constructor """
    self._level = level
    self._syslog = sysl
    self._lock = Lock()

    if self._syslog:
      syslog.openlog("pi-vameter")

  def msg(self,msg_level,text,nl=True):
    """ write message to stderr or the system log """
    if Msg.MSG_LEVELS[msg_level] >= Msg.MSG_LEVELS[self._level]:
      now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
      text = "[%s] [%s] %s" % (msg_level,now,text)
      if nl and not self._syslog:
        text = text + "\n"
      try:
        with self._lock:
          if self._syslog:
            syslog.syslog(text)
          else:
            sys.stderr.write(text)
            sys.stderr.flush()
      except:
        pass

# ----------------------------------------------------------------------------
# ----------------------------------------------------------------------------

# --- query output options   -------------------------------------------------

def query_output_opts(options):
  """ query output options """

  # check terminal
  if options.out_opt == "auto" or options.out_opt == "term":
    try:
      have_term = os.getpgrp() == os.tcgetpgrp(sys.stdout.fileno())
    except:
      have_term = False
    if not have_term:
      options.out_opt = 'plain'
      options.logger.msg("INFO","switching to 'plain' output")
    else:
      options.out_opt = 'term'

  # check 44780
  try:
    options.logger.msg("DEBUG", "checking HD44780")
    bus = smbus.SMBus(1)
    bus.read_byte(0x27)
    options.have_disp = True
    options.lcd = lcddriver.lcd()
  except:
    options.have_disp = False

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
      return int((5 + 0.5*math.sin(float(now)))/(U_RES*U_FAC))
    else:
      i = 0.5 + 0.5*math.cos(float(now))
      return int((U_CC_2 - i*CONV_VALUE)/U_RES)
  else:
    cmd_bytes = list(ADC_BYTES[channel])       # use copy, since
    data = options.spi.xfer(cmd_bytes)         # xfer changes the data
    options.logger.msg("TRACE", "result xfer channel %d: %r" %
                       (channel, str([bin(x) for x in data])))
    options.logger.msg("TRACE", "result-bits: %r" %
                       bin(((data[1]&ADC_MASK) << 8) + data[2]))
    return ((data[1]&ADC_MASK) << 8) + data[2]

# --- create database   ------------------------------------------------------

def create_db(options):
  """ create RRD database """

  # create database with averages, minimums and maximums
  options.logger.msg("INFO", "creating %s" % options.dbfile)
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

def convert_data(u_raw,ui_raw,voltage=False):
  """ convert (scale) data """

  global secs, u_max, i_max, p_max, p_sum

  secs += 1
  u = u_raw*U_RES*U_FAC
  if voltage:
    i = ui_raw*U_RES
    p = 0.0                 # not relevant
  else:
    i = max(0.0,(U_CC_2 - ui_raw*U_RES)/CONV_VALUE)*I_SCALE
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

  (h,m,s) = convert_secs(secs)

  # always try to write to the display
  try:
    if options.have_disp:
      if options.voltage:
        options.lcd.lcd_display_string(LINE1V, 1)
        options.lcd.lcd_display_string(LINE2V.format("now",i,u), 2)
        options.lcd.lcd_display_string(LINE3V.format(i_max,u_max), 3)
        options.lcd.lcd_display_string(LINE4V.format(h,m,s),4)
      else:
        options.lcd.lcd_display_string(LINE1, 1)
        options.lcd.lcd_display_string(LINE2.format("now",int(i),u,p), 2)
        options.lcd.lcd_display_string(LINE3.format(int(i_max),u_max,p_max), 3)
        options.lcd.lcd_display_string(LINE4.format(h,m,s,p_sum/3600.0),4)
  except:
    #traceback.format_exc()
    pass

  # check other output-options (silently ignore 'none')
  try:
    if options.out_opt == "term":
      print("\033c")
      print(LINE0)
      if options.voltage:
        print("|%s|" % LINE1V)
        print("|%s|" % LINE2V.format("now",i,u))
        print("|%s|" % LINE3V.format(i_max,u_max))
        print("|%s|" % LINE4V.format(h,m,s))
      else:
        print("|%s|" % LINE1)
        print("|%s|" % LINE2.format("now",int(i),u,p))
        print("|%s|" % LINE3.format(int(i_max),u_max,p_max))
        print("|%s|" % LINE4.format(h,m,s,p_sum/3600.0))
      print(LINE0)

    elif options.out_opt == "log":
      options.logger.msg("INFO", "%s: %fV, %fmA, %fW" %
                         (ts.strftime(TIMESTAMP_FMT+".%f"),u,i,p))

    elif options.out_opt == "plain":
      if options.raw:
        sys.stderr.write("%s: U: %8.2f, I: %8.2f\n" %
                       (ts.strftime(TIMESTAMP_FMT+".%f"),u,i))
      elif options.voltage:
        sys.stderr.write("%s: U: %6.4fV, I: %6.4fV\n" %
                       (ts.strftime(TIMESTAMP_FMT+".%f"),u,i))
      else:
        sys.stderr.write("%s: %4.2fV, %6.1fmA, %5.2fW\n" %
                       (ts.strftime(TIMESTAMP_FMT+".%f"),u,i,p))
      sys.stderr.flush()

    elif options.out_opt == "json":
      sys.stdout.write(
          '{"ts": "%s", "U": "%.2f", "I": "%.1f", "P": "%.2f", ' %
                         (ts.strftime("%s"),u,i,p) +
                       '"U_max": "%.2f", "I_max": "%.1f", "P_max": "%.2f",' %
                         (u_max,i_max,p_max) +
                       ' "s_tot": "%02d:%02d:%02d", "P_tot": "%.2f"}\n' %
                         (h,m,s,p_sum/3600.0 ))
      sys.stdout.flush()
  except:
    #traceback.format_exc()
    pass

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

  # sample accumulators
  u_samp = []
  ui_samp = []

  # start at (near) full second
  ms       = datetime.datetime.now().microsecond
  poll_int = (1000000 - ms)/1000000.0
  while True:
    if options.stop_event.wait(poll_int):
      break

    # read timestamp and values of voltage and current from ADC
    ts      = datetime.datetime.now()
    ts_save = ts + (
              datetime.timedelta(seconds=INTERVAL,milliseconds=-10))

    # read and save raw values
    while ts < ts_save:
      u_samp.append(read_spi(0,options))
      ui_samp.append(read_spi(1,options))
      time.sleep(0.01)
      ts = datetime.datetime.now()
    u_samp.append(read_spi(0,options))
    ui_samp.append(read_spi(1,options))

    # save values
    options.logger.msg("DEBUG", "sample-size: %d" % len(u_samp))
    save_and_display(options,ts,u_samp,ui_samp)

    # reset accumulators
    u_samp  = []
    ui_samp = []

    # set poll_int small enough so that we hit the next interval boundry
    ms = datetime.datetime.now().microsecond
    poll_int = (INTERVAL - 1 + (1000000 - ms)/1000000.0)/100.0

# --- save and display data   ------------------------------------------------

def save_and_display(options,ts,u_samp,ui_samp):
  """ save and display data """

  options.logger.msg("TRACE", "sample u_raw: %r" % (u_samp,))
  options.logger.msg("TRACE", "sample ui_raw: %r" % (ui_samp,))

  # calculate values and log statistics
  u_raw   = statistics.mean(u_samp)
  ui_raw  = statistics.mean(ui_samp)
  options.logger.msg("DEBUG", "u_raw   mean: %8.2f" % u_raw)
  options.logger.msg("DEBUG", "i_raw   mean: %8.2f" % ui_raw)

  # since calculation of statistics is expensive, check level
  if options.level == "TRACE":
    options.logger.msg("TRACE", "u_raw median: %5d" %
                              statistics.median(u_samp))
    options.logger.msg("TRACE", "i_raw median: %5d" %
                              statistics.median(ui_samp))
    options.logger.msg("TRACE", "u_raw  sigma: %8.2f" %
                              statistics.stdev(u_samp,u_raw))
    options.logger.msg("TRACE", "i_raw  sigma: %8.2f" %
                              statistics.stdev(ui_samp,ui_raw))

  # convert values
  if options.raw:
    (U,I,P) = (u_raw,ui_raw,0)
  elif options.voltage:
    (U,I,P) = convert_data(u_raw,ui_raw,voltage=True)
    options.logger.msg("TRACE", "voltage data (U,I): %4.2f,%4.2f" % (U,I))
  else:
    (U,I,P) = convert_data(u_raw,ui_raw)
    options.logger.msg("TRACE", "converted data (U,I,P): %4.2f,%6.1f,%5.2f" % (U,I,P))

  # show current data
  display_data(options,ts,U,I,P)

  # update database
  if I >= options.limit:
    if options.limit > 0:
      options.limit = 0  # once above the limit, record everything
    if not options.raw:
      rrdtool.update(options.dbfile,"%s:%f:%f:%f" % (ts.strftime("%s"),U,I,P))

    # save start timestamp, since rrdtool does not record it
    if options.ts_start == 0:
      options.logger.msg("INFO", "starting to update DB")
      options.ts_start = int(ts.strftime("%s"))

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
  options.logger.msg("INFO", "starting data-collection")
  data_thread.start()

  # wait for signal
  signal.pause()

  # stop data-collection
  options.logger.msg("INFO", "terminating data-collection")
  options.stop_event.set()
  data_thread.join()

# --- fetch data   -----------------------------------------------------------

def fetch_data(options):
  """ fetch data and delete NaNs """

  first = options.summary["ts_start"]
  last  = options.summary["ts_end"]

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
    options.logger.msg("INFO", "creating summary-file: %s" % sumfile)

  # create summary
  try:
    if options.ts_start > 0:
      first = options.ts_start
    else:
      # this should not happen, unless somebody deleted to summary file
      first = rrdtool.first(options.dbfile)
    last  = rrdtool.last(options.dbfile)
  except Exception as e:
    options.logger.msg("TRACE", traceback.format_exc())
    options.logger.msg("ERROR", "no data in database: %s" % options.dbfile)
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
          "PRINT:I_avg:%8.4lf",
          "PRINT:I_max:%8.4lf",
          "PRINT:U_avg:%8.4lf",
          "PRINT:U_max:%8.4lf",
          "PRINT:P_avg:%6.2lf",
          "PRINT:P_max:%6.2lf"
         ]
  info = rrdtool.graphv(options.dbfile,args[3:])
  summary = {
    "ts_start": first,
    "ts_end":   last,
    "U_avg": float(info['print[2]']),
    "U_max": float(info['print[3]']),
    "P_avg": float(info['print[4]']),
    "P_max": float(info['print[5]']),
    "P_tot": round((last-first+1)*float(info['print[4]'])/3600,2)
    }
  if options.voltage:
    summary["I_avg"] = float(info['print[0]'])
    summary["I_max"] = float(info['print[1]'])
  else:
    summary["I_avg"] = int(float(info['print[0]']))
    summary["I_max"] = int(float(info['print[1]']))

  # write results to file
  f = open(sumfile,"w")
  json.dump(summary,f,indent=2,sort_keys=True)
  f.close()

  return summary

# --- print summary   --------------------------------------------------------

def print_summary(options):
  """ print summary of collected data """

  i_avg = options.summary["I_avg"]
  u_avg = options.summary["U_avg"]
  p_avg = options.summary["P_avg"]
  i_max = options.summary["I_max"]
  u_max = options.summary["U_max"]
  p_max = options.summary["P_max"]
  p_tot = options.summary["P_tot"]
  secs  = options.summary["ts_end"]-options.summary["ts_start"]+1
  (h,m,s) = convert_secs(secs)

  try:
    if options.have_disp:
      if options.voltage:
        options.lcd.lcd_display_string(LINE1V, 1)
        options.lcd.lcd_display_string(LINE2V.format("avg",i_avg,u_avg,p_avg), 2)
        options.lcd.lcd_display_string(LINE3V.format(i_max,u_max,p_max), 3)
        options.lcd.lcd_display_string(LINE4V.format(h,m,s),4)
      else:
        options.lcd.lcd_display_string(LINE1, 1)
        options.lcd.lcd_display_string(LINE2.format("avg",i_avg,u_avg,p_avg), 2)
        options.lcd.lcd_display_string(LINE3.format(i_max,u_max,p_max), 3)
        options.lcd.lcd_display_string(LINE4.format(h,m,s,p_tot),4)
  except:
    #traceback.format_exc()
    pass

  try:
    if options.out_opt in ["term", "both", "plain"]:
      print(LINE0)
      if options.voltage:
        print("|%s|" % LINE1V)
        print("|%s|" % LINE2V.format("avg",i_avg,u_avg,p_avg))
        print("|%s|" % LINE3V.format(i_max,u_max,p_max))
        print("|%s|" % LINE4V.format(h,m,s))
      else:
        print("|%s|" % LINE1)
        print("|%s|" % LINE2.format("avg",i_avg,u_avg,p_avg))
        print("|%s|" % LINE3.format(i_max,u_max,p_max))
        print("|%s|" % LINE4.format(h,m,s,p_tot))
      print(LINE0)
    elif options.out_opt == "json":
      sys.stdout.write(
        '{"U_avg": "%.2f", "I_avg": "%.1f", "P_avg": "%.2f", ' %
                       (u_avg,i_avg,p_avg) +
                     '"U_max": "%.2f", "I_max": "%.1f", "P_max": "%.2f"}' %
                       (u_max,i_max,p_max) +
                     '"tot": "%02d:%02d:%02d", "P_tot": "%.2f"}\n' %
                       (h,m,s,p_tot))
      sys.stdout.flush()
  except:
    #traceback.format_exc()
    pass

# --- print data   -----------------------------------------------------------

def print_data(options):
  """ print collected data """

  result_title,result_data = fetch_data(options)

  for ts,(u,i,p) in result_data:
    ts = datetime.datetime.fromtimestamp(ts).strftime(TIMESTAMP_FMT)
    u = 0 if not u else u
    i = 0 if not i else i
    p = 0 if not p else p
    try:
      if options.voltage:
        print("%s: U=%6.4fV, UI=%6.4fV" % (ts,u,i))
      else:
        print("%s: %s=%4.2fV, %s=%4.0fmA, %s=%4.2fW" %
              (ts, result_title[0],u, result_title[1],i, result_title[2],p))
    except:
      #traceback.format_exc()
      pass

# --- graph data   -----------------------------------------------------------

def graph_data(options):
  """ create graphical representation of data """

  # extend first and last datapoint a bit for a nice graphical rep
  first = options.summary["ts_start"]  - 5
  last  = options.summary["ts_end"]    + 5

  # query filename without path and extension for title
  title = os.path.splitext(os.path.basename(options.dbfile))[0]
  for graph_type in options.do_graph:
    imgfile = os.path.splitext(options.dbfile)[0] + "-%s.png" % graph_type
    options.logger.msg("INFO", "creating image-file: %s" % imgfile)

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
                "--title", title,
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
  options.logger.msg("DEBUG", "interrupt %d detected, exiting" % _signo)
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
    choices=["auto","44780","term","both","plain","json","log","none"],
    help="""output-mode for measurements: one of
            auto, 44780, term, both, plain, json, log, none)""")

  parser.add_argument('-R', '--raw', action='store_true',
    dest='raw', default=False,
    help='record raw ADC-values')
  parser.add_argument('-V', '--voltage', action='store_true',
    dest='voltage', default=False,
    help='record voltage values from ADC')
  parser.add_argument('-T', '--trigger', nargs=1,
    metavar='limit', default=[0.0],
    dest='limit', type=float,
    help='start recording data as soon as current is larger than limit')

  parser.add_argument('-l', '--level', dest='level', default='INFO',
                      metavar='debug-level',
                      choices=['NONE','ERROR','WARN','INFO','DEBUG','TRACE'],
    help='debug level: one of NONE, ERROR, WARN, INFO, DEBUG, TRACE')
  parser.add_argument('-y', '--syslog', action='store_true',
    dest='syslog',
    help='log to syslog')

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
  options.logger   = Msg(options.level,options.syslog)

  # default database
  if not options.dbfile:
    now            = datetime.datetime.now()
    fname          = now.strftime("%Y%m%d_%H%M%S.rrd")
    options.dbfile = os.path.join(options.target_dir[0],fname)
  options.logger.msg("INFO", "Database-file: %s" % options.dbfile)

  # set run-mode as default
  if not options.do_graph and not options.do_print and not options.do_sum:
    options.do_run = True

  # do not recreate the database if no new run is requested
  if os.path.exists(options.dbfile) and not options.do_run:
    options.do_notcreate = True

  # check if we need to create the database
  if not os.path.exists(options.dbfile) and options.do_notcreate:
      options.logger.msg("ERROR", "database does not exist")
      sys.exit(3)
  if not os.path.exists(options.dbfile) and not options.do_run:
      options.logger.msg("ERROR", "database does not exist")
      sys.exit(3)

  options.limit    = options.limit[0]
  options.logger.msg("DEBUG", "limit: %f" % options.limit)
  options.ts_start = 0

  # without real hardware we just simulate
  options.simulate = options.simulate or not have_spi
  options.logger.msg("INFO", "simulation-mode: %r" % options.simulate)

# --- main program   ---------------------------------------------------------

if __name__ == '__main__':

  # parse commandline-arguments
  opt_parser     = get_parser()
  options        = opt_parser.parse_args(namespace=Options)
  check_options(options)

  # query output options
  query_output_opts(options)

  # initialize database
  if not options.do_notcreate:
    create_db(options)

  # collect data
  if options.do_run:
    options.logger.msg("DEBUG", "ADC: %s" % ADC)
    options.logger.msg("DEBUG", "ADC resolution: %s" % ADC_RES)
    options.logger.msg("DEBUG", "ADC command-bytes: %r" % ADC_BYTES)
    options.logger.msg("DEBUG", "ADC mask: %r" % bin(ADC_MASK))
    options.logger.msg("DEBUG", "HALL U_CC_2:     %4.2f" % U_CC_2)
    options.logger.msg("DEBUG", "HALL conv-value: %5.3f" % CONV_VALUE)
    get_data(options)

  # we always create a summary if it does not yet exist
  if not options.raw:
    options.summary = sum_data(options)

  # create output
  if not options.raw:
    if options.do_print:
      print_data(options)
    if options.do_sum:
      print_summary(options)
    if options.do_graph:
      graph_data(options)

  sys.exit(0)
