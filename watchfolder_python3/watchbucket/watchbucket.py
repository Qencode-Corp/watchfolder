#
import collections
import os
import sys
import time
import boto3
import qencode3
import settings
from botocore.exceptions import ClientError
from tools.logtools import Log
from tools.prepare_data import prepare_query, prepare_extension, prepare_file_name

EncodeItem = collections.namedtuple('EncodeItem', ['key', 'file_name', 'url'])

class WatchBucket:
  API_KEY = settings.QENCODE_API_KEY
  API_SERVER = settings.QENCODE_API_SERVER
  CREATE_TASK_ATTEMPT_NUMBER = 3
#
  SLEEP_INTERVAL = settings.SLEEP_INTERVAL
#
  S3_KEY = settings.S3_KEY
  S3_SECRET = settings.S3_SECRET
  S3_BUCKET = settings.S3_BUCKET
  if settings.S3_HOST:
    S3_ENDPOINT = '%s://%s' % (settings.S3_SCHEME, settings.S3_HOST)
  else:
    S3_ENDPOINT = None
#
  INPUT_PATH = settings.INPUT_PATH
  ERRORS_PATH = settings.ERRORS_PATH
  PROCESSED_PATH = settings.PROCESSED_PATH
  URL_LIFETIME = settings.URL_LIFETIME
#
  GET_BUCKET_LIST_ATTEMPT_NUMBER = 5
  QUEUE_SIZE = settings.QUEUE_SIZE
  QUERY_DIR = settings.QUERY_DIR
  OUTPUT_EXTENSION = settings.OUTPUT_EXTENSION
  MOVE_FILE_TIMEOUT = 5

  def __init__(self):
    self._log = Log('(PID %s) ' % os.getpid())
    self._client = None
    self._bucket = None
    self._processed = set()
    if self._connect():
      sys.exit(1)
    self._qclient = qencode3.client(self.API_KEY, api_url=self.API_SERVER)
    if self._qclient.error:
      self._log.error(self._qclient.message)
      sys.exit(1)
    else:
      self._log.debug(
        'Qencode. Client created. (expiry date %s) ', self._qclient.expire
      )
    self._load_processed()
    self._worker()

