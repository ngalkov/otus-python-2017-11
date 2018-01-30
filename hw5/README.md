This is an educational project
---

# VS_Server
This is multithreaded HTTP server. VS stands for 'very simple'. 

## Description
A simple non-blocking HTTP server, written in Python 3.6, that serves static content.  
Supports HEAD and GET requests.  
Uses multithreading to serve more than one client at a time.

## Usage
```python httpd.py -r DOCUMENT_ROOT [-a ADDRESS] [-p PORT] [-w WORKERS_COUNT]```  
Options:  
DOCUMENT_ROOT - path to directory with content  
ADDRESS - an address to listening for connections (Defaults to "localhost")  
PORT - port number (Defaults to 8080)  
WORKERS_COUNT - number of server threads (Defaults to 10)

## Dependencies
Python 3.6 or higher

## Testing
Server passes all the tests from  
```https://github.com/s-stupnikov/http-test-suite```  

## Benchmark
Server started as  
```python httpd.py -r ./tests -w 4```

Apache Benchmark testing command:  
```ab -n 50000 -c 100  http://localhost:8080/```

Test results:  
```
This is ApacheBench, Version 2.3 <$Revision: 1706008 $>
Copyright 1996 Adam Twiss, Zeus Technology Ltd, http://www.zeustech.net/
Licensed to The Apache Software Foundation, http://www.apache.org/

Benchmarking localhost (be patient)
Completed 5000 requests
Completed 10000 requests
Completed 15000 requests
Completed 20000 requests
Completed 25000 requests
Completed 30000 requests
Completed 35000 requests
Completed 40000 requests
Completed 45000 requests
Completed 50000 requests
Finished 50000 requests


Server Software:        VS_Server/0.1
Server Hostname:        localhost
Server Port:            8080

Document Path:          /
Document Length:        19 bytes

Concurrency Level:      100
Time taken for tests:   17.179 seconds
Complete requests:      50000
Failed requests:        0
Total transferred:      8350000 bytes
HTML transferred:       950000 bytes
Requests per second:    2910.45 [#/sec] (mean)
Time per request:       34.359 [ms] (mean)
Time per request:       0.344 [ms] (mean, across all concurrent requests)
Transfer rate:          474.65 [Kbytes/sec] received

Connection Times (ms)
              min  mean[+/-sd] median   max
Connect:        0    0   0.5      0      19
Processing:     8   34   1.7     34      52
Waiting:        8   33   1.6     33      51
Total:         26   34   1.7     34      57

Percentage of the requests served within a certain time (ms)
  50%     34
  66%     35
  75%     35
  80%     35
  90%     36
  95%     37
  98%     40
  99%     42
 100%     57 (longest request)
```
