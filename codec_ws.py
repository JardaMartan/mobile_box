import websocket
import _thread
import time
import rel
from base64 import b64encode
import ssl
import json
import concurrent.futures
import logging
import sys
import signal
from config import CODEC_CONFIG

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)7s]  [%(module)s.%(name)s.%(funcName)s]:%(lineno)s %(message)s",
    handlers=[
        # logging.FileHandler("/log/debug.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

thread_executor = concurrent.futures.ThreadPoolExecutor()

def sigterm_handler(_signo, _stack_frame):
    "When sysvinit sends the TERM signal, cleanup before exiting."

    logger.info(f"Received signal {_signo}, exiting...")
    
    thread_executor._threads.clear()
    concurrent.futures.thread._threads_queues.clear()
    sys.exit(0)
    
def kill_threads():
    logger.info("Kill threads")
    
    rel.abort()
    
    thread_executor._threads.clear()
    concurrent.futures.thread._threads_queues.clear()
    sys.exit(0)

signal.signal(signal.SIGTERM, sigterm_handler)
signal.signal(signal.SIGINT, sigterm_handler)

class CodecRPCRegister:
    
    def __init__(self, ws):
        ws.on_message = self.handle_rpc_message
        self._ws = ws
        self._msg_sequence = 1
        self._msg_register = {}
        self._feedback_register = {}
        self._feedback_callbacks_temp = {}
        
    def send_rpc_message(self, method, params, callback = None):
        msg = self.create_rpc_message(method, params, callback)
        self._ws.send(json.dumps(msg))
        
    def _feedback_registered(self, msg_id, response):
        logger.info(f"Feedback register response: {response}")
        try:
            callback_reg = self._feedback_callbacks_temp.pop(msg_id)
            self._feedback_register[response["Id"]] = {
                "callback": callback_reg["callback"]
            }
        except KeyError:
            logger.error(f"Feedback callback {response['id']} not registered")
                
    def feedback_subscribe(self, params, callback):
        try:
            msg = self.create_rpc_message("xFeedback/Subscribe", {"Query": params}, self._feedback_registered)
            self._feedback_callbacks_temp[msg["id"]] = {
                "callback": callback
            }
            self._ws.send(json.dumps(msg))
        except Exception as e:
            logger.error(f"Feedback subscribe exception: {e}")
        
    def create_rpc_message(self, method, params, callback):
        self._msg_sequence += 1
        rpc_message = {
            "jsonrpc": "2.0",
            "id": str(self._msg_sequence),
            "method": method,
            "params": params
        }
        try:
            a = self._msg_register[rpc_message["id"]]
            logger.error(f"Message id {rpc_message['id']} already registered")
        except KeyError:
            self._msg_register[rpc_message["id"]] = {
                "message": rpc_message,
                "callback": callback
            }
            return rpc_message
            
    def handle_rpc_message(self, ws, message):
        message = json.loads(message)
        logger.info(f"RPC message: {message}")
        if message.get("method") == "xFeedback/Event":
            logger.debug(f"Feedback event: {message['params']}")
            self._feedback_register[message["params"]["Id"]]["callback"](message["params"])
        else:
            try:
                msg_reg = self._msg_register.pop(message["id"])
                logger.info(f"Handling reponse {message['id']}, RPC register: {self._msg_register}")
                if msg_reg["callback"] is not None:
                    try:
                        msg_reg["callback"](message["id"], message["result"])
                    except Exception as e:
                        logger.error(f"RPC callback exception: {e}")
            except KeyError:
                logger.error(f"Message id {message['id']} already handled")

def on_message(ws, message):
    logger.info(message)

def on_error(ws, error):
    logger.info(error)

def on_close(ws, close_status_code, close_msg):
    logger.info("### closed ###")
    
def codec_status(msg_id, status):
    logger.info(f"Codec info: {status['ProductId']}")
    
def ui_event(event):
    logger.info(f"UI event: {event}")

def codec_requests(ws, interval = 10):
    rpc_reg = CodecRPCRegister(ws)
    # test_req = {'jsonrpc': '2.0', 'id': 101, 'method': 'xGet', 'params': {'Path': ['Status', 'SystemUnit']}}
    try:
        rpc_reg.feedback_subscribe(["Event", "UserInterface", "Extensions"], ui_event)
    except Exception as e:
        logger.error(f"Subscribe exception: {e}")          
    while True:
        # logger.info(f"Codec request: {dir(ws)}")
        try:
            # pass
            rpc_reg.send_rpc_message("xGet", {"Path": ["Status", "SystemUnit"]}, codec_status)
        except Exception as e:
            logger.error(f"RPC exception: {e}")          
        time.sleep(interval)
                
def on_open(ws):
    logger.info("Opened connection")
    try:
        logger.info("Start my loop")
        thread_executor.submit(codec_requests, ws, 5)
    except Exception as e:
        logger.error(f"Thread pool exception: {e}")
            
if __name__ == "__main__":
    websocket.enableTrace(True)
    auth = b64encode(f"{CODEC_CONFIG['username']}:{CODEC_CONFIG['password']}".encode()).decode()
    http_header = {
        "Authorization": f"Basic {auth}"
    }
    
    # ws = websocket.WebSocket(sslopt={"cert_reqs": ssl.CERT_NONE})
    # ws.connect(f"wss://{CODEC_CONFIG['ip']}/ws",
    #     header=http_header
    # )
    # test_req = {'jsonrpc': '2.0', 'id': 101, 'method': 'xGet', 'params': {'Path': ['Status', 'SystemUnit']}}
    # ws.send(json.dumps(test_req))
    # result = json.loads(ws.recv())
    
    wsapp = websocket.WebSocketApp(f"wss://{CODEC_CONFIG['ip']}/ws",
        header=http_header,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close)
    
    wsapp.run_forever(dispatcher=rel, sslopt={"cert_reqs": ssl.CERT_NONE})  # Set dispatcher to automatic reconnection
    # rel.signal(2, rel.abort)  # Keyboard Interrupt
    rel.signal(2, kill_threads)  # Keyboard Interrupt
    rel.dispatch()
