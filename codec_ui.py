# definition of the codec touch screen control panel
# see https://roomos.cisco.com/docs/UiExtensions.md
ROUTER_PANEL = """
<Extensions>
  <Version>1.8</Version>
  <Panel>
    <Order>5</Order>
    <PanelId>router_mgmt</PanelId>
    <Origin>local</Origin>
    <Type>Home</Type>
    <Icon>Lightbulb</Icon>
    <Name>Router</Name>
    <ActivityType>Custom</ActivityType>
    <Page>
      <Name>Router Control</Name>
      <Row>
        <Name>Tlačítka</Name>
        <Widget>
          <WidgetId>sh_ver</WidgetId>
          <Name>show version</Name>
          <Type>Button</Type>
          <Options>size=2</Options>
        </Widget>
        <Widget>
          <WidgetId>sh_ip_ro</WidgetId>
          <Name>show ip route</Name>
          <Type>Button</Type>
          <Options>size=2</Options>
        </Widget>
        <Widget>
          <WidgetId>show_result_1</WidgetId>
          <Name>Text 1</Name>
          <Type>Text</Type>
          <Options>size=4;fontSize=small;align=left</Options>
        </Widget>
      </Row>
      <PageId>page_rtr_control</PageId>
      <Options>hideRowNames=1</Options>
    </Page>
    <Page>
      <Name>Router Info</Name>
      <Row>
        <Name>CPU Usage</Name>
        <Widget>
          <WidgetId>rtr_cpu_usage</WidgetId>
          <Name>Text</Name>
          <Type>Text</Type>
          <Options>size=4;fontSize=normal;align=left</Options>
        </Widget>
      </Row>
      <Row>
        <Name>Memory Usage</Name>
        <Widget>
          <WidgetId>rtr_mem_usage</WidgetId>
          <Name>Text</Name>
          <Type>Text</Type>
          <Options>size=4;fontSize=normal;align=left</Options>
        </Widget>
      </Row>
      <Row>
        <Name>Last Update</Name>
        <Widget>
          <WidgetId>rtr_update</WidgetId>
          <Name>Text</Name>
          <Type>Text</Type>
          <Options>size=4;fontSize=normal;align=left</Options>
        </Widget>
      </Row>
      <PageId>page_rtr_info</PageId>
      <Options/>
    </Page>
  </Panel>
</Extensions>
"""
