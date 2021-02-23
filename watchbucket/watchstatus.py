#!/usr/bin/python
#-*- coding: utf-8 -*-

import settings as conf
from tools.s3tools import connect_s3, boto
import json
import time
from tools.logtools import Log
import os
import sys
from tools.database import db
from tools.utils import to_utf8, call_server_post
from tools.ftp import ftp_connect


S3_DATA = dict(
  host=dict(
    host=conf.S3_HOST,
    scheme=conf.S3_SCHEME
  ),
  access_id=conf.S3_KEY,
  access_key=conf.S3_SECRET,
  bucket=conf.S3_BUCKET
)

FTP_CREDENTIALS = dict(host=conf.FTP_HOST, port=conf.FTP_PORT, username=conf.FTP_USERNAME, password=conf.FTP_PASSWORD)

STATUS_URL = '%s/%s/status' % (conf.QENCODE_API_SERVER, conf.QENCODE_API_VERSION)


class WatchStatus(object):

  def __init__(self):
    self._log = Log('(PID %s) ' % os.getpid())
    self.bucket = None
    self.connect()
    self._worker()

  def _worker(self):
    while 1:
      time.sleep(conf.SLEEP_INTERVAL_WATCH_STATUS)
      self._log.debug('getting task statuses...')
      data = db.task.get_all("status != 'completed' AND status != 'error' AND (error = 0 OR error IS NULL)", as_dict=True)
      self._log.debug('processing tasks count: ' + str(len(data)))
      for item in data:
        self._log.debug('getting job status: ' + item.get('token'))
        status = self.get_status(item.get('token'))
        if not status:
          continue
        error_description = None
        if 'error_description' in status:
          error_description = status['error_description']

        db.task.update_by_id(item.get('id'), dict(status=status['status'],
                                                  error=status['error'],
                                                  error_description=error_description))
        self._log.debug('status: %s', str(status))
        if status['status'] == 'completed' and str(status['error']) == '0':
          try:
            if conf.DELETE_PROCESSED_FILE:
              self.rm_file(item['filename'])
              self._log.debug('_worker.rm_file %s', item['filename'])
            else:
              self._log.debug('Move to processed: %s', item['filename'])
              path = conf.FTP_PROCESSED_FOLDER if conf.MODE == 'ftp' else conf.PROCESSED_PATH
              self.mv_file(item['filename'], path)
          except Exception as e:
            self._log.error('Error finalizing video: %s', str(e))
            self._log.debug('skipping videos:', repr(status['videos']))
        if str(status['error']) == '1':
          self._log.debug('Move to errors: %s', item['filename'])
          path = conf.FTP_ERRORS_FOLDER if conf.MODE == 'ftp' else conf.ERRORS_PATH
          self.mv_file(item['filename'], path)



  def call_server(self, url, post_data):
    try:
      return call_server_post(url, post_data)
    except Exception as e:
      self._log.error('%s', str(e))

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
      self._log.error('connect to: %s/%s' % (conf.S3_HOST, conf.S3_BUCKET))
      self.bucket = connect_s3(S3_DATA)
    except Exception as e:
      self._log.error('%s', str(e))
      sys.exit(1)

  def _s3_reconnect(self):
    try:
      self._log.error('reconnect to: %s/%s' % (conf.S3_HOST, conf.S3_BUCKET))
      self.bucket = connect_s3(S3_DATA)
    except Exception as e:
      self._log.error('%s', str(e))
      
  def _ftp_connect(self):
    try:
      self.ftp = ftp_connect(FTP_CREDENTIALS, conf.USE_TLS)
      self._log.debug('Connect to: %s', conf.FTP_HOST)
    except Exception as e:
      self._log.error('%s', str(e))
      sys.exit(1)

  def _ftp_reconnect(self):
    self._log.debug("Trying reconnect to: %s",  conf.FTP_HOST)
    try:
      self.ftp = ftp_connect(FTP_CREDENTIALS, conf.USE_TLS)
      self._log.debug('Reconnect to: %s', conf.FTP_HOST)
    except Exception as e:
      self._log.error('%s', str(e))

  def rm_file(self, file_name):
    while 1:
      try:
        if conf.MODE == 's3':
          self._s3_rm_file(file_name)
        if conf.MODE == 'ftp':
          self._ftp_rm_file(file_name)
        
      except Exception as e:
        self._log.error('_worker.rm_file error %s', str(e))
        self.reconnect()
        time.sleep(5)
      else:
        break

  def _s3_rm_file(self, file_name):
    key_name = "%s/%s" % (conf.INPUT_PATH, file_name)
    old_key = self.bucket.get_key(key_name)
    old_key.delete()

  def get_status(self, token):
    res = self.call_server(STATUS_URL, {'task_tokens[]': token})
    if not res:
      return
    status = res['statuses'][token]
    if not status:
      return
    self._log.debug('%s: status: %s error: %s', token, status.get('status'), status.get('error'))
    return status

  def mv_file(self, filename, path):
    while 1:
      try:
        if conf.MODE == 's3':
          self._s3_mv_file(filename, path)
        if conf.MODE == 'ftp':
          self._ftp_mv_file(filename, path)
        
      except Exception as e:
        self._log.error('_worker.mv_file error %s', str(e))
        self.reconnect()
        time.sleep(5)
      else:
        break

  def _s3_mv_file(self, filename, path):
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
    
  def _ftp_mv_file(self, file_name, path):
    ftp = self.ftp['ftp_obj']
    ftp.retrlines("LIST")
    # ftp.cwd(processing_path)
    # ftp.delete(file_name)
    old_name = '{0}/{1}'.format(conf.FTP_PROCESSING_FOLDER, file_name)
    new_name = '{0}/{1}'.format(path, file_name)
    ftp.rename(old_name, new_name)
    self._log.debug('_worker.mv_file: %s to %s', old_name, new_name)
    
  def _ftp_rm_file(self, file_name):
    ftp = self.ftp['ftp_obj']
    ftp.retrlines("LIST")
    ftp.cwd(conf.FTP_PROCESSING_FOLDER)
    ftp.delete(file_name)
    self._log.debug('_worker.rm_file: %s', file_name)
    

def main():
  WatchStatus()


if __name__ == '__main__':
  main()
