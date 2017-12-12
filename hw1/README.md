This is an educational project
---
# Log analyzer
This is a command line tool that parses nginx log file, collects request time statistics for every unique url and  determines urls with the highest total request time.

## DESCRIPTION
Script scans (by default) directory `./log` looking for files with names like `nginx-access-ui.log-YYYYMMDD` or `nginx-access-ui.log-YYYYMMDD.gz` where YYYYMMDD - log date. Script selects and analyzes file with the latest YYYYMMDD date. Log file should have the following format (see [nginx log format](http://nginx.org/en/docs/http/ngx_http_log_module.html#log_format)):
 
````$remote_addr $remote_user $http_x_real_ip [$time_local] "$request" $status $body_bytes_sent "$http_referer" "$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" $request_time````
   
Script creates in directory `./reports` report file `report-YYYY.DD.MM.html` if the file with such name doesn't already exist (YYYY.DD.MM the same as in log name). Report contains 1000 unique urls with the highest total request time and has following fields:

```
url: unique url  
count: number of requests for url  
count_perc: number of requests percentile for url   
time_avg: average request time  
time_max: maximum request time  
time_sum: sum of request time  
time_med: median request time  
time_perc: time percentile for url
```

Script outputs all events occurred during the script execution to stdout or to the log file if it is specified in the corfig.  
If there are no errors script creates file `./log_analyzer.ts` with current timestamp.

## USAGE
`python log_analyzer.py [--config FILE]`  
Optional argument `--congig` sets a path to a custom config file.

There must be a report template `./report.html` and config file `./log_analyzer.conf` or config file must be specified with `--config` argument.

## CONFIGURATION
### Default configuration:  
Log files directory - `./log`  
Reports directory - `./reports`  
Number of urls in the report - `1000`

Default parameters can be overridden with custom values. Script loads config at startup from `log_analyzer.conf` by default or from custom config file if `--config` argument presents. 
Config parameters are:  
* REPORT_SIZE - Number of urls in the report  
* LOG_DIR - directory with nginx log files  
* REPORT_DIR - directory to store report file  
* LOGGING - filename to write monitoring log output

Config file should have section [MAIN] at first line.

Example config:  
```   
[MAIN]
REPORT_SIZE : 1234  
LOG_DIR : ./path/to/log/dir  
REPORT_DIR : ./path/to/report/dir  
LOGGING : ./logname.log   
```

## Tests
A test suite is provided with complete environment (`./tests` folder).  
To perform tests, run from command line:  
`python ./test_log_analyzer.py`

