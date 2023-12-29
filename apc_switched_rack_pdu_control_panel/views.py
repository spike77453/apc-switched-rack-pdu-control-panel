import datetime
from pprint import pformat

from easysnmp import Session
from flask import abort, render_template, request

from apc_switched_rack_pdu_control_panel import app

from .forms import SingleOutletForm, OutletForm, PDURenameForm

rPDUIdentName                  = '1.3.6.1.4.1.318.1.1.12.1.1.0'
rPDUOutletDevCommand           = '1.3.6.1.4.1.318.1.1.12.3.1.1.0'
rPDUOutletControlOutletCommand = '1.3.6.1.4.1.318.1.1.12.3.3.1.1.4'
rPDUOutletStatusIndex          = '1.3.6.1.4.1.318.1.1.12.3.5.1.1.1'
rPDUOutletStatusOutletName     = '1.3.6.1.4.1.318.1.1.12.3.5.1.1.2'
rPDUOutletStatusOutletState    = '1.3.6.1.4.1.318.1.1.12.3.5.1.1.4'

outlet_state_dict = {
    "1": "ON",
    "2": "OFF",
    "3": "REBOOT"
}

def find_apc_pdu_by_hostname(hostname):
    for apc_pdu in app.config['APC_PDUS']:
        if apc_pdu['hostname'] == hostname:
            return apc_pdu
    return None


def walk_outlets(session):
    outlets = []
    outlet_indices = session.walk(rPDUOutletStatusIndex)
    outlet_names = session.walk(rPDUOutletStatusOutletName)
    outlet_states = session.walk(rPDUOutletStatusOutletState)

    for (index, name, state) in zip(outlet_indices, outlet_names, outlet_states):
        outlets.append({
            "index": index.value,
            "name": name.value,
            "state": outlet_state_dict.get(state.value, "UNKNOWN"),
        })

    return outlets


@app.route("/system")
def system():

    pdus = []

    for apc_pdu in app.config['APC_PDUS']:
        session = Session(version=3, **apc_pdu)

        # Perform an SNMP system walk
        system_items = session.walk('system')
        app.logger.debug('APC PDU "%s" system walk:\n%s',
            apc_pdu['hostname'],
            pformat([f'{item.oid}.{item.oid_index} {item.snmp_type} = {item.value}' for item in system_items], width=255, sort_dicts=False)
        )
        pdus.append({'snmp_variables': system_items})

    return render_template('system_table.html.j2', pdus=pdus)



@app.route('/pdu', methods=['POST'])
def pdu():
    app.logger.debug(f'Form: {pformat(request.form)}')
    form = PDURenameForm(request.form)
    if not form.validate():
        return abort(400, description=form.errors)
    apc_pdu = find_apc_pdu_by_hostname(form.pdu_hostname.data)
    session = Session(version=3, **apc_pdu)
    session.set(rPDUIdentName, form.pdu_input_name.data, snmp_type='OCTETSTR')
    pdu_name = session.get('sysName.0').value
    json_response = {
        'pdu_hostname': form.pdu_hostname.data,
        'pdu_name': pdu_name,
    }
    app.logger.debug(f'JSON response: {pformat(json_response)}')
    return json_response


@app.route('/outlets', methods=['POST'])
def outlets():
    app.logger.debug(f'Form: {pformat(request.form)}')
    form = OutletForm(request.form)
    if not form.validate():
        return abort(400, description=form.errors)
    apc_pdu = find_apc_pdu_by_hostname(form.pdu_hostname.data)
    session = Session(version=3, **apc_pdu)

    match form.requested_state.data:
        case 'ON':
            session.set(rPDUOutletDevCommand, '2', snmp_type='INTEGER')
        case 'OFF':
            session.set(rPDUOutletDevCommand, '3', snmp_type='INTEGER')
        case 'REBOOT':
            session.set(rPDUOutletDevCommand, '4', snmp_type='INTEGER')

    json_response = {
        'pdu_hostname': form.pdu_hostname.data,
        'outlets': walk_outlets(session),
    }
    app.logger.debug(f'JSON response:\n{pformat(json_response)}')
    return json_response



@app.route('/outlet', methods=['POST', 'GET'])
def outlet():
    # Making changes with a GET requests is evil,
    # keeping it though for functional parity to https://github.com/disisto/apc-switched-rack-pdu-control-panel
    if request.method == 'GET':
        app.logger.debug(f'Args: {pformat(request.args)}')
        form = SingleOutletForm(request.args)
    else:
        app.logger.debug(f'Form: {pformat(request.form)}')
        form = SingleOutletForm(request.form)

    if not form.validate():
        return abort(400, description=form.errors)
    apc_pdu = find_apc_pdu_by_hostname(form.pdu_hostname.data)
    session = Session(version=3, **apc_pdu)
    outlet_index = form.outlet_index.data

    # Get state of the affected APC PDU power outlet
    query_outlet_state = session.get(f"{rPDUOutletStatusOutletState}.{outlet_index}")
    if query_outlet_state.snmp_type != 'INTEGER':
        return abort(500, description='Invalid SNMP response')
    # ON (1), OFF (2), REBOOT (3)
    current_state = outlet_state_dict.get(query_outlet_state.value, "UNKNOWN")
    app.logger.debug(f"Current state: {current_state}, Requested state: {form.requested_state.data}")

    match form.requested_state.data:
        case 'ON':
            session.set(f"{rPDUOutletControlOutletCommand}.{outlet_index}" , '1', snmp_type='INTEGER')
        case 'OFF':
            session.set(f"{rPDUOutletControlOutletCommand}.{outlet_index}" , '2', snmp_type='INTEGER')
        case 'REBOOT':
            session.set(f"{rPDUOutletControlOutletCommand}.{outlet_index}" , '3', snmp_type='INTEGER')
        case 'TOGGLE':
            if current_state == 'ON':
                session.set(f"{rPDUOutletControlOutletCommand}.{outlet_index}" , '2', snmp_type='INTEGER')
            elif current_state == 'OFF':
                session.set(f"{rPDUOutletControlOutletCommand}.{outlet_index}" , '1', snmp_type='INTEGER')

    query_outlet_state = session.get(f"{rPDUOutletStatusOutletState}.{outlet_index}")
    json_response = {
        'state': outlet_state_dict.get(query_outlet_state.value, "UNKNOWN"),
        'pdu_hostname': form.pdu_hostname.data,
        'index': outlet_index,
    }
    app.logger.debug(f'JSON response: {pformat(json_response)}')
    return json_response


@app.get('/')
def main_get():

    pdus = []
    for apc_pdu in app.config['APC_PDUS']:

        session = Session(version=3, **apc_pdu)

        pdu_name = session.get('sysName.0').value

        outlets = walk_outlets(session)
        app.logger.debug('Outlet state on APC PDU "%s" (%s):\n%s', pdu_name, apc_pdu['hostname'], pformat(outlets, sort_dicts=False))

        pdus.append({
            'name': pdu_name,
            'hostname': apc_pdu['hostname'],
            'outlets': outlets,
        })

    rendered_template =  render_template(
        'index.html.j2',
        pdus=pdus,
        year=datetime.date.today().year,
    )
    return rendered_template
