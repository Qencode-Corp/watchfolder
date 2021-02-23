#!/usr/bin/python
#-*- coding: utf-8 -*-

import settings as conf
from tools.s3tools import connect_s3, boto
import qencode
import time
from tools.logtools import Log
import os
import sys
import socket
from tools.database import db, mysql
from tools.utils import to_utf8
from tools.prepare_data import prepare_query, prepare_extension, prepare_file_name
from tools.ftp import ftp_connect




S3_DATA = dict(
  host=dict(
    host=conf.S3_HOST_DEV if conf.DEV else conf.S3_HOST,
    scheme=conf.S3_SCHEME_DEV if conf.DEV else conf.S3_SCHEME
  ),
  access_id=conf.S3_KEY_DEV if conf.DEV else conf.S3_KEY,
  access_key=conf.S3_SECRET_DEV if conf.DEV else conf.S3_SECRET,
  bucket=conf.S3_BUCKET_DEV if conf.DEV else conf.S3_BUCKET
)

FTP_CREDENTIALS = dict(host=conf.FTP_HOST, port=conf.FTP_PORT, username=conf.FTP_USERNAME, password=conf.FTP_PASSWORD)


class WatchBucket(object):
  API_KEY = conf.QENCODE_API_KEY
  API_SERVER =  conf.QENCODE_API_SERVER

  def __init__(self):
    self._log = Log('(PID %s) ' % os.getpid())
    self.bucket = None
    self.ftp = None
    self.connect()
    self.client = qencode.client(self.API_KEY, api_url=self.API_SERVER)
    if self.client.error:
      self._log.error(self.client.message)
      sys.exit(1)
    else:
      self._log.debug('Qencode. Client created. (expiry date %s) ', self.client.expire)
    self._worker()

  def _worker(self):
    while 1:
      time.sleep(conf.SLEEP_INTERVAL_WATCH_BUCKET)
      self._log.debug("\ndaemon sleep [%s second]", conf.SLEEP_INTERVAL_WATCH_BUCKET)
      try:
        data = self.get_files()
      except socket.error as e:
        self.reconnect()
        self._log.error('_worker.get_files %s', str(e)) #socket.error: [Errno 111] Connection refused
        continue
      except Exception as e:
        self.reconnect()
        self._log.error('_worker.get_files %s', str(e))
        continue
      if not data:
        continue
      self._log.debug('got files: %s', str(data))
      for item in data:
        payload = item['file_name']
        queries = self.get_queries(item['url'], item['file_name'])
        for query in queries:
          task = self.start_encode(query, payload, 1)
          self._log.debug('start encode response [error, message] %s %s', task.error, task.message)
          if task.task_token:
            try:
              db.task.add(
                dict(source_url=item['url'], filename=item['file_name'], token=task.task_token, status='created'))
            except mysql.Error as e:
              self._log.error('_worker.db.task.add %s', str(e))
            finally:
              pass

  def readfile(self, filename):
    file = open(filename, "r")
    return file.read()

  def get_queries(self, input_video_url, filename):

    query_templates = os.listdir(conf.QUERY_DIR)
    queries = []

    filename = prepare_file_name(filename)
    filename = prepare_extension(filename, conf.OUTPUT_EXTENSION)

    for query in query_templates:
      if not query.endswith('.json'):
        continue
      if conf.DEV and not query.endswith('_dev.json'):
        continue
      try:
        json = self.readfile(os.path.join(conf.QUERY_DIR, query))
        data = prepare_query(json, input_video_url, filename)
        queries.append(data)
      except Exception as e:
        self._log.error('%s', str(e))
        sys.exit(1)
    return queries

  def create_task(self, filename, count):
    task = self.client.create_task()
    self._log.debug('create_task [error, message] %s %s', task.error, task.message)

    if task.error and task.error != 5:
      self._log.debug('Move to errors: %s', filename)
      self.mv_file(filename, conf.ERRORS_PATH)

    if task.error and task.error == 5 and count < 5:
      self.client.refresh_access_token()
      if self.client.error:
        self._log.error(self.client.message)
      self._log.debug('Qencode. Refresh access_token. Expiry date: %s) ', self.client.expire)
      time.sleep(3)
      self.create_task(filename, count + 1)
    return task

  def start_encode(self, query, payload, count):
    task = self.create_task(payload, 1)
    if task.error:
      return task

    task.error = None
    task.message = ''

    if conf.USE_DRM:
      task.drm(key=conf.DRM_KEY, iv=conf.DRM_IV, key_url=conf.DRM_KEY_URL,
               la_url=conf.DRM_KEY_URL, key_id=conf.DRM_KEY_ID, pssh=conf.DRM_PSSH)
    if conf.USE_AES128:
      task.aes128_encription(key=conf.DRM_KEY, iv=conf.DRM_IV, key_url=conf.DRM_KEY_URL)
      
    query = query.replace('\n', '').replace(' ', '').strip()
    task.custom_start(query, payload=payload)
    self._log.debug('start encode. task [try count, error, message] %s %s %s', count, task.error, task.message)
    self._log.debug('start encode with query: %s \npayload: %s', str(query), payload)

    if task.error and task.error == 5:
      self.client.refresh_access_token()
      if self.client.error:
        self._log.error(self.client.message)
        return self.client
      self._log.debug('Qencode. The access token is refreshed. (expiry date %s) ', self.client.expire)
      if count > 5:
        return task
      time.sleep(3)
      res = self.start_encode(query, payload, count + 1)
      if not res.error:
        return res
    return task
  
  def connect(self):
    if conf.MODE == 's3':
      self._s3_connect()
    if conf.MODE == 'ftp':
      self._ftp_connect()
      
  def reconnect(self):
    if conf.MODE == 's3':
      self._s3_reconnect()
    if conf.MODE == 'ftp':
      self._ftp_reconnect()

  def _s3_connect(self):
    try:
      self.bucket = connect_s3(S3_DATA)
      self._log.debug('Connect to: %s/%s', conf.S3_HOST, conf.S3_BUCKET)
    except Exception as e:
      self._log.error('%s', str(e))
      sys.exit(1)

  def _s3_reconnect(self):
    self._log.debug("Trying reconnect to: %s/%s",  conf.S3_HOST, conf.S3_BUCKET)
    try:
      self.bucket = connect_s3(S3_DATA)
      self._log.debug('Reconnect to: %s/%s', conf.S3_HOST, conf.S3_BUCKET)
    except Exception as e:
      self._log.error('%s', str(e))

  def get_bucked_list(self, count):
    self._log.debug('get_bucked_list %s', count)
    try:
      if conf.INPUT_PATH:
        prefix = "%s/" % conf.INPUT_PATH
        bucked_list = self.bucket.list(prefix=prefix)
      else:
        prefix = ''
        bucked_list = self.bucket.list(delimiter='/')
      return bucked_list, prefix
    except boto.exception.S3ResponseError as e:
      self._log.error('%s', str(e))
      if count > 5:
        return None
      self.reconnect()
      self.get_bucked_list(count + 1)
    except Exception as e:
      self._log.error('%s', str(e))
      
  def get_files(self):
    if conf.MODE == 's3':
      self._log.debug('_worker.get_files check: %s%s', conf.S3_BUCKET, conf.INPUT_PATH)
      return self._s3_get_files()
    if conf.MODE == 'ftp':
      self._log.debug('_worker.get_files check: %s%s', conf.FTP_HOST, conf.FTP_INPUT_FOLDER)
      return self._ftp_get_files()
      

  def _s3_get_files(self):
    bucked_list, prefix = self.get_bucked_list(1)
    if not bucked_list:
      self._log.error('Error getting key list')
      return
    encode_data = []
    counter = 0
    for object_key in bucked_list:
      if isinstance(object_key, boto.s3.prefix.Prefix):
        continue
      key_name = object_key.key
      self._log.debug("key_name: {0}".format(to_utf8(key_name)))
      key_name_list = key_name.split('/')
      file_name = key_name_list[len(key_name_list) - 1]
      file_name = to_utf8(file_name)
      is_exist = db.task.exists("filename = '{0}'".format(file_name))
      if is_exist:
        self._log.debug('skipped: {0}'.format(file_name))
        continue
      if counter > conf.QUEUE_SIZE:
        self._log.debug('got limit of the queue: {0}'.format(conf.QUEUE_SIZE))
        break
      self._log.debug('adding to queue: {0}'.format(file_name))

      if file_name:
        counter += 1
        object_key.set_acl('public-read')
        url = object_key.generate_url(2592000, query_auth=False)
        encode_data.append(dict(url=url, key_name=key_name, file_name=file_name))
    if len(encode_data) > 0:
      self._log.debug('list to encode: %s', str(encode_data))
    return encode_data

  def mv_file(self, filename, path):
    while 1:
      try:
        self._mv_file(filename, path)
      except Exception as e:
        self._log.error('_worker.mv_file error %s', str(e))
        self.reconnect()
        time.sleep(5)
      else:
        break

  def _mv_file(self, filename, path):
    old_key_name = "%s/%s" % (conf.INPUT_PATH, filename)
    new_key_name = "%s/%s" % (path, filename)
    self._log.error('old_key_name: %s',  old_key_name)
    self._log.error('new_key_name: %s', new_key_name)
    try:
      self.bucket.copy_key(new_key_name, conf.S3_BUCKET, old_key_name, preserve_acl=False)
    except Exception as e:
      self._log.error(str(e))
      return
    old_key = self.bucket.get_key(old_key_name)
    old_key.delete()
    
    
  # ftp
  
  def _ftp_connect(self):
    try:
      self.ftp = ftp_connect(FTP_CREDENTIALS, conf.USE_TLS)
      self._log.debug('Connect to: %s', conf.FTP_HOST)
    except Exception as e:
      self._log.error('%s', str(e))
      sys.exit(1)

  def _ftp_reconnect(self):
    self._log.debug("Trying to reconnect to: %s", conf.FTP_HOST)
    try:
      self.ftp = ftp_connect(FTP_CREDENTIALS, conf.USE_TLS)
      self._log.debug('Reconnect to: %s', conf.FTP_HOST)
    except Exception as e:
      self._log.error('%s', str(e))
  
  def _ftp_destination(self, file_name):
    file_path = '{0}/{1}'.format(conf.FTP_PROCESSING_FOLDER, file_name)
    file_path = file_path.replace('//', '/')
    url = 'ftp://{username}:{password}@{host}:{port}{file_path}'.format(
      password=conf.FTP_PASSWORD, username=conf.FTP_USERNAME, host=conf.FTP_HOST, port=conf.FTP_PORT, file_path=file_path
    )
    return url

  def _ftp_get_files(self):
    file_list = []
    ftp = self.ftp['ftp_obj']
    ftp.retrlines("LIST")
    ftp.cwd(conf.FTP_INPUT_FOLDER)
    files = ftp.nlst()
    for i, file in enumerate(files):
      try:
        is_exist = db.task.exists("filename = '{0}'".format(file))
        if is_exist:
          self._log.debug('skipped: {0}'.format(file))
          continue
      except Exception as e:
        self._log.error('%s', str(e))
        continue
      if i >= conf.QUEUE_SIZE:
        break
      old_name = '{0}/{1}'.format(conf.FTP_INPUT_FOLDER, file)
      new_name = '{0}/{1}'.format(conf.FTP_PROCESSING_FOLDER, file)
      self._log.debug('Trying to move: {0} {1}'.format(old_name, new_name))
      ftp.rename(old_name, new_name)
      self._log.debug('Moved: {0} {1}'.format(old_name, new_name))
      file_list.append(dict(url=self._ftp_destination(file), key_name=new_name, file_name=file))
      self._log.debug('Adding to queue: {0}'.format(file))
    # ftp.quit()
    return file_list


def main():
  WatchBucket()

if __name__ == '__main__':
  main()
