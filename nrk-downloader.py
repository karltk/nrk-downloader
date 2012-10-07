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
  chunks = count_chunks(index)
  
  rows, columns = os.popen('stty size', 'r').read().split()
  columns = int(columns) - 2
  
  sys.stdout.write("[%s]" % (" " * columns))
  sys.stdout.flush()
  sys.stdout.write("\b" * (columns + 1))
  
  cursor_at = 0
  pos = 0
  
  for x in index.split("\n"):
    if x.startswith("#"):
      continue
    if x.strip() is "":
      continue
      
    if (1.0 * pos / chunks) > (1.0 * cursor_at / columns):
      sys.stdout.write("=")
      sys.stdout.flush()
      cursor_at += 1
    
    ous.write(slurp(x))
    pos += 1
      
  sys.stdout.write("]\n")
  sys.stdout.flush()
  
  ous.close()
  
def guess_base_filename(url):
  o = urlparse.urlparse(url)
  return o.path.strip("/").replace("/", "_")

def remux_stream(tmp_fn, fn):
  os.system("avconv -i %s -acodec copy -vcodec copy %s" % (tmp_fn, fn))
  
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
