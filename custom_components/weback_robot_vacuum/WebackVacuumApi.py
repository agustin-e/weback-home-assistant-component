import asyncio
import websocket
import websockets
import threading
import time
import json
import logging
import hashlib 
import httpx

_LOGGER = logging.getLogger(__name__)

AUTH_URL = "https://user.grit-cloud.com/prod/oauth"

class WebackVacuumApi:

    def __init__(self, user, password, region):                
        _LOGGER.debug("WebackVacuumApi __init__")
        self.update_callback = self.null_callback
        self.user = user
        self.password = password
        self.region = region
        self.ws = websocket
        self.authorization = "Basic KG51bGwpOihudWxsKQ=="
        self.socket_state = "CLOSE"

    def clone(self):

        my_clone = WebackVacuumApi(
            self.user, 
            self.password,
            self.region,
        )

        my_clone.jwt_token   = self.jwt_token
        my_clone.region_name = self.region_name
        my_clone.wss_url   = self.wss_url
        my_clone.api_url   = self.api_url

        return my_clone


    async def login(self):
        data = {
            "payload": {
                "opt": "login",
                "pwd": hashlib.md5(self.password.encode()).hexdigest()
            },
            "header": {
                "language" : "es",
                "app_name" : "WeBack",
                "calling_code" : "00" + self.region,
                "api_version" : "1.0",
                "account" : self.user,
                "client_id" : "yugong_app"
            }
        }

        _LOGGER.debug("LOG URL: " + AUTH_URL)
        _LOGGER.debug(data)

        
        t = httpx.Timeout(30.0, connect=90.0)
        async with httpx.AsyncClient(timeout=t) as client:
            r = await client.post(AUTH_URL, json=data)      
            _LOGGER.debug(r)

            if r.status_code == 200:
                jsonResponse = r.json()
                if jsonResponse['msg'] == 'success':                
                    _LOGGER.debug("WebackVacuumApi login sucessful - Token: " + jsonResponse['data']['jwt_token'])

                    self.jwt_token   = jsonResponse['data']['jwt_token']
                    self.region_name = jsonResponse['data']['region_name']
                    self.wss_url     = jsonResponse['data']['wss_url']
                    self.api_url     = jsonResponse['data']['api_url']
                else:
                    _LOGGER.error("WebackVacuumApi can't login (2) - verify user/password/region")
            else:
                _LOGGER.error("WebackVacuumApi can't login - verify user/password/region")
        

    def null_callback(self, message):
        _LOGGER.debug("WebackVacuumApi null_callback: ", message)


    async def robot_list(self):

        _LOGGER.debug("WebackVacuumApi - robot list")
        data = {"opt": "user_thing_list_get"}
        authHeaders = {'Token': self.jwt_token, 'Region': self.region_name}

        async with httpx.AsyncClient() as client:
            r = await client.post(self.api_url, json=data, headers=authHeaders) 
        
            if r.status_code == 200:
                jsonResponse = r.json()

                if jsonResponse['msg'] == 'success':
                    _LOGGER.debug("WebackVacuumApi robot list OK", jsonResponse['data']['thing_list'])
                    return jsonResponse['data']['thing_list']
                else:
                    return False

    
    async def connect_wss(self):
        _LOGGER.debug("WebackVacuumApi connect_wss")

        try:
            websocket.enableTrace(True)
            self.ws = websocket.WebSocketApp(self.wss_url, header={"Authorization": self.authorization,
                                                                "region": self.region_name,
                                                                "token": self.jwt_token,
                                                                "Connection": "keep-alive, Upgrade",
                                                                "handshakeTimeout": "10000"},
                                            on_message = self.on_message,
                                            on_close   = self.on_close,
                                            on_open    = self.on_open,
                                            on_error   = self.on_error)

            self.wst = threading.Thread(target=self.ws.run_forever)
            self.wst.start()

            if self.wst.is_alive():
                _LOGGER.debug("> WssHandle thread iniciado OK")
            else:
                _LOGGER.debug("> WssHandle thread error al iniciar")

            for i in range(20):                
                _LOGGER.debug("WSS esperando a conectar...", i)
                if self.socket_state == "OPEN":
                    _LOGGER.debug("WSS conexión establecida")
                    return True
                asyncio.sleep(0.5)

            _LOGGER.debug("WSS espera fallida")
            return False

        except Exception as e:
            self.socket_state = "ERROR"
            _LOGGER.debug("WSS error durante la apertura del socket", e)
            return False

    def on_error(self, ws, error):
        _LOGGER.debug("WebackVacuumApi ERROR", error)        
        ws.close()
        self.socket_state = "ERROR"

    def on_close(self, ws, close_status_code, close_msg):
        _LOGGER.debug("WebackVacuumApi CLOSE")
        ws.close()
        self.socket_state = "CLOSE"
        _LOGGER.debug("WSS | socket cerrado - status_code", close_status_code, close_msg)

    def on_open(self, ws):
        _LOGGER.debug("WebackVacuumApi socket OPEN")
        self.socket_state = "OPEN"
        _LOGGER.debug("WSS conexion establecida!")

    def on_message(self, ws, message):
        _LOGGER.debug("WebackVacuumApi recibe mensaje por socket", message)
        message = json.loads(message)
        if message["notify_info"] == "thing_status_update":
            self.update_callback(message["thing_status"])

    async def send_message_to_cloud(self, json_message):
        _LOGGER.debug("WebackVacuumApi.send_message_to_cloud", json_message)

        if self.socket_state != "OPEN":
            _LOGGER.debug("WebackVacuumApi intento conectar - socket: ", self.socket_state)
            await self.connect_wss()

        if self.socket_state == "OPEN":
            _LOGGER.debug(">> WSS enviando mensaje", json_message)            

            try:
                self.ws.send(json_message)
            except websocket.WebSocketConnectionClosedException as e:
                print('Socket closed when trying to send message to cloud')
                self.socket_state = "CLOSE"
            
        else:
            if await self.connect_wss():
                logging.debug("# state WSS OK-RECO (send mess)")
                
                try:
                    self.ws.send(json_message)
                except websocket.WebSocketConnectionClosedException as e:
                    print('Socket closed when trying to send message to cloud')
                    self.socket_state = "CLOSE"

            else:
                logging.debug("# state WSS NOK (failed)")            
            
    async def send_command(self, thing_name, sub_type, key, value):
        _LOGGER.debug("WebackVacuumApi.send_command", thing_name, key, value)
        payload = {
            "topic_name": "$aws/things/"+ thing_name +"/shadow/update",
            "opt": "send_to_device",
            "sub_type": sub_type,
            "topic_payload": {'state': {
                                    key: value
                                }
                            },
            "thing_name": thing_name,
        }
        
        json_message = str( payload ).replace("'", '"')
        await self.send_message_to_cloud( json_message )
        

    async def update_status(self, thing_name, sub_type):        
        _LOGGER.debug("WebackVacuumApi.get_update", thing_name)
        payload = {
            "opt": "thing_status_get",
            "sub_type": sub_type,            
            "thing_name": thing_name,
        }

        json_message = str( payload ).replace("'", '"')
        await self.send_message_to_cloud( json_message )

    def register_update_callback(self, callback):
        self.update_callback = callback


    # goto point
    async def goto_command(self, thing_name, sub_type, point: str):
        _LOGGER.debug("*** goto_command (point) location: " + point)
        
        payload = {
            "topic_name": "$aws/things/"+ thing_name +"/shadow/update",
            "opt": "send_to_device",
            "sub_type": sub_type,
            "topic_payload": {'state': {
                                    'working_status': 'PlanningLocation',
                                    'goto_point': "@xy@"
                                }
                            },
            "thing_name": thing_name,
        }

        _LOGGER.debug(payload)        
        json_message = str( payload ).replace("'", '"').replace("\"@xy@\"", point)

        _LOGGER.debug(json_message)
        await self.send_message_to_cloud( json_message )


        # sync
        payload = {
            "opt": "sync_thing",
            "sub_type": sub_type,
            "thing_name": thing_name,
        }

        _LOGGER.debug(payload)
        
        json_message = str( payload ).replace("'", '"')

        _LOGGER.debug(json_message)
        await self.send_message_to_cloud( json_message )



    # clean rectangle
    async def clean_rectangle_command(self, thing_name, sub_type, rectangle: str):
        _LOGGER.debug("*** clean_rectangle_command (rectangle) location: " + rectangle)
        
        payload = {
            "topic_name": "$aws/things/"+ thing_name +"/shadow/update",
            "opt": "send_to_device",
            "sub_type": sub_type,
            "topic_payload": {'state': {
                                    'working_status': 'PlanningRect',
                                    'virtual_rect_info': "@rectangle@"
                                }
                            },
            "thing_name": thing_name,
        }

        _LOGGER.debug(payload)        
        json_message = str( payload ).replace("'", '"').replace("\"@rectangle@\"", rectangle)

        _LOGGER.debug(json_message)
        await self.send_message_to_cloud( json_message )


        # sync
        payload = {
            "opt": "sync_thing",
            "sub_type": sub_type,
            "thing_name": thing_name,
        }

        _LOGGER.debug(payload)
        
        json_message = str( payload ).replace("'", '"')

        _LOGGER.debug(json_message)
        await self.send_message_to_cloud( json_message )
