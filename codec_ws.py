import sys
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)7s]  [%(module)s.%(name)s.%(funcName)s]:%(lineno)s %(message)s",
    handlers=[
        # logging.FileHandler("/log/debug.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

import websocket
import _thread
import time
import rel
from base64 import b64encode
import ssl
import json
import signal
from config import CODEC_CONFIG, ROUTER_CONFIG, TESTING
from codec_ui import ROUTER_PANEL
import socket, struct
from datetime import datetime
import requests

router_ip = None # see TESTING in config.py and codec_requests()

logger = logging.getLogger(__name__)

MAX_MSG_SEQUENCE = 4096
class CodecRPCRegister:
    """
    Communicate with Cisco codec via websocket
    See the guide: https://www.cisco.com/c/dam/en/us/td/docs/telepresence/endpoint/api/collaboration-endpoint-software-api-transport.pdf
    Latest version can be found here: https://www.cisco.com/c/en/us/support/collaboration-endpoints/spark-room-kit-series/products-command-reference-list.html
    """
    
    def __init__(self, ws):
        """
        Initialize the CodecRPCRegister object
        
        Parameters:
            ws: websocket object
        """
        
        ws.on_message = self.handle_rpc_message
        self._ws = ws
        self._msg_sequence = 1
        self._msg_register = {}
        self._feedback_register = {}
        self._feedback_callbacks_temp = {}
        
    def send_rpc_message(self, method, params, callback = None):
        """
        Send message to the codec via websocket
        
        Parameters:
            method (str): operation and object xPath (for example: "xCommand/UserInterface/Extensions/Widget/SetValue")
            params (dict): parameters
            callback (function): callback function to be called after the response is received,
                the function is called in the form: callback(codec_rpc, message_id, message_result)
        """
        
        msg = self.create_rpc_message(method, params, callback)
        self._ws.send(json.dumps(msg))
        
    def _feedback_registered(self, codec_rpc, msg_id, response):
        """
        Callback function for feedback register (xFeedback/Subscribe) method.
        As a result, the callback function provided in feedback_subscribe() is associated
        with the feedback id.
        
        Parameters:
            codec_rpc: CodecRPCRegister object
            msg_id (str): message id
            response (dict): response from the codec
        """
        
        logger.info("Feedback register response: {}".format(response))
        try:
            callback_reg = codec_rpc._feedback_callbacks_temp.pop(msg_id)
            codec_rpc._feedback_register[response["Id"]] = {
                "callback": callback_reg["callback"]
            }
        except KeyError:
            logger.error("Feedback callback {} not registered".format(response['id']))
                
    def feedback_subscribe(self, params, callback):
        """
        Set callback for codec feedback. Each feedback registration has its own id.
        Multiple feedback registrations are possible, each with its own callback function.
        
        Parameters:
            params (str): xPath for which we want to receive a feedback
            callback: callback function, it's called in the form: callback(codec_rpc, reponse_parameters)
        """
        
        try:
            msg = self.create_rpc_message("xFeedback/Subscribe", {"Query": params}, self._feedback_registered)
            self._feedback_callbacks_temp[msg["id"]] = {
                "callback": callback
            }
            self._ws.send(json.dumps(msg))
        except Exception as e:
            logger.error("Feedback subscribe exception: {}".format(e))
        
    def create_rpc_message(self, method, params, callback):
        """
        Create a codec RPC message and register a callback function for handling the response.
        Each RPC message has its own id and the callback is associated with the id.
        
        Parameters:
            method (str): operation and object xPath (for example: "xCommand/UserInterface/Extensions/Widget/SetValue")
            params (str): parameters
            callback: callback function
        """
        
        self._msg_sequence += 1
        if self._msg_sequence > MAX_MSG_SEQUENCE:
            self._msg_sequence = 1
        rpc_message = {
            "jsonrpc": "2.0",
            "id": str(self._msg_sequence),
            "method": method,
            "params": params
        }
        try:
            a = self._msg_register[rpc_message["id"]]
            logger.error("Message id {} already registered".format(rpc_message['id']))
        except KeyError:
            self._msg_register[rpc_message["id"]] = {
                "message": rpc_message,
                "callback": callback
            }
            return rpc_message
            
    def handle_rpc_message(self, ws, message):
        """
        Handle the RPC message. Based on the RPC message id, the callback function is called.
        There are two possible callbacks:
        1. asynchronous event associated with feedback registration, the callback is called in the form of
            callback(codec_rpc, message_parameters)
        2. response to the previous RPC request, the callback is called in the form of
            callback(codec_rpc, message_id, parameters). In this case the callback is removed from
            the pool of callback functions - each message id is handled only once.
        
        Parameters:
            ws: websocket object
            message (str): JSON representation of the RPC response
        """
        
        message = json.loads(message)
        logger.info("RPC message: {}".format(message))
        if message.get("method") == "xFeedback/Event":
            logger.debug("Feedback event: {}".format(message['params']))
            self._feedback_register[message["params"]["Id"]]["callback"](self, message["params"])
        else:
            try:
                msg_reg = self._msg_register.pop(message["id"])
                logger.info("Handling reponse {}, RPC register: {}".format(message['id'], self._msg_register))
                if msg_reg["callback"] is not None:
                    try:
                        msg_reg["callback"](self, message["id"], message["result"])
                    except Exception as e:
                        logger.error("RPC callback exception: {}".format(e))
            except KeyError:
                logger.error("Message id {} already handled".format(message['id']))

def on_message(ws, message):
    """
    Dummy function from the example
    """
    logger.info(message)

def on_error(ws, error):
    """
    Dummy function from the example
    """
    logger.info(error)

def on_close(ws, close_status_code, close_msg):
    """
    Dummy function from the example
    """
    logger.info("### closed ###")
    
def codec_status(msg_id, status):
    """
    Dummy function
    """
    logger.info("Codec info: {}".format(status['ProductId']))
    
def ui_event(codec_rpc, event):
    """
    Handle Event/UserInterface/Extensions event. The function is set as a callback for xFeedback/Subscribe.
    """
    logger.info("UI event: {}".format(event))
    # {'Event': {'UserInterface': {'Extensions': {'Widget': {'Action': {'Type': 'pressed', 'Value': '2', 'WidgetId': 'widget_1', 'id': 1}, 'id': 1}, 'id': 1}, 'id': 1}}, 'Id': 0}
    try:
        action = event["Event"]["UserInterface"]["Extensions"]["Widget"]["Action"]
        if action["Type"] == "clicked":
            try:
                if action["WidgetId"] == "sh_ver":
                    sh_ver_res = get_router_version(router_ip, ROUTER_CONFIG["username"], ROUTER_CONFIG["password"])
                    codec_rpc.send_rpc_message("xCommand/UserInterface/Extensions/Widget/SetValue",
                        {"WidgetId": "show_result_1", "Value": sh_ver_res})
                elif action["WidgetId"] == "sh_ip_ro":
                    routing = get_routing_table(router_ip, ROUTER_CONFIG["username"], ROUTER_CONFIG["password"])
                    route_list = []
                    for route_rec in routing:
                        fwd_list = route_rec['fwd-list']
                        next_hops = []
                        for fwd in fwd_list:
                            next_hops.append(fwd["fwd"])
                        next_str = ",".join(next_hops)
                        res = "{}/{} -> {}".format(route_rec['prefix'], route_rec['mask'], next_str)
                        route_list.append(res)
                    codec_rpc.send_rpc_message("xCommand/UserInterface/Extensions/Widget/SetValue",
                        {"WidgetId": "show_result_1", "Value": "\n".join(route_list)})
            except Exception as e:
                logger.info("UI execute exception: {}".format(e))
                
    except KeyError:
        logger.info("Action not found in Event")

def codec_requests(ws, interval = 10):
    """
    Thread for communication with the codec. Started after the websocket connection is established.
    Workflow:
    1. push panel specification file to the codec (create or update it)
    2. start a router polling thread
    3. run an infinite loop which can for example talk to codec or do other things
    """
    
    global router_ip
    
    rpc_reg = CodecRPCRegister(ws)
    
    setup_router_panel(rpc_reg, ROUTER_PANEL)
    
    # test_req = {'jsonrpc': '2.0', 'id': 101, 'method': 'xGet', 'params': {'Path': ['Status', 'SystemUnit']}}
    try:
        rpc_reg.feedback_subscribe(["Event", "UserInterface", "Extensions"], ui_event)
    except Exception as e:
        logger.error("Subscribe exception: {}".format(e))    
        
    # see config.py - if not testing, the router_ip is a default gateway of the docker
    if TESTING["active"]:
        router_ip = TESTING["router_ip"]
    else:
        router_ip = get_default_gateway_linux()

    _thread.start_new_thread(periodic_router_info, (rpc_reg, router_ip, ROUTER_CONFIG["username"], ROUTER_CONFIG["password"]))      

    while True:
        # logger.info("Codec request: {}".format(dir(ws)))
        try:
            # place periodic updates towards codec (e.g. router status) here
            # another option is a periodic query of codec status, registration request, etc.
            pass
            # rpc_reg.send_rpc_message("xGet", {"Path": ["Status", "SystemUnit"]}, codec_status)
        except Exception as e:
            logger.error("RPC exception: {}".format(e))          
        time.sleep(interval)
        
def show_router_panel(codec_rpc, *args):
    """
    Pop-up the router control panel on the codec's touch interface.
    
    Parameters:
        codec_rpc: CodecRPCRegister object for communication with the codec
    """
    
    try:
        logger.info("Show router panel")
        codec_rpc.send_rpc_message("xCommand/UserInterface/Extensions/Panel/Open",
            {"PanelId": "router", "PageId": "page_rtr_info"})
    except Exception as e:
        logger.error("Panel show exception: {}".format(e))
                
def setup_router_panel(codec_rpc, panel = ROUTER_PANEL):
    """
    Send a panel definition to the codec and pop it up.
    
    Parameters:
        codec_rpc: CodecRPCRegister object for communication with the codec
        panel (str): XML definition of the panel, see codec_ui.py
    """
    
    try:
        logger.info("Setup router panel")
        codec_rpc.send_rpc_message("xCommand/UserInterface/Extensions/Panel/Save",
            {"PanelId": "router", "body": ROUTER_PANEL}, show_router_panel)
    except Exception as e:
        logger.error("Panel setup exception: {}".format(e))
        
def periodic_router_info(codec_rpc, router_ip, username, password, interval = 10):
    """
    Inifinite loop which periodically polls the router and sends the information to the codec's touch panel.
    
    Parameters:
        codec_rpc: CodecRPCRegister object for communication with the codec
        router_ip (str): router IP address
        username (str): router username
        password (str): router password
    """
    
    logger.info("Starting perodic router info, ip: {}, interval: {}".format(router_ip, interval))
    while True:
        try:
            mem_usage = get_memory_usage(router_ip, username, password)
            codec_rpc.send_rpc_message("xCommand/UserInterface/Extensions/Widget/SetValue",
                {"WidgetId": "rtr_mem_usage", "Value": mem_usage})
            cpu_usage = get_cpu_usage(router_ip, username, password)
            codec_rpc.send_rpc_message("xCommand/UserInterface/Extensions/Widget/SetValue",
                {"WidgetId": "rtr_cpu_usage", "Value": cpu_usage})
            now = datetime.now().isoformat()[:-7]
            codec_rpc.send_rpc_message("xCommand/UserInterface/Extensions/Widget/SetValue",
                {"WidgetId": "rtr_update", "Value": now})
        except Exception as e:
            logger.error("Periodic router exception: {}".format(e))
            
        time.sleep(interval)       
                
def on_open(ws):
    """
    Called after successful websocket connection. Starts the codec_requests() thread.
    
    Parameters:
        ws: websocket object
    """
    
    logger.info("Opened connection")
    try:
        logger.info("Start my loop")
        _thread.start_new_thread(codec_requests, (ws, 5))
    except Exception as e:
        logger.error("Thread pool exception: {}".format(e))
        
def get_default_gateway_linux():
    """Read the default gateway directly from /proc.
    source: https://stackoverflow.com/questions/2761829/python-get-default-gateway-for-a-local-interface-ip-address-in-linux
    
    Returns:
        str: IP address of the default gateway
    """
    
    with open("/proc/net/route") as fh:
        for line in fh:
            fields = line.strip().split()
            if fields[1] != '00000000' or not int(fields[3], 16) & 2:
                # If not default route or not RTF_GATEWAY, skip it
                continue

            return socket.inet_ntoa(struct.pack("<L", int(fields[2], 16)))
            
def restconf_query(router_ip, username, password, module_name, xpath):
    """
    Run a restconf GET request.
    
    Parameters:
        router_ip (str): router IP address
        username (str): router username
        password (str): router password
        module_name (str): restconf module name
        xpath (str): xPath or other restconf parameters for the module query
    """
    
    router_url = "https://{}/restconf/data/{}:{}".format(router_ip, module_name, xpath)
    logger.info("Restconf URL: {}".format(router_url))
    headers = {
        "Accept": "application/yang-data+json"
    }
    auth = (username, password)
    rf_res = requests.get(router_url, headers = headers, auth = auth, verify = False)
    logger.info("Response code: {}".format(rf_res.status_code))
    
    if rf_res.ok:
        return rf_res.json()

def get_memory_usage(router_ip, username, password):
    """
    Get IOS-XE memory usage and format it to a string.
    
    Parameters:
        router_ip (str): router IP address
        username (str): router username
        password (str): router password
        
    Returns:
        string: formatted result
    """
    
    mem_stat = restconf_query(router_ip, username, password, "Cisco-IOS-XE-memory-oper", "memory-statistics/memory-statistic")
    if mem_stat:
        for mem in mem_stat['Cisco-IOS-XE-memory-oper:memory-statistic']:
            if mem["name"].lower() == "processor":
                usage = "used: {}, free: {}".format(mem["used-memory"], mem["free-memory"])
                return usage

def get_cpu_usage(router_ip, username, password):
    """
    Get IOS-XE CPU usage and format it to a string.
    
    Parameters:
        router_ip (str): router IP address
        username (str): router username
        password (str): router password
        
    Returns:
        string: formatted result
    """

    cpu_stat = restconf_query(router_ip, username, password, "Cisco-IOS-XE-process-cpu-oper", "cpu-usage/cpu-utilization?fields=five-seconds;one-minute;five-minutes")
    cpu_info = cpu_stat.get("Cisco-IOS-XE-process-cpu-oper:cpu-utilization")
    if cpu_info:
        usage = "5s: {:2d}%, 1m: {:2d}%, 5m: {:2d}%".format(cpu_info["five-seconds"], cpu_info["one-minute"], cpu_info["five-minutes"])
        return usage
        
def get_routing_table(router_ip, username, password):
    """
    Get IOS-XE routing table.
    
    Parameters:
        router_ip (str): router IP address
        username (str): router username
        password (str): router password
        
    Returns:
        list: list of IP routes
    """

    routing_res = restconf_query(router_ip, username, password, "Cisco-IOS-XE-native", "native/ip/route")
    routing_data = routing_res["Cisco-IOS-XE-native:route"]["ip-route-interface-forwarding-list"]
    return routing_data
    
def get_router_version(router_ip, username, password):
    """
    Get IOS-XE router hostname, IOS version and hardware model and format it to a string.
    
    Parameters:
        router_ip (str): router IP address
        username (str): router username
        password (str): router password
        
    Returns:
        string: formatted result
    """

    ios_info_res = restconf_query(router_ip, username, password, "Cisco-IOS-XE-native", "native?fields=version;hostname")
    ios_info = ios_info_res["Cisco-IOS-XE-native:native"]
    hw_info_res = restconf_query(router_ip, username, password, "Cisco-IOS-XE-device-hardware-oper", "device-hardware-data/device-hardware/device-inventory?fields=hw-type;part-number")
    hw_info = hw_info_res["Cisco-IOS-XE-device-hardware-oper:device-inventory"]
    model = "unknown"
    for module in hw_info:
        if module["hw-type"] == "hw-type-chassis":
            model = module["part-number"]
    result = "{}, hw: {}, sw: {}".format(ios_info["hostname"], model, ios_info["version"])
    return result
            
if __name__ == "__main__":
    # just for testing & logging
    router_ip = get_default_gateway_linux()
    logger.info("Router IP: {}".format(router_ip))
    
    websocket.enableTrace(True)
    auth = b64encode("{}:{}".format(CODEC_CONFIG['username'], CODEC_CONFIG['password']).encode()).decode()
    http_header = {
        "Authorization": "Basic {}".format(auth)
    }
    
    # ws = websocket.WebSocket(sslopt={"cert_reqs": ssl.CERT_NONE})
    # ws.connect("wss://{}/ws".format(CODEC_CONFIG['ip']),
    #     header=http_header
    # )
    # test_req = {'jsonrpc': '2.0', 'id': 101, 'method': 'xGet', 'params': {'Path': ['Status', 'SystemUnit']}}
    # ws.send(json.dumps(test_req))
    # result = json.loads(ws.recv())
    
    # start a websocket connection. SSL didn't work in Python 3.5. Later versions are OK, so "wss:" is possible.
    wsapp = websocket.WebSocketApp("ws://{}/ws".format(CODEC_CONFIG['ip']),
        header=http_header,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close)

    # SSL version of the websocket start
    # wsapp.run_forever(dispatcher=rel, sslopt={"cert_reqs": ssl.CERT_NONE})  # Set dispatcher to automatic reconnection

    # connect and maintain websocket connection
    wsapp.run_forever(dispatcher=rel)  # Set dispatcher to automatic reconnection
    rel.signal(2, rel.abort)  # Keyboard Interrupt
    rel.dispatch()
