## APC Switched Rack PDU Control Panel
A Python/Flask based reimplementation of [disisto's Control Panel](https://github.com/disisto/apc-switched-rack-pdu-control-panel) to control multiple APC Switched Rack PDUs via SNMPv3. A single panel to switch (on, off, restart) the attached devices between different states.

![](https://github.com/spike77453/apc-switched-rack-pdu-control-panel/blob/python/img/0_apc_pdu_control_panel.gif?raw=true)

Check https://github.com/disisto/apc-switched-rack-pdu-control-panel/wiki for details on how to configure the PDU

---

## Requirements
+ APC Switched Rack PDU(s) with enabled SNMPv3 
  * Tested with APC Switched Rack PDU [AP7920](https://www.apc.com/shop/my/en/products/Rack-PDU-Switched-1U-12A-208V-10A-230V-8-C13/P-AP7920) and [AP7921](https://www.apc.com/shop/my/en/products/Rack-PDU-Switched-1U-12A-208V-10A-230V-8-C13/P-AP7921) on EOL firmware `v3.9.2`
  * Tested with APC Switched Rack PDU [AP7920B](https://www.apc.com/shop/my/en/products/Rack-PDU-Switched-1U-12A-208V-10A-230V-8-C13/P-AP7920B) on latest firmware `v6.5.6`

---

## Quick Install

### Run locally
```
pip install apc_switched_rack_pdu_control_panel
curl -o config.py https://raw.githubusercontent.com/spike77453/apc-switched-rack-pdu-control-panel/python/instance/config.py.example
APC_PDU_SETTINGS=/absolute/path/to/config.py flask --app apc_switched_rack_pdu_control_panel run
```

### Run as WSGI app
```
pip install apc_switched_rack_pdu_control_panel
curl -o config.py https://raw.githubusercontent.com/spike77453/apc-switched-rack-pdu-control-panel/python/instance/config.py.example
APC_PDU_SETTINGS=/absolute/path/to/config.py gunicorn 'apc_switched_rack_pdu_control_panel:app'
```

### Supplying configuration data via flask instance folder

Altnatively, loading configuration settings from a [flask instance folder](https://flask.palletsprojects.com/en/3.0.x/config/#instance-folders) is supported as well:

```
mkdir -p $PREFIX/var/apc_switched_rack_pdu_control_panel-instance
cd $PREFIX/var/apc_switched_rack_pdu_control_panel-instance
curl -o config.py https://raw.githubusercontent.com/spike77453/apc-switched-rack-pdu-control-panel/python/instance/config.py.example
```

Configuration settings supplied via an instance folder always take precedence over configuration data supplied via the `APC_PDU_SETTINGS` environment variable.

---
This project is not affiliated with [APC by Schneider Electric](https://www.apc.com/).  
All mentioned trademarks are the property of their respective owners.
