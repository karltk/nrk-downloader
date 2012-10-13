#! /usr/bin/env python
#
# Downloader for the tv.nrk.no
#
# Copyright (c) 2012, Karl Trygve Kalleberg
# Licensed under the GNU General Public License, v3

import os
import re
import sys
import json
import urllib2
import urlparse
from urllib import urlencode

DATA_MEDIA_REGEX=re.compile('data-media="([^"]+)"')
BANDWIDTH_REGEX=re.compile('BANDWIDTH=([0-9]+)')

class ProgressBar:
  def __init__(self, max_pos):
    self._determine_width()
    self._cursor_at = 0
    self._max_pos = max_pos

  def _determine_width(self):
    self._draw = True
    if sys.stdout.isatty():
      try:  
        rows, columns = os.popen('stty size', 'r').read().split()
        self._columns = int(columns) - 2
      except:
        self._columns = 0
        self._draw = False
    else:
      self._draw = False

  def _draw_initial_bar(self):
    sys.stdout.write("[%s]" % (" " * self._columns))
    sys.stdout.flush()
    sys.stdout.write("\b" * (self._columns + 1))

  def update(self, pos):
    if not self._draw:
      return

    if pos == 0:
      self._draw_initial_bar()

    pos = min(pos, self._max_pos)

    if (1.0 * pos / self._max_pos) > (1.0 * self._cursor_at / self._columns):
      sys.stdout.write("=")
      sys.stdout.flush()
      self._cursor_at += 1

    if pos == self._max_pos:
      sys.stdout.write("]\n")
      sys.stdout.flush()


def slurp(url, params={}, headers={}):
  params = urlencode(params, doseq=True)
  request = urllib2.Request(url)
  for (k,v) in headers.iteritems():
    request.add_header(k, v)
  response = urllib2.urlopen(request)
  content = response.read()
  response.close()
  return content

def parse_alternatives(manifest):
  alternatives = {}
  prev_alternative = None
  for x in manifest.split("\n"):
    if x.startswith("#"):
      bw = BANDWIDTH_REGEX.search(x)
      if bw is not None:
        prev_alternative = int(bw.group(1))
    elif prev_alternative is not None:
      alternatives[prev_alternative] = x
    else:
      prev_alternative = None
  return alternatives


def count_chunks(index):
  count = 0
  for x in index.split("\n"):
    if not x.startswith("#"):
      count += 1
  return count

def fetch_and_merge_stream_data(index, fn):

  ous = open(fn, "wb")
  pb = ProgressBar(count_chunks(index))

  cursor_at = 0
  pos = 0

  pb.update(0)

  for x in index.split("\n"):
    if x.startswith("#"):
      continue
    if x.strip() is "":
      continue

    ous.write(slurp(x))
    pos += 1
    pb.update(pos)

  ous.close()

def guess_base_filename(url):
  o = urlparse.urlparse(url)
  return o.path.strip("/").replace("/", "_")

def remux_stream(tmp_fn, fn):
  exe = None
  for dir in sys.path:
    path = os.path.join(dir, "avconv")
    if os.path.isfile(path) and os.access(path, os.X_OK):
      exe = path
      break
  if exe:
    os.system(exe + " -i %s -acodec copy -vcodec copy %s" % (tmp_fn, fn))
  else:
    shutil.copyfile(tmp_fn, fn)

def main():

  url = sys.argv[1]
  base = guess_base_filename(url)
  temp_fn = base + ".m4v.download"
  fn = base + ".m4v"

  doc = slurp(url, headers={'Cookie' : 'NRK_PROGRAMPLAYER_SETTINGS=devicetype=desktop&preferred-player=hls&max-data-rate=2250;' })  
  m = DATA_MEDIA_REGEX.search(doc)
  if m is not None:

    manifest_url = m.group(1)
    manifest = slurp(manifest_url)
    alternatives = parse_alternatives(manifest)
    best = 0
    for x in alternatives.keys():
      best = max(x, best)
    best = alternatives[best]

    index = slurp(best)
    fetch_and_merge_stream_data(index, temp_fn)

    remux_stream(temp_fn, fn)
    os.unlink(temp_fn)
    print fn
    
if __name__ == '__main__':
  main()
