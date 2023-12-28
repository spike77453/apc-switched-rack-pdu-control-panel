import datetime
from pprint import pformat

from easysnmp import Session
from flask import redirect, render_template, request, url_for

from apc_switched_rack_pdu_control_panel import app

rPDUIdentName                  = '1.3.6.1.4.1.318.1.1.12.1.1.0'
rPDUOutletDevCommand           = '1.3.6.1.4.1.318.1.1.12.3.1.1.0'
rPDUOutletControlOutletCommand = '1.3.6.1.4.1.318.1.1.12.3.3.1.1.4'
rPDUOutletStatusIndex          = '1.3.6.1.4.1.318.1.1.12.3.5.1.1.1'
rPDUOutletStatusOutletName     = '1.3.6.1.4.1.318.1.1.12.3.5.1.1.2'
rPDUOutletStatusOutletState    = '1.3.6.1.4.1.318.1.1.12.3.5.1.1.4'


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


@app.post('/')
def main_post():
#---- BEGIN: Handle outlets -----------
    if not 'IP' in request.form:
        return 'PDU not found', 400
    apc_pdu = find_apc_pdu_by_hostname(request.form['IP'])
    if not apc_pdu:
        return 'PDU not found', 400
    session = Session(version=3, **apc_pdu)

    # Command to all outlets has been sent
    if 'OUTLET' in request.form and not request.form['OUTLET'].isnumeric():
        match request.form['STATE']:
            case 'ON':
                session.set(rPDUOutletDevCommand, '2', snmp_type='INTEGER')
            case 'OFF':
                session.set(rPDUOutletDevCommand, '3', snmp_type='INTEGER')
            case 'REBOOT':
                session.set(rPDUOutletDevCommand, '4', snmp_type='INTEGER')

    # Command to a single outlets has been sent
    elif 'OUTLET' in request.form and request.form['OUTLET'].isnumeric():
        # Get state of the affected APC PDU power outlet
        query_outlet_state = session.get(f"{rPDUOutletStatusOutletState}.{request.form['OUTLET']}")

        # ON (1), OFF (2), REBOOT (3)
        if 'REQUESTED_STATE' in request.form and query_outlet_state.snmp_type == 'INTEGER':
            app.logger.debug(f"Current state: {query_outlet_state.value}, Requested state: {request.form['REQUESTED_STATE']}")

            # If current state is ON (1) and requested state is OFF, change to OFF (2)
            if query_outlet_state.value == '1' and request.form['REQUESTED_STATE'] == 'OFF':
                session.set(f"{rPDUOutletControlOutletCommand}.{request.form['OUTLET']}" , '2', snmp_type='INTEGER')

            # If current state is OFF (2), and requested state is ON, change to ON (1)
            elif query_outlet_state.value == '2' and request.form['REQUESTED_STATE'] == 'ON':
                session.set(f"{rPDUOutletControlOutletCommand}.{request.form['OUTLET']}" , '1', snmp_type='INTEGER')

            # REBOOT has been requested
            elif request.form['REQUESTED_STATE'] ==  'REBOOT':
                session.set(f"{rPDUOutletControlOutletCommand}.{request.form['OUTLET']}" , '3', snmp_type='INTEGER')
#---- END: Handle outlets ------

#---- BEGIN: PDU rename ---------------
    elif 'pduInputName' in request.form:
        app.logger.debug('Renaming PDU')
        if request.form['pduInputName'].isascii():
            session.set(rPDUIdentName, request.form['pduInputName'], snmp_type='OCTETSTR')
        else:
            app.logger.error('New name contains non-ASCII characters')
#---- END: PDU rename -----------------

    # PRG to stop the form resubmission on page refresh, see https://en.wikipedia.org/wiki/Post/Redirect/Get
    return redirect(url_for('main_get'))



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
