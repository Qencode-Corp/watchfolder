#
import ftptools

def ftp_connect(connect_params, is_secure):
  return ftptools.connect(
    connect_params['host'], connect_params['port'],
    login=connect_params['username'], password=connect_params['password'],
    is_secure=is_secure
  )