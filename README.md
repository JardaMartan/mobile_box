# Cisco router and codec integration
This is an example of integration between IOS-XE router (tested on IR1101) and Cisco video codec (RoomKit mini).
It was built for a ruggedized mobile video unit and provides router monitoring and control user interface on the Touch10
of the video codec. This way the user of the video device can for example check the connection quality or
switch from one type of connection to another. The example implements following features:
* color change of the panel button
* show command buttons for the HW/SW version and IP routing table
* periodical update of router CPU and memory utilization

Following technologies / techniques are used:
* [websocket](https://www.cisco.com/c/dam/en/us/td/docs/telepresence/endpoint/api/collaboration-endpoint-software-api-transport.pdf) for two-way communication with the codec API. It provides real-time, easy-to use interface.
* [Restconf]() for router monitoring and configuration changes
* [IOx](https://developer.cisco.com/site/iox/)-hosted Docker image 

<img src="./images/panel_blend_1.png" width="70%">  
<img src="./images/panel_blend_2.png" width="70%">  

## How it works
The mobile box consists of a Webex RoomKit mini or [Room Bar](https://projectworkplace.cisco.com/products/webex-room-bar), [Touch10](https://www.cisco.com/c/en/us/products/collateral/collaboration-endpoints/telepresence-touch/data_sheet_c78-646041.html) or [Navigator](https://projectworkplace.cisco.com/products/cisco-webex-navigator-table-version) and a LTE/Ethernet router.  

<img src="./images/mobile_box_blend_1.jpg" width="70%">  

The application is hosted as a Docker image on the IOS-XE router using [IOx](https://developer.cisco.com/site/iox/). 
Following diagram shows the components and communication protocols:

<img src="./images/topology_1.png" width="70%">  

**Websocket** channel is established in the direction from router to codec and is used both for sending commands to the codec
and for receiving notifications (feedback) from codec - for example touch interface or call events.  
**Restconf** is used to get an information from the router. It can also be used to send configuration changes
or other commands to the router.

## Restconf
In order to create Restconf request [Cisco YANG Suite](https://developer.cisco.com/yangsuite/) is an essential tool.
It can get a list of YANG models supported by the specific router type and IOS version. Then the user can explore the
YANG models and prepare the Restconf query and its parameters. [Postman](https://www.postman.com/) can be then
used for Restconf query testing. 
