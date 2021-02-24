# watchfolder
Use this script to monitor an S3 bucket or an FTP folder and automatically launch transcoding jobs when new files are uploaded.

## pre-requisites
 * python2
 * mysql
 * boto==2.40.0 (for S3 mode)
 * qencode>=0.9.1
 * urllib2
 * httplib
 * ssl
 * json

## setup and configuration

 1. Create a folder (e.g. "watchbucket") and clone the script into it:

```
git clone https://github.com/qencode-dev/watchfolder.git ./watchbucket/
```

 2. Create a database by running sql scripts from _sql/database_ddl.sql and set db access params in watchbucket/settings/db.py

 3. Set the script mode (either 's3' or 'ftp') in watchbucket/settings/sys.py

 4. In S3 mode:
    * Specify S3 host, bucket and credentials in watchbucket/settings/ftp.py

    In FTP mode:
    * Specify FTP host and credentials in watchbucket/settings/ftp.py

 5. Modify paths in services.sh so it points to the folder you cloned the script to.

 6. Set Qencode API Key in watchbucket/settings/qencode.py

 7. Update job query JSON in watchbucket/query/query.json

 You can create several .json files in watchbucket/query folder. In this case a separate transcoding job will be launched for each json request.
 Available placeholders for query.json:

 * {source_url} - url to the source video
 * {file_name} - output file name


