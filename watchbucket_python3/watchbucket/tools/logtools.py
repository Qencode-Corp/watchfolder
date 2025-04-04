#
import sys
import time
import traceback
from io import StringIO

def print_exception(file=None):
  file = file if file is not None else sys.stderr
  traceback.print_exc(file=file)

class StopCommand(object):
  pass

class LogItem(object):
  __slots__ = [ 'timestamp', 'message' ]
  def __init__(self, timestamp, message):
    self.timestamp = timestamp
    self.message = message

class Log(object):
  TIMESTAMP_FORMAT = '%Y-%m-%d %H:%M:%S'
  FORMAT = '[{0}] {1}{2}\n'

  def __init__(self, prefix=None):
    self._prefix = prefix

  def debug(self, message, *args):
    timestamp = self._get_timestamp()
    message = self._format_message(message, args)
    self._print_item(LogItem(timestamp, message))

  def error(self, message, *args):
    self.debug(message, *args)

  def error2(self, where, message='', *args):
    d_message = '{0}: {1}'.format(where, message)
    self.debug(d_message, *args)

  def exception(self, message='', *args):
    where = message.strip().rstrip(':')
    self._exception(where, message, *args)

  def exception2(self, where, message='', *args):
    message = '{0}: {1}'.format(where, message) if message else '{0}:'.format(where)
    self._exception(where, message, *args)

  def _print_item(self, item):
    prefix = self._prefix if self._prefix else ''
    try:
      timestamp = self._format_timestamp(item.timestamp)
      text = self.FORMAT.format(timestamp, prefix, item.message)
    except:
      print_exception()
    else:
      sys.stdout.write(text)

  def _get_timestamp(self):
    return time.gmtime()

  def _format_timestamp(self, timestamp):
    return time.strftime(self.TIMESTAMP_FORMAT, timestamp)

  def _format_message(self, template, args):
    try:
      message = template % args
    except BaseException as error:
      message = '{0}: {1}\n{2} {3}'.format(self.__class__.__name__, error, template, args)
    return message

  def _get_exception(self):
    f = StringIO.StringIO()
    print_exception(f)
    text = f.getvalue().rstrip()
    f.close()
    return text

  def _exception(self, where, message='', *args):
    timestamp = self._get_timestamp()
    message = self._format_message(message, args)
    message = '{0}\n{1}'.format(message, self._get_exception())
    self._print_item(LogItem(timestamp, message))
