# Cisco router and codec integration
This is an example of integration between IOS-XE router (tested on IR1101) and Cisco video codec (RoomKit mini).
It was built for the ruggedized mobile video unit and provides router monitoring and control user interface on the Touch10
of the video codec. This way the user of the video device can for example check the connection quality or
switch from one type of connection to another. The example implements following features:
* color change of the panel button
* show command buttons for the HW/SW version and IP routing table
* periodical update of router CPU and memory utilization

<img src="./images/panel_blend_1.png" width="70%">  
<img src="./images/panel_blend_2.png" width="70%">  

## How it works
