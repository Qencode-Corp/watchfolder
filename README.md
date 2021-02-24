# watchfolder
Use this script to monitor an S3 bucket or an FTP folder and automatically launch transcoding jobs when new files are uploaded.

## pre-requisites
 * python2
 * mysql
 * boto>=2.40.0 (for S3 mode)
 * qencode>=0.9.1
 * urllib2
 * httplib
 * ssl
 * json

## setup and configuration


 1. Create user 'encoder'. Under the user's home dir create a folder named "watchbucket" and clone the script into it:

```
git clone https://github.com/qencode-dev/watchfolder.git /home/encoder/watchbucket/
```

 2. Create a database by running sql scripts from _sql/database_ddl.sql and set db access params in watchbucket/settings/db.py

 3. Set the script mode (either 's3' or 'ftp') in watchbucket/settings/sys.py

 4. In S3 mode:
    * Specify S3 host, bucket and credentials in watchbucket/settings/ftp.py

    In FTP mode:
    * Specify FTP host and credentials in watchbucket/settings/ftp.py

 5. (Optional) Modify paths in services.sh so it points to the folder you cloned the script to.
 You need to do this only in case you need to run under the different username or in different folder.

 6. Set Qencode API Key in watchbucket/settings/qencode.py

 7. Update job query JSON in watchbucket/query/query.json
 
     Available placeholders for query.json:
    
     * {source_url} - url to the source video
     * {file_name} - output file name

    You can create several .json files in watchbucket/query folder. In this case a separate transcoding job will be launched for each json request.
    
 8. (FTP mode only) Create watchbucket "input", "processing", "processed" and "errors" folders in the root of your FTP server.
 
 You can optionally change these folders names in watchbucket/settings/sys.py
 
 By default there's the following flow:
 
  1) Upload the file to the S3 bucket or FTP server.
  
    IMPORTANT NOTE: in FTP mode you should upload source video and then move it to the "input" folder. 
    If you upload directly to the "input" folder, service might try prematurely launching a transcoding job for an incomplete file.
    
  2) After the transcoding job is launched, source video is moved to "processing" folder.  
  
  3) After transcoding job is successfully completed source video is moved to "processed" folder.
  In case you want source to be deleted after successful processing, you should set 
  
      DELETE_PROCESSED_FIin LE = True

  in watchbucket/settings/sys.py
  
  4) In case a transcoding job results in an error, source video is moved to "errors" folder.
  
    
  
 


