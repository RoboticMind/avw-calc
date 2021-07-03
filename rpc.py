import requests
import json
from typing import List, Union, Any

class RPC:

    def __init__(
            self,
            rpc_user: str,
            rpc_password: str,
            port:int = 15715 #default port is 15715
        ) -> None: 

        self.port:int = port
        
        #boiler plate for a session
        self.session = requests.Session()
        self.session.auth = (rpc_user,rpc_password)

    def call(
            self, 
            method:str, 
            params: Union[str, int, List[Any]] = [], 
            silent_error:bool = False
        ) -> Union[dict, None]:

        url:str = "http://127.0.0.1:" + str(self.port)
        
        if isinstance(params, str) or isinstance(params, int):
            params: List[Any] = [params] #wrap in list if its a string or int

        if len(params) > 0:
            #command with one arg
            payload = json.dumps(
                {
                "jsonrpc":1.0,
                "method": method, 
                "params": params,
                "id":"avw-calc"
                }
            )
        else:
            #no arg command
            payload = json.dumps(
                {
                "jsonrpc":1.0,
                "method": method,
                "id":"avw-calc"
                }
            )
        
        headers = {
                    'content-type':"text/plain", 
                   'cache-control': "no-cache"
                   }
        try:
            response = self.session.post(url, data=payload, headers=headers)
        except Exception as e:
            if not silent_error:
                print("Error: " + str(e))

            return None

        if response.status_code == 401:
            if not silent_error:
                print("Error: unauthorized request. Check that the username and password are correct and that you allow connections from localhost")
            
            return None

        try:
            result = json.loads(response.text)["result"]
        except Exception as e:
            if not silent_error:
                print("Error: " + str(e))
                print(response.text)
            
            return None


        if result == None and not silent_error: 
            print("Error: " + response.text)
        
        return result