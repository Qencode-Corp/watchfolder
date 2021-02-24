import os

MODE = 'ftp' # available 's3', 'ftp'.

SLEEP_INTERVAL_WATCH_BUCKET = 10
SLEEP_INTERVAL_WATCH_STATUS = 15
QUEUE_SIZE = 5

INPUT_PATH = 'input' #important
PROCESSED_PATH = 'processed' #required
ERRORS_PATH = 'errors'

QUERY_DIR = os.path.abspath(os.path.join(os.getcwd(), './watchbucket/query'))
DELETE_PROCESSED_FILE = False
USE_DRM = False
USE_AES128 = False

DEV = False
DEBUG = False

# ftp

FTP_INPUT_FOLDER = '/input'
FTP_PROCESSING_FOLDER = '/processing'
FTP_PROCESSED_FOLDER = '/processed'
FTP_ERRORS_FOLDER = '/errors'



