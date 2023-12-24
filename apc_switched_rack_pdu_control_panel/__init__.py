from flask import Flask

app = Flask(__name__, instance_relative_config=True)
app.config.from_mapping(
    # a default list of PDUs that should be overridden by instance config
    APC_PDUS = [],
)
app.config.from_envvar('APC_PDU_SETTINGS', silent=True)
app.config.from_pyfile('config.py', silent=True)

import apc_switched_rack_pdu_control_panel.views
