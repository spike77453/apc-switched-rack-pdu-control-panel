from flask import Flask

from .jinja2_hash_filter import get_hash

app = Flask(__name__, instance_relative_config=True)
app.config.from_mapping(
    # a default list of PDUs that should be overridden by instance config
    APC_PDUS = [],
)
app.config.from_envvar('APC_PDU_SETTINGS', silent=True)
app.config.from_pyfile('config.py', silent=True)
app.jinja_env.filters['hash'] = get_hash

import apc_switched_rack_pdu_control_panel.views
