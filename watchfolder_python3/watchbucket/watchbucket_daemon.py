#!/usr/bin/env python3

import sys
from tools.daemon import daemon_command
from watchbucket import main

if __name__ == "__main__":
  if len(sys.argv) == 4:
    if daemon_command(main, sys.argv[1:3], sys.argv[3]):
      print("Unknown command")
      sys.exit(2)
    else:
      sys.exit(0)
  else:
    print("usage: %s pidfile logfile start|stop|restart|status" % sys.argv[0])
    sys.exit(2)
