This is an educational project
---

# Scoring API
This API is an HTTP-based scoring service interface. 

## Usage
#### Server-side
API works on python 3.  
```python api.py [-p,--port PORT] [-l,--log LOG_FILE]```  
The above command starts a server at localhost listening on PORT and saving logs to LOG_FILE. 

#### Client-side
Send HTTP POST request to ```http://<host>/method/``` where host - server hostname.   The request body must contain query arguments (see Making requests) 

## Making requests
Requests to the Scoring API must be served over HTTP.
Query arguments must be passed as application/json in the body of the POST method:  
```
{
  "account": "<company name>",
  "login": "<username>",
  "method": "<API method name>",
  "token": "<authentication token>", 
  "arguments": {<method arguments>}
}
```  
* account ‑ string, optional, can be empty
* login ‑ string, required, can be empty
* method ‑ string, required, can be empty
* token ‑ string, required, can be empty
* arguments ‑ JSON object, required, not empty  

(For available methods see Methods)


## Response
The response contains a JSON object, which always has a field "code" that contains 3-digit response code:  
* 200 - OK
* 400 - "Bad Request"
* 403 - "Forbidden"
* 404 - "Not Found"
* 422 - "Invalid Request"
* 500 - "Internal Server Error"

If request was successful it has form  
```
{  
  "code": <response code>,   
  "response": {<response message>}  
}  
```  
аnd the result of the request can be found in the "response" field.

In case of an unsuccessful request  it has form  
```
{  
  "code": <response code>,   
  "error": {<error message>}  
}  
```  
and the errors are explained in the "error" field


## Methods
#### online_score
This method returns a score in range from 0 to 5 for common user or 42 for admin ("login": "ADMIN"):  
```{"code": 200, "score": "<score>"}```

"method" field must be:  
```"method": "online_score"```  
"arguments" field must be JSON object in the form:
```
{  
  "phone": <phone number>,
  "email": "<email>",
  "first_name": "<first name>",
  "last_name": "<last name>",
  "birthday": "<birthday>",
  "gender":  <gender>
}  
```  
* phone - string or integer, optinal, can be empty
* email - string, optinal, can be empty
* first_name - string, optinal, can be empty
* last_name - string, optinal, can be empty
* birthday - string in the form "DD.MM.YYYY", optinal, can be empty
* gender - integers, optinal, can be empty  

At least one pair phone-email, first name-last name, gender-birthday must not be empty.  
Phone must be of length 11 and starts with 7.  
Birthday must be not more than 70 years from now.  
Gender - 0 for unknown, 1 for male, 2 for female.
  
#### clients_interests
This method returns clients interests as a JSON object in the form:  
```
{"<client1>": ["<interest1>", "<interest2>" ...], 
 "<client2>": [...] ...}
```

"method" field must be:  
```"method": "clients_interests"```  
"arguments" field must be JSON object in the form:
```
{  
  "client_ids": <ids list>,
  "date": "<date>",
}  
```  
* client_ids - list of integers, required, not empty
* date - string in the form "DD.MM.YYYY", optinal, can be empty


## Examples
### online_score
Query:
```
{
    "account": "horns&hoofs",
    "login": "h&f",
    "method": "online_score",
    "token": "55cc9ce545bcd144300fe9efc28e65d415b923ebb6be1e19d2750a2c03e80dd209a27954dca045e5bb12418e7d89b6d718a9e35af34e14e1d5bcd5a08f21fc95", 
    "arguments": {  
        "phone": 79101002040,
        "email": "bender@mail.com",
        "first_name": "Ostap",
        "last_name": "Bender",
        "birthday": "01.01.1985",
        "gender":  1
    }  
}
``` 

Responce:
```
{
    "code": 200,
    "response": {"score": 5}
}
```

### clients_interests
Query:
```
{
    "account": "horns&hoofs",
    "login": "h&f",
    "method": "clients_interests",
    "token": "55cc9ce545bcd144300fe9efc28e65d415b923ebb6be1e19d2750a2c03e80dd209a27954dca045e5bb12418e7d89b6d718a9e35af34e14e1d5bcd5a08f21fc95", 
    "arguments": {  
        "client_ids": [1,2,3,4],
        "date": "20.07.2017"
    }  
}
``` 

Responce:
```
{
    "code": 200,
    "response": {
        "1": ["cars", "pets"],
        "2": ["sport", "pets"],
        "3": ["books", "pets"],
        "4": ["hi-tech","music"]
    }
}
```


## Logging
Script outputs all events occurred during the script execution to stdout or to the log file if it is specified.


## Tests 
To perform unit testing, run from command line:  
`python test_api.py`

