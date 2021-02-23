#
import socket
try:
  from . import ftplib2 as ftplib
except ImportError:
  import ftplib

class FTP(ftplib.FTP):
  def makepasv(self):
    if self.af == socket.AF_INET:
      host, port = ftplib.parse227(self.sendcmd('PASV'))
    else:
      host, port = ftplib.parse229(self.sendcmd('EPSV'), self.sock.getpeername())
      # We tweak this so we don't use the internal ip returned by the remote server.
      # old: `return host, port`
    return self.host, port

class FTPS(ftplib.FTP_TLS):
  def makepasv(self):
    if self.af == socket.AF_INET:
      host, port = ftplib.parse227(self.sendcmd('PASV'))
    else:
      host, port = ftplib.parse229(self.sendcmd('EPSV'), self.sock.getpeername())
      # We tweak this so we don't use the internal ip returned by the remote server.
      # old: `return host, port`
    return self.host, port

def connect(host, port, login=None, password=None, is_passive=True, is_secure=False):
  if not login:
    login = 'anonymous'
    password = 'guest'

  ftp = FTPS() if is_secure else FTP()
  ftp.set_pasv(is_passive)
  transfer_log = ftp.connect(host, int(port)) + '\n'
  transfer_log += ftp.login(login, password) + '\n'
  if callable(getattr(ftp, "prot_p", None)) == True:
    try:
      transfer_log += ftp.prot_p() + '\n'
    except Exception:
      transfer_log += ftp.prot_c() + '\n'
  return {'ftp_obj': ftp, 'log': transfer_log}
