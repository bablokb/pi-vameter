#!/usr/bin/python
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Simple web-interface for the results of vameter.py
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

import sys, os, json, subprocess
from argparse import ArgumentParser

import rrdtool

import bottle
from bottle import route
from gevent import monkey; monkey.patch_all()

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
    (name,ext) = os.path.splitext(f)
    if not ext == ".rrd":
      continue
    try:
      item = get_values(os.path.join(data_root,f))
      item['name'] = name
      item['rrd'] = "/data/%s" % f
      for m in ['I','U','P']:
        item["%s_img" % m] = "/data/%s-%s.png" % (name,m)
      results.append(item)
    except:
      # get_values fails if no summary-file is present - so ignore rrd
      pass
  return results

# --- query webroot   -------------------------------------------------------

def get_webroot(pgm_dir):
  return os.path.realpath(os.path.join(pgm_dir,"..","lib","vameter","web"))

def get_webpath(path):
  return os.path.join(WEB_ROOT,path)

# --- static routes   -------------------------------------------------------

@route('/css/<filepath:path>')
def css_pages(filepath):
    return bottle.static_file(filepath, root=get_webpath('css'))
  
@route('/images/<filepath:path>')
def images(filepath):
    return bottle.static_file(filepath, root=get_webpath('images'))

@route('/js/<filepath:path>')
def js_pages(filepath):
    return bottle.static_file(filepath, root=get_webpath('js'))

@route('/data/<filepath:path>')
def data_pages(filepath):
  global options
  return bottle.static_file(filepath, root=options.data_root[0])

# --- main page   -----------------------------------------------------------

@route('/')
def main_page():
  tpl = bottle.SimpleTemplate(name="index.html",lookup=[WEB_ROOT])
  return tpl.render()

# --- results   -------------------------------------------------------------

@route('/results',method='POST')
def results():
  """ lookup results in the filesystem """

  global options

  rows = get_results()
  if options.debug:
    print("DEBUG: rows: %r" % rows)
    print("DEBUG: number of results: %d" % len(rows))
  bottle.response.content_type = 'application/json'
  return json.dumps(rows)

# --- download database   ---------------------------------------------------

@route('/download',method='GET')
def delete():
  """ download data """

  global options
  # get name-parameter
  name = bottle.request.query.get('name')

  if options.debug:
    print("DEBUG: processing delete (name: %s)" % name)

  if name is None:
    msg = '"missing argument"'
    bottle.response.content_type = 'application/json'
    bottle.response.status       = 400                 # bad request
    return '{"msg": ' + msg +'}'

  # make sure we don't have fake input-data
  words = name.split(os.sep)
  if len(words) > 1:
    if options.debug:
      print("DEBUG: separators in %s: %d" % (f,len(words)))
    msg = '"invalid argument"'
    bottle.response.content_type = 'application/json'
    bottle.response.status       = 400                 # bad request
    return '{"msg": ' + msg +'}'

  # check if database file exists
  f = os.path.join(options.data_root[0],"%s.rrd" % name)
  if options.debug:
    print("DEBUG: checking %s" % f)
  if not os.path.exists(f):
    msg = '"database does not exist"'
    bottle.response.content_type = 'application/json'
    bottle.response.status       = 404                # not found
    return '{"msg": ' + msg +'}'

  # convert to xml and download result
  bottle.response.content_type = 'application/xml'
  bottle.response.set_header('Content-Disposition','attachment; filename=%s.xml' % name)
  return subprocess.check_output(['rrdtool','dump',f])

# --- delete entry   --------------------------------------------------------

@route('/delete',method='POST')
def delete():
  """ delete data """

  global options
  # get name-parameter
  name = bottle.request.forms.get('name')

  if options.debug:
    print("DEBUG: processing delete (name: %s)" % name)

  bottle.response.content_type = 'application/json'

  # make sure we don't have fake input-data
  words = name.split(os.sep)
  if len(words) > 1:
    if options.debug:
      print("DEBUG: slashes in %s: %d" % (f,len(words)))
    msg = '"invalid argument"'
    bottle.response.status       = 400                 # bad request
    return '{"msg": ' + msg +'}'

  # find and delete all matching files
  count = 0
  for suffix in ['.rrd','.summary','.xml','-I.png','-U.png','-P.png']:
    f = os.path.join(options.data_root[0],"%s%s" % (name,suffix))
    if options.debug:
      print("DEBUG: checking %s" % f)
    if os.path.exists(f):
      count += 1
      os.unlink(f);
      if options.debug:
        print("DEBUG: deleted %s" % f)

  # return number of deleted files
  msg = '"deleted %d files"' % count
  print "DEBUG: count: %d, msg: %s" % (count,msg)
  bottle.response.status = 200                 # OK
  return '{"msg": ' + msg +'}'

