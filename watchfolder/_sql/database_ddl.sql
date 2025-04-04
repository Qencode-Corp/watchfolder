CREATE DATABASE IF NOT EXISTS qencode;
USE qencode;

CREATE TABLE IF NOT EXISTS task (
  id int(11) NOT NULL AUTO_INCREMENT,
  token tinytext,
  status tinytext,
  error  INT(11),
  filename tinytext,
  source_url varchar(4000),
  error_description varchar(4000),
  images varchar(4000),
  videos varchar(4000),
  create_datetime timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id)
) ENGINE=InnoDB  DEFAULT CHARSET=utf8;
