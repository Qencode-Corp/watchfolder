#

def prepare_file_name(file_name):
  if not file_name:
    return '{uuid}.mp4'
  return file_name

def prepare_extension(file_name, ext):
  try:
    eol = file_name.split('.')
    if len(eol) == 1:
      eol.append('')
    eol[len(eol) - 1] = ext
    if not ext:
      return '.'.join(eol)[:-1]
    return '.'.join(eol)
  except Exception:
    return file_name

def prepare_query(data, *args):
  data = data\
    .replace('{source_url}', args[0]) \
    .replace('{tag}', args[1]) \
    .replace('{file_name}', args[1])
  return data