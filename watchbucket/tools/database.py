#!/usr/bin/python
#-*- coding: utf-8 -*-

import sys
import os
import os.path
sys.path.append(os.path.abspath(os.path.join(os.getcwd(),"../..")))

import MySQLdb as mysql
import settings as config

def db_connect():
  connect = mysql.connect(
    host=config.DATABASE_HOST, db=config.DATABASE_NAME, 
    user=config.DATABASE_USER, passwd=config.DATABASE_PASSWORD,
    charset=config.DATABASE_CHARSET
  )
  connect.autocommit(True)
  return connect

class AS_IS(object):
  def __init__(self, value):
    self.value = value

class BaseStorage(object):
  AS_IS = AS_IS
  TABLE_NAME = None
  ID_FIELD = 'id'
  PARAM_CHAR = '%s'

  def __init__(self, table=None, id_field=None, connect=None):
    self._connect = None
    self._cursor  = None
    self._table = table if table else self.TABLE_NAME
    self._id_field = id_field if id_field else self.ID_FIELD
    self.reconnect(connect)

  id_field = property(lambda self: self._id_field)

  def _close_cursor(self):
    self._cursor.close()
    self._cursor = None

  def _execute(self, *args, **kwargs):
    try:
      self._cursor.execute(*args, **kwargs)
    except Exception, error:
      if repr(error).find('InterfaceError') >= 0:
        self._cursor = self._connect.cursor()
        self._cursor.execute(*args, **kwargs)
      else:
        raise error

  def reconnect(self, connect=None):
    if connect is None:
      connect = db_connect()
    self._connect = connect
    self._cursor  = self._connect.cursor()

  def _prepare_where(self, where):
    where_array = []; where_values = []
    if where:
      if   isinstance(where, dict):
        where_array = []
        for name, value in where.items():
          name = name.strip()
          end_char = name[-1:]
          if end_char not in ( '=', '<', '>' ):
            w1 = "%s = %s" % (name, self.PARAM_CHAR)
          else:
            w1 = "%s %s" % (name, self.PARAM_CHAR)
          where_array.append(w1)
          where_values.append(value)
        where = " AND ".join(where_array)
      elif not isinstance(where, basestring):
        where = None
    else:
      where = None
    return (where, where_values)

  def _prepare_join(self, join):
    if isinstance(join, str):
      join = 'JOIN %s' % join
    else:
      join_array = []
      for item in join:
        if isinstance(join, str):
          item = 'JOIN %s' % item
        else:
          item = 'JOIN %s ON %s' % tuple(item)
        join_array.append(item)
      join = '\n'.join(join_array)
    return join

  def _prepare_left_join(self, join):
    if isinstance(join, str):
      join = 'LEFT JOIN %s' % join
    else:
      join_array = []
      for item in join:
        if isinstance(join, str):
          item = 'LEFT JOIN %s' % item
        else:
          item = 'LEFT JOIN %s ON %s' % tuple(item)
        join_array.append(item)
      join = '\n'.join(join_array)
    return join

  def _prepare_dict_items(self, data, cursor):
    descriptions = [ desc[0] for desc in cursor.description ]
    res = []
    for item in data:
      item2 = dict([
        (name, value) for name, value in map(None, descriptions, item) 
      ])
      res.append(item2)
    return res

  def _prepare_dict_item(self, data, cursor):
    if data:
      res = dict([ 
        (desc[0], value) for desc, value in map(None, cursor.description, data)
      ])
    else:
      res = None
    return res

  def _correct_timestamp(self, timestamp):
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

  def close(self):
    self._close_cursor()
    self._connect.close()
    self._connect = None

  def with_transaction(self, function, *args, **kwargs):
    self.begin()
    error = None
    try:
      res = function(*args, **kwargs)
    except Exception, error:
      print_exception()
      self.rollback()
      raise error
    else:
      self.commit()
    return res

  def execute(self, command, values=None):
    if values is not None:
      self._execute(command, values)
    else:
      self._execute(command)
    return self._cursor

  def execute_and_fetch(self, command, values=None, as_dict=False):
    cursor = self.execute(command, values)    
    res = cursor.fetchall()
    if res and as_dict:
      res = self._prepare_dict_items(res, cursor)
    return res

  def begin(self):
    self._execute('BEGIN')

  def commit(self):
    self._execute('COMMIT')

  def rollback(self):
    self._execute('ROLLBACK')

  def delete(self, where=None, debug=False):
    command = "DELETE FROM %s" % self._table
    where, where_values = self._prepare_where(where)
    if where:
      command += " WHERE %s" % where
    if debug:
      print command
      print 'values:', where_values
    self._execute(command, where_values)

  def insert(self, data, table=None, debug=False):
    names = data.keys(); values = data.values()
    names = ", ".join(names)
    holders = ", ".join([self.PARAM_CHAR]*len(values))
    table = table if table else self._table
    command = 'INSERT INTO %s (%s) VALUES (%s)' % (
      table, names, holders
    )
    if debug:
      print command, values
    self._execute(command, tuple(values))
    return self._cursor.lastrowid

  def update(self, data, where, table=None, debug=False):
    sets_array = []; values = []
    table = table if table else self._table
    for name, value in data.items():
      if isinstance(value, self.AS_IS):
        sets_array.append("%s = %s" % (name, value.value))
      else:
        sets_array.append("%s = %s" % (name, self.PARAM_CHAR))
        values.append(value)
    sets = ", ".join(sets_array)
    command = "UPDATE %s SET %s" % (table, sets)
    if where:
      where, where_values = self._prepare_where(where)
      command += " WHERE %s" % where
      values.extend(where_values)
    if debug:
      print command, values
    self._execute(command, values)

  def get_by_id(self, id, select=None, table=None, as_dict=True, debug=False):
    return self.get({ self._id_field: id }, select, table=table, as_dict=as_dict, debug=debug)

  def update_by_id(self, id, data, debug=False):
    self.update(data, { self._id_field: id }, debug=debug)

  def delete_by_id(self, id, debug=False):
    self.delete({ self._id_field: id }, debug=debug)

  def get(self, where, select=None, order_by=None, join=None, table=None, 
    as_dict=False, debug=False
  ):
    if select is None:
      select = '*'
    table = table if table else self._table
    command = "SELECT %s FROM %s" % (select, table)
    where, where_values = self._prepare_where(where)
    if join:
      join = self._prepare_join(join)
      command += '\n %s' % join
    if where:
      command += " WHERE %s" % where
    if order_by:
      command += " ORDER BY %s" % order_by
    command += " LIMIT 1"
    if debug:
      print command
      print 'values:', where_values
    self._execute(command, where_values)
    res = self._cursor.fetchone()
    if res and as_dict:
      res = self._prepare_dict_item(res, self._cursor)
    return res

  def get_all(self, where=None, select=None, order_by=None, group_by=None, limit=None, join=None,
    left_join=None, table=None, as_dict=False, debug=False
  ):
    table = table if table else self._table
    if select is None:
      select = '*'
    command = "SELECT %s FROM %s" % (select, table)
    where, where_values = self._prepare_where(where)
    if join:
      join = self._prepare_join(join)
      command += '\n %s' % join
    if left_join:
      left_join = self._prepare_left_join(left_join)
      command += '\n %s' % left_join
    if where:
      command += " WHERE %s" % where
    if order_by:
      command += " ORDER BY %s" % order_by
    if group_by:
      command += " GROUP BY %s" % group_by
    if limit:
      command += " LIMIT %s" % limit
    if debug:
      print command
      print 'values:', where_values
    return self.execute_and_fetch(command, where_values, as_dict=as_dict)

  def get_list(self, where, field=None, debug=False):
    if field is None:
      field = self._id_field
    data = self.get_all(where, field, debug=debug)
    data = [ item[0] for item in data ]
    return data

  def exists(self, where, field=None):
    field = field if field else self._id_field
    res = self.get(where, field)
    return res

  def add(self, data=None, **kwargs):
    data = data if data is not None else {}
    data = dict(data, **kwargs)
    return self.with_transaction(self.insert, data)

  def save(self, where, data, table=None, debug=False):
    self.with_transaction(self.update, data, where, table=table, debug=debug)

  def save_by_id(self, id, data, table=None, debug=False):
    self.save({ self._id_field : id }, data, table=table, debug=debug)

class TaskStorage(BaseStorage):
  TABLE_NAME = 'task'

  def get_by_token(self, token, select=None, as_dict=True, debug=False):
    return self.get(dict(token=token), select, as_dict=as_dict, debug=debug)

  def update_by_token(self, token, data, debug=False):
    self.with_transaction(
      self.update, data, dict(token=token), debug=debug
    )


class DBManager(object):
  task = property(lambda self: TaskStorage())

db = DBManager()