#Private nethods
  def _connect(self):
    error = False
    self._client = None
    self._bucket = None
    params = {}
    if self.S3_ENDPOINT:
      params.update(endpoint_url=self.S3_ENDPOINT)
    session = boto3.Session(
      aws_access_key_id=self.S3_KEY, aws_secret_access_key=self.S3_SECRET
    )
    s3 = session.resource('s3', **params)
    self._bucket = s3.Bucket(self.S3_BUCKET)
    try:
      list(self._bucket.objects.pages())
    except Exception as e:
      self._log.error('%s', str(e))
      error = True
    else:
      self._client = boto3.client('s3',
        aws_access_key_id=self.S3_KEY, aws_secret_access_key=self.S3_SECRET,
        **params
      )
    return error

  def _get_files(self):
    objects = self._get_bucket_list()
    if not objects:
      self._log.error('Error getting objects list')
      return
    counter = 0
    encode_data = []
    for obj in objects:
      self._log.debug('_get_files.key: %s', obj.key)
      if obj.key == '..':
        continue
      file_name = obj.key.rsplit('/', 1)[-1]
      if file_name:
        if file_name in self._processed:
          continue
        self._log.debug('_get_files: adding to queue: %s', file_name)
        try:
          obj.Acl().put(ACL='public-read')
        except ClientError as e:
          self._log.error('_get_files.obj.acl: %s', e)
          continue
        try:
          url = self._client.generate_presigned_url(
            'get_object', Params=dict(Bucket=obj.bucket_name, Key=obj.key),
            ExpiresIn=self.URL_LIFETIME
          )
        except ClientError as e:
          self._log.error('_get)files.obj.generate_presigned_url: %s', e)
        encode_data.append(EncodeItem(url=url, key=obj.key, file_name=file_name))
        counter += 1
      if counter > self.QUEUE_SIZE:
        self._log.debug('_get_files: got limit of the queue: %s', self.QUEUE_SIZE)
        break
    if encode_data:
      self._log.debug('_get_files: list to encode: %s', encode_data)
    return encode_data

  def _get_bucket_list(self):
    self._log.debug('_get_bucket_list.begin:')
    objects = None
    prefix = None
    if self.INPUT_PATH:
      prefix = '%s/' % self.INPUT_PATH
    for _ in range(self.GET_BUCKET_LIST_ATTEMPT_NUMBER):
      try:
        if prefix:
          objects = self._bucket.objects.filter(Prefix=prefix)
        else:
          objects = self._bucket.objects.all()
      except Exception as e:
        self._log.error('%s', str(e))
        self._connect()
      else:
        break
    self._log.debug('_get_bucket_list.end:')
    return objects

  def _get_queries(self, source_url, filename):
    filename = prepare_file_name(filename)
    filename = prepare_extension(filename, self.OUTPUT_EXTENSION)

    names = os.listdir(self.QUERY_DIR)
    queries = []

    for name in names:
      if not name.endswith('.json'):
        continue
      try:
        json = open(os.path.join(self.QUERY_DIR, name), 'r').read()
        query = prepare_query(json, source_url, filename)
      except Exception as e:
        self._log.error('%s', str(e))
        sys.exit(1)
      else:
        queries.append(query)
    return queries

  def _start_encode(self, query, payload):
    task = self._create_task()

    if task.error:
      self._log.debug('_create_task.move: %s => %s', payload, self.ERRORS_PATH)
      self._move_file(payload, self.ERRORS_PATH)
      return task

    query = query.replace('\n', '').strip()
    self._log.debug('_start_encode.query: %s', query)
    task.custom_start(query, payload=payload)
    return task

  def _create_task(self):
    task = None
    for i in range(self.CREATE_TASK_ATTEMPT_NUMBER):
      task = self._qclient.create_task()
      self._log.debug('_create.task[%s] task_obj:%s', i, task)
      if not task or (task.error and task.error == 5):
        self._qclient.refresh_access_token()
        continue
      else:
        self._log.debug(
          '_create.task[%s] token: %s,  error: %s, msg: %s', i, task.task_token, task.error, task.message
        )
        break
    return task

  def _move_file(self, filename, path):
    while 1:
      try:
        self._move_file_simple(filename, path)
      except Exception as e:
        self._log.error('_move_file error %s', e)
        self._connect()
        time.sleep(self.MOVE_FILE_TIMEOUT)
      else:
        break

  def _move_file_simple(self, filename, path):
    old_key = "%s/%s" % (self.INPUT_PATH, filename)
    new_key = "%s/%s" % (path, filename)
    self._log.error('Move old_key: %s new_key: %s', old_key, new_key)

    source = dict(Bucket=self._bucket.name, Key=old_key)
    try:
      self._client.copy_object(
        Bucket=self._bucket.name, Key=new_key, CopySource=source
      )
    except ClientError as e:
      self._log.error('_move_file_simple error ', e)
      return
    else:
      self._bucket.delete_objects(Delete=dict(Objects=[dict(Key=old_key)]))

  def _mark_done(self, name, token):
    if self.PROCESSED_PATH:
      key = '%s/%s' % (self.PROCESSED_PATH, name)
      obj = self._bucket.Object(key)
      obj.put(Body=token)
    self._processed.add(name)

  def _load_processed(self):
    self._log.debug('_load_processed.begin:')
    if self.PROCESSED_PATH:
      prefix = '%s/' % self.PROCESSED_PATH
      for _ in range(self.GET_BUCKET_LIST_ATTEMPT_NUMBER):
        try:
          for obj in self._bucket.objects.filter(Prefix=prefix):
            if obj.key == '..':
              continue
            file_name = obj.key.rsplit('/', 1)[-1]
            if file_name:
              self._processed.add(file_name)
        except Exception as e:
          self._log.error('%s', str(e))
          self._connect()
        else:
          break
    self._log.debug('_load_processed.end:')

  def _worker(self):
    while 1:
      self._log.debug("_worker.sleep: %s seconds", self.SLEEP_INTERVAL)
      time.sleep(self.SLEEP_INTERVAL)
      encode_items = self._get_files()
      for item in encode_items:
        queries = self._get_queries(item.url, item.file_name)
        payload = item.file_name
        for query in queries:
          self._log.debug('_worker.start_encode: %s', payload)
          task = self._start_encode(query, payload)
          self._log.debug(
            '_worker.start_encode.res: token: %s, error: %s', task.task_token, task.error
          )
          if task.task_token is not None:
            self._mark_done(payload, task.task_token)

def main():
  WatchBucket()

if __name__ == '__main__':
  main()
