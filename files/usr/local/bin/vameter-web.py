#!/usr/bin/python
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Simple web-interface for the results of pi-vameter.py 
#
# Author: Bernhard Bablok
# License: GPL3
#
# Website: https://github.com/bablokb/pi-vameter
#
# ----------------------------------------------------------------------------

DEFAULT_PORT = 8026
DATA_ROOT    = "/var/lib/vameter/data"

# --- System-Imports   ------------------------------------------------------

import sys, os, json
from argparse import ArgumentParser

import rrdtool

import bottle
from bottle import route

# --- helper class for options   --------------------------------------------

class Options(object):
  pass

# --- get values   ----------------------------------------------------------

def get_values(rrd):
  """ return key values of given database """

  sumfile = os.path.splitext(rrd)[0] + ".summary"
  f = open(sumfile,"r")
  result = json.load(f)
  f.close()
  return result

# --- get result list   -----------------------------------------------------

def get_results():
  """ query results from filesystem """

  global options
  data_root = options.data_root[0]

  # sanity check
  if not os.path.isdir(data_root):
    return []

  # build list of rrd-databases
  results = []
  for f in os.listdir(data_root):
    rrd = os.path.join(data_root,f)
    (root,ext) = os.path.splitext(rrd)
    if not ext == ".rrd":
      continue
    item = get_values(rrd)
    item['rrd'] = rrd
    for m in ['I','U','P']:
      item["%s_img" % m] = "%s-%s.png" % (root,m)
    results.append(item)
  return results

# --- query webroot   -------------------------------------------------------

def get_webroot(pgm):
  pgm_dir = os.path.dirname(os.path.realpath(pgm))
  return os.path.realpath(os.path.join(pgm_dir,"..","lib","vameter","web"))

def get_webpath(path):
  return os.path.join(WEB_ROOT,path)

# --- static routes   -------------------------------------------------------

@route('/css/<filepath:path>')
def css_pages(filepath):
    print(filepath)
    return bottle.static_file(filepath, root=get_webpath('css'))
  
@route('/js/<filepath:path>')
def js_pages(filepath):
    return bottle.static_file(filepath, root=get_webpath('js'))

# --- main page   -----------------------------------------------------------

@route('/')
def main_page():
  tpl = bottle.SimpleTemplate(name="index.html",lookup=[WEB_ROOT])
  return tpl.render()

# --- results   -------------------------------------------------------------

@route('/results',method='POST')
def results():
  """ lookup results in the filesystem """
  rows = get_results()
  print("DEBUG: rows: %r" % rows)
  if not rows:
    print("DEBUG: no results available")
    return "{}"

  print("DEBUG: number of results: %d" % len(rows))
  bottle.response.content_type = 'application/json'
  return json.dumps(rows)

# --- start data collection   -----------------------------------------------

@route('/start',method='POST')
def start():
  """ start data collection """
  print("DEBUG: starting data collection")
  pass

# --- stop data collection   -----------------------------------------------

@route('/stop',method='POST')
def stop():
  """ stop data collection """
  print("DEBUG: stopping data collection")
  pass

# --- shutdown system   ----------------------------------------------------

@route('/shutdown',method='POST')
def shutdown():
  """ shutdown the system """
  print("DEBUG: shutting down the system """)
  pass

# --- rebooting the system   -----------------------------------------------

@route('/reboot',method='POST')
def reboot():
  """ rebooting the system """
  print("DEBUG: rebooting the system")
  pass

# --- commandline-parser   --------------------------------------------------

def get_parser():
  parser = ArgumentParser(add_help=False,
    description='Simple webserver for pi-vameter')

  parser.add_argument('-H', '--host', nargs=1,
    metavar='host', default=['0.0.0.0'],
    dest='host',
    help='host-mask')
  parser.add_argument('-P', '--port', nargs=1,
    metavar='port', default=[DEFAULT_PORT],
    dest='port',
    help='port the server is listening on (default: %d)' % DEFAULT_PORT)

  parser.add_argument('-D', '--dir', nargs=1,
    metavar='data-root', default=[DATA_ROOT],
    dest='data_root',
    help='directory with RRDs and graphics')

  parser.add_argument('-d', '--debug',
    dest='debug', default=False, action='store_true',
    help='start in debug-mode')

  parser.add_argument('-h', '--hilfe', action='help',
    help='display this help')
  return parser

# --- main program   --------------------------------------------------------

if __name__ == '__main__':
  # read options
  opt_parser = get_parser()
  options = opt_parser.parse_args(namespace=Options)

  # start server
  WEB_ROOT = get_webroot(__file__)
  print("DEBUG: web-root directory: %s" % WEB_ROOT)
  if options.debug:
    print("DEBUG: starting the webserver in debug-mode")
    bottle.run(host='localhost', port=options.port[0], debug=True,reloader=True)
  else:
    bottle.run(host=options.host[0], port=options.port[0], debug=False,reloader=False)