# --- rename entry   --------------------------------------------------------

@route('/rename',method='POST')
def rename():
  """ delete data """

  global options
  # get name-parameter
  name     = bottle.request.forms.get('name')
  new_name = bottle.request.forms.get('new_name')

  if options.debug:
    print("DEBUG: processing rename from %s to %s" % (name,new_name))

  bottle.response.content_type = 'application/json'

  # check input parameters
  if len(new_name) == 0:
    if options.debug:
      print("DEBUG: no new name specified")
    msg = '"missing new name"'
    bottle.response.status       = 400                 # bad request
    return '{"msg": ' + msg +'}'

  # find and rename all matching files
  count = 0
  for suffix in ['.rrd','.summary','.xml','-I.png','-U.png','-P.png']:
    f_old = os.path.join(options.data_root[0],"%s%s" % (name,suffix))
    f_new = os.path.join(options.data_root[0],"%s%s" % (new_name,suffix))
    if options.debug:
      print("DEBUG: checking %s" % f_old)
    if os.path.exists(f_old):
      count += 1
      os.rename(f_old,f_new);
      if options.debug:
        print("DEBUG: renamed %s to %s" % (f_old,f_new))

  # recreate img-files
  args = [
    os.path.join(options.pgm_dir,"vameter.py"),
    "-D",
    options.data_root[0],
    "-g",
    "UIP",
    os.path.join(options.data_root[0],"%s.rrd" % new_name)
    ]
  subprocess.check_output(args)

  # return number of deleted files
  msg = '"renamed %d files"' % count
  print "DEBUG: count: %d, msg: %s" % (count,msg)
  bottle.response.status = 200                 # OK
  return '{"msg": ' + msg +'}'

# --- start data collection   -----------------------------------------------

@route('/start',method='POST')
def start():
  """ start data collection """

  global options
  # get name-parameter
  name = bottle.request.forms.get('name')

  if options.debug:
    print("DEBUG: starting data collection (name: %s)" % name)
  args = [
    os.path.join(options.pgm_dir,"vameter.py"),
    "-D",
    options.data_root[0],
    "-O",
    "json",
    "-g",
    "UIP",
    "-r"
    ]
  if len(name):
    args.append(os.path.join(options.data_root[0],"%s.rrd" % name))

  # start process
  options.collect_process = subprocess.Popen(args,
                                             bufsize=-1,
                                             stdout=subprocess.PIPE,
                                             stderr=options.devnull)

# --- send server-side-events   --------------------------------------------

@route('/update',method='GET')
def update():
  """ send server side event data """

  global options
  p = options.collect_process
  if not p:
    bottle.response.content_type = 'text/plain'
    bottle.response.status = 404                 # not found

  try:
    bottle.response.content_type = 'text/event-stream'
    bottle.response.set_header('Cache-Control','no-cache')
    bottle.response.set_header('Connection','keep-alive')
    while True:
      data = p.stdout.readline()
      if data == '' and p.poll() is not None:
        break
      if data:
        # send data using SSE
        bottle.response.status = 200                 # OK
        yield "data: %s\n\n" % data
  except:
    pass
  bottle.response.content_type = 'text/plain'
  bottle.response.status = 404

# --- stop data collection   -----------------------------------------------

@route('/stop',method='POST')
def stop():
  """ stop data collection """

  global options
  if options.debug:
    print("DEBUG: stopping data collection")
  if options.collect_process:
    options.collect_process.terminate()
    options.collect_process = None

# --- shutdown system   ----------------------------------------------------

@route('/shutdown',method='POST')
def shutdown():
  """ shutdowne the system """

  global options
  if options.debug:
    print("DEBUG: shutting down the system """)
  os.system("sudo /sbin/halt &")

# --- rebooting the system   -----------------------------------------------

@route('/reboot',method='POST')
def reboot():
  """ rebooting the system """

  global options
  if options.debug:
    print("DEBUG: rebooting the system")
  os.system("sudo /sbin/reboot &")

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
  options.collect_process = None
  options.devnull = open(os.devnull)
  options.pgm_dir = os.path.dirname(os.path.abspath(__file__))
  if options.debug:
    print("DEBUG: pgm_dir directory: %s" % options.pgm_dir)

  # start server
  WEB_ROOT = get_webroot(options.pgm_dir)
  if options.debug:
    print("DEBUG: web-root directory: %s" % WEB_ROOT)
    print("DEBUG: starting the webserver in debug-mode")
    bottle.run(host='localhost',
               port=options.port[0],
               debug=True,reloader=True,
               server='gevent')
  else:
    bottle.run(host=options.host[0],
               port=options.port[0],
               debug=False,reloader=False,
               server='gevent')
