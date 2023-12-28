import datetime
from pprint import pformat

from easysnmp import Session
from flask import abort, render_template, request

from apc_switched_rack_pdu_control_panel import app

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
    if not 'pduInputName' in request.form or not request.form['pduInputName'].isascii() or not request.form['pduInputName']:
        return abort(400, description='Invalid PDU name')
    if not 'IP' in request.form:
        return abort(400, description='No PDU specified')
    pdu_hostname = request.form['IP']
    apc_pdu = find_apc_pdu_by_hostname(pdu_hostname)
    if not apc_pdu:
        return abort(400, description='PDU not found')
    session = Session(version=3, **apc_pdu)
    session.set(rPDUIdentName, request.form['pduInputName'], snmp_type='OCTETSTR')
    pdu_name = session.get('sysName.0').value
    json_response = {
        'pdu_hostname': pdu_hostname,
        'pdu_name': pdu_name,
    }
    app.logger.debug(f'JSON response: {pformat(json_response)}')
    return json_response


@app.route('/outlets', methods=['POST'])
def outlets():
    app.logger.debug(f'Form: {pformat(request.form)}')
    if not 'REQUESTED_STATE' in request.form or request.form['REQUESTED_STATE'] not in ['ON', 'OFF', 'REBOOT']:
        return abort(400, description='Invalid state requested')
    if not 'IP' in request.form:
        return abort(400, description='No PDU specified')
    pdu_hostname = request.form['IP']
    apc_pdu = find_apc_pdu_by_hostname(pdu_hostname)
    if not apc_pdu:
        return abort(400, description='PDU not found')
    session = Session(version=3, **apc_pdu)

    match request.form['REQUESTED_STATE']:
        case 'ON':
            session.set(rPDUOutletDevCommand, '2', snmp_type='INTEGER')
        case 'OFF':
            session.set(rPDUOutletDevCommand, '3', snmp_type='INTEGER')
        case 'REBOOT':
            session.set(rPDUOutletDevCommand, '4', snmp_type='INTEGER')

    outlets = []
    outlet_indices = session.walk(rPDUOutletStatusIndex)
    outlet_names = session.walk(rPDUOutletStatusOutletName)
    outlet_states = session.walk(rPDUOutletStatusOutletState)

    json_response = {
        'pdu_hostname': pdu_hostname,
        'outlets': {}
    }
    for (index, name, state) in zip(outlet_indices, outlet_names, outlet_states):
        json_response['outlets'][index.value] = {
            "name": name.value,
            "state": outlet_state_dict.get(state.value, "UNKNOWN"),
        }
    app.logger.debug(f'JSON response:\n{pformat(json_response)}')
    return json_response



@app.route('/outlet', methods=['POST'])
def outlet():
    app.logger.debug(f'Form: {pformat(request.form)}')
    if not 'OUTLET' in request.form or not request.form['OUTLET'].isnumeric():
        return abort(400, description='Invalid outlet index')
    if not 'REQUESTED_STATE' in request.form or request.form['REQUESTED_STATE'] not in ['ON', 'OFF', 'REBOOT']:
        return abort(400, description='Invalid state requested')
    if not 'IP' in request.form:
        return abort(400, description='No PDU specified')
    pdu_hostname = request.form['IP']
    apc_pdu = find_apc_pdu_by_hostname(pdu_hostname)
    if not apc_pdu:
        return abort(400, description='PDU not found')
    session = Session(version=3, **apc_pdu)
    outlet_index = request.form['OUTLET']
    requested_state = request.form['REQUESTED_STATE']

    # Get state of the affected APC PDU power outlet
    query_outlet_state = session.get(f"{rPDUOutletStatusOutletState}.{outlet_index}")
    if query_outlet_state.snmp_type != 'INTEGER':
        return abort(500, description='Invalid SNMP response')
    # ON (1), OFF (2), REBOOT (3)
    current_state = outlet_state_dict.get(query_outlet_state.value, "UNKNOWN")
    app.logger.debug(f"Current state: {current_state}, Requested state: {requested_state}")

    # If current state is ON (1) and requested state is OFF, change to OFF (2)
    if current_state == 'ON' and requested_state == 'OFF':
        session.set(f"{rPDUOutletControlOutletCommand}.{outlet_index}" , '2', snmp_type='INTEGER')

    # If current state is OFF (2), and requested state is ON, change to ON (1)
    elif current_state == 'OFF' and requested_state == 'ON':
        session.set(f"{rPDUOutletControlOutletCommand}.{outlet_index}" , '1', snmp_type='INTEGER')

    # REBOOT has been requested
    elif requested_state ==  'REBOOT':
        session.set(f"{rPDUOutletControlOutletCommand}.{outlet_index}" , '3', snmp_type='INTEGER')

    query_outlet_state = session.get(f"{rPDUOutletStatusOutletState}.{outlet_index}")
    json_response = {
        'state': outlet_state_dict.get(query_outlet_state.value, "UNKNOWN"),
        'pdu_hostname': pdu_hostname,
        'index': outlet_index,
    }
    app.logger.debug(f'JSON response: {pformat(json_response)}')
    return json_response


@app.get('/')
def main_get():
    if 'IP' in request.args and 'OUTLET' in request.args and request.args['OUTLET'].isnumeric():
        app.logger.warning("This should toggle outlet %s on %s. Not implemented yet.", request.args['OUTLET'], request.args['IP'])
        return '', 302

    pdus = []
    for apc_pdu in app.config['APC_PDUS']:

        session = Session(version=3, **apc_pdu)

        pdu_name = session.get('sysName.0').value

        outlets = []
        outlet_indices = session.walk(rPDUOutletStatusIndex)
        outlet_names = session.walk(rPDUOutletStatusOutletName)
        outlet_states = session.walk(rPDUOutletStatusOutletState)

        for (index, name, state) in zip(outlet_indices, outlet_names, outlet_states):
            outlets.append({
                "index": index.value,
                "name": name.value,
                "state": {"1": "ON", "2": "OFF"}.get(state.value, "UNKNOWN"),
            })

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
        server_name='localhost',
    )
    return rendered_template
