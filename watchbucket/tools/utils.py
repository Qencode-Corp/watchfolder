import urllib2
import urllib
import json

def to_utf8(text):
  if isinstance(text, unicode):
    text = text.encode('utf-8')
  return text

def call_server_post(url, post_data):
  data = urllib.urlencode(post_data)
  request = urllib2.Request(url, data)
  res = urllib2.urlopen(request)
  return json.loads(res.read())
