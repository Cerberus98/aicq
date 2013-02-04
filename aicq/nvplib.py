"""
Created September 6, 2012

@author: Justin Hammond, Rackspace Hosting
"""

import logging

import aiclib
import aicq.blue
from quantum.common import exceptions as exception

LOG = logging.getLogger("aicq-nvplib")
LOG.setLevel(logging.INFO)


def check_default_transport_zone(controller):
    """c is ignored and this function is expected to throw an exception
    if the default transport zone doesn't exist"""
    if isinstance(controller, aicq.blue.Blue):
        blue = controller
    if not blue.default_transport_zone_exists():
        msg = "Unable to find zone \"%s\" for controller \"%s\"" % (
               blue.default_zone, blue.connection_description)
        raise Exception(msg)


def check_tenant(controller, net_id, tenant_id):
    """Return true if the tenant 'owns' this network; controller ignored"""
    if isinstance(controller, aicq.blue.Blue):
        blue = controller
    return blue.check_tenant(net_id, tenant_id)


# -------------------------------------------------------------------
# Network functions
# -------------------------------------------------------------------


def get_network(controller, net_id):
    """Returns the configuration of the lswitch"""
    if isinstance(controller, aicq.blue.Blue):
        blue = controller
    try:
        network = blue.get_network(net_id)
    except aiclib.nvp.ResourceNotFound:
        raise exception.NetworkNotFound(net_id=net_id)
    except aiclib.nvp.NVPException:
        raise exception.QuantumException()
    LOG.debug("Got network \"%s\": %s" % (net_id, network))
    return network


def update_network(controller, network, **kwargs):
    if isinstance(controller, aicq.blue.Blue):
        blue = controller
    try:
        obj = blue.update_network(network, kwargs)
    except aiclib.nvp.ResourceNotFound:
        raise exception.NetworkNotFound(net_id=network)
    except aiclib.nvp.NVPException:
        raise exception.QuantumException()
    return obj


def get_all_networks(controller, tenant_id, networks):
    if isinstance(controller, aicq.blue.Blue):
        blue = controller
    try:
        resp = blue.query_networks(tenant_id, fields=['uuid', 'display_name'])
    except aiclib.nvp.NVPException:
        raise exception.QuantumException()
    switches = resp['results']
    for switch in switches:
        net_id = switch['uuid']
        if net_id not in [x['id'] for x in networks]:
            networks.append({"id": net_id,
                             "name": switch["display_name"]})
    return networks


def query_networks(controller, tenant_id, fields="*", tags=None):
    if isinstance(controller, aicq.blue.Blue):
        blue = controller
    try:
        resp = blue.query_networks(tenant_id, fields, tags)
    except aiclib.nvp.NVPException:
        raise exception.QuantumException()
    if not resp:
        return []
    switches = resp['results']
    nets = [{'id': switch['uuid'], 'name': switch['display_name']} for
            switch in switches]
    return nets


def delete_network(controller, network):
    delete_networks(controller, [network])


def delete_networks(controller, networks):
    if isinstance(controller, aicq.blue.Blue):
        blue = controller
    for network in networks:
        try:
            blue.delete_network(network)
        except aiclib.nvp.ResourceNotFound:
            raise exception.NetworkNotFound(net_id=network)
        except aiclib.nvp.NVPException:
            raise exception.QuantumException()


def create_lswitch(controller, lswitch_obj):
    """Deprecated: how does this work in this new non-flat world?"""
    pass


def create_network(tenant_id, net_name, **kwargs):
    controller = kwargs["controller"]
    if isinstance(controller, aicq.blue.Blue):
        blue = controller
    try:
        net = blue.create_network(tenant_id, net_name, **kwargs)
    except aiclib.nvp.NVPException:
        raise exception.QuantumException()
    d = {}
    d['id'] = net['uuid']
    d['name'] = net['display_name']
    d['net-op-status'] = 'UP'
    return net


#---------------------------------------------------------------------
# Port functions
#---------------------------------------------------------------------


def get_port_stats(controller, network_id, port_id):
    if isinstance(controller, aicq.blue.Blue):
        blue = controller
    if not blue.check_network_existance(network_id):
        LOG.error("Network not found, Error")
        raise exception.NetworkNotFound(net_id=network_id)
    try:
        stats = blue.get_port_stats(network_id, port_id)
    except aiclib.nvp.ResourceNotFound as e:
        LOG.error("Port not found, Error: %s" % str(e))
        raise exception.PortNotFound(port_id=port_id, net_id=network_id)
    LOG.debug("Returning stats for port \"%s\" on \"%s\": %s" % (port_id,
                                                                 network_id,
                                                                 stats))
    return stats


def check_port_state(state):
    if state not in ["ACTIVE", "DOWN"]:
        LOG.error("Invalid port state (ACTIVE and DOWN are valid states): %s" %
                  state)
        raise exception.StateInvalid(port_state=state)


def query_ports(controller, network, relations=None, fields="*",
                filters=None):
    if isinstance(controller, aicq.blue.Blue):
        blue = controller
    try:
        results = blue.query_ports(network, relations, fields, filters)
    except aiclib.nvp.ResourceNotFound as e:
        LOG.error("Network not found, Error: %s" % str(e))
        raise exception.NetworkNotFound(net_id=network)
    except aiclib.nvp.NVPException:
        raise exception.QuantumException()
    return results


def delete_port(controller, network, port):
    if isinstance(controller, aicq.blue.Blue):
        blue = controller
    try:
        blue.delete_port(network, port)
    except aiclib.nvp.ResourceNotFound as e:
        LOG.error("Port or Network not found, Error: %s" % str(e))
        raise exception.PortNotFound(port_id=port, net_id=network)
    except aiclib.nvp.NVPException:
        raise exception.QuantumException()


def delete_all_ports(controller, ls_uuid):
    if isinstance(controller, aicq.blue.Blue):
        blue = controller
    try:
        blue.delete_all_ports(ls_uuid)
    except aiclib.nvp.NVPException:
        raise exception.QuantumException()


def get_port(controller, network, port, relations=None):
    if isinstance(controller, aicq.blue.Blue):
        blue = controller
    try:
        port = blue.get_port(network, port, relations)
    except aiclib.nvp.ResourceNotFound as e:
        LOG.error("Port or Network not found, Error: %s" % str(e))
        raise exception.PortNotFound(port_id=port, net_id=network)
    except aiclib.nvp.NVPException:
        raise exception.QuantumException()
    return port


def plug_interface(controller, network, port, attach_type, attachment=None):
    if isinstance(controller, aicq.blue.Blue):
        blue = controller
    try:
        resp = blue.plug_vif_interface(network, port, attachment)
    except aiclib.nvp.ResourceNotFound:
        LOG.error("Port or Network not found, Error: %s" % str(e))
        raise exception.PortNotFound(port_id=port, net_id=network)
    except aiclib.nvp.Conflict as e:
        LOG.error("Conflict while making attachment to port, "
                  "Error: %s" % str(e))
        raise exception.AlreadyAttached(att_id=attachment,
                                        port_id=port,
                                        net_id=network,
                                        att_port_id="UNKNOWN")
    except aiclib.nvp.NVPException:
        raise exception.QuantumException()
    return resp


def unplug_interface(controller, network, port):
    if isinstance(controller, aicq.blue.Blue):
        blue = controller
    try:
        resp = blue.unplug_interface(network, port)
    except aiclib.nvp.ResourceNotFound as e:
        LOG.error("Port or Network not found, Error: %s" % str(e))
        raise exception.PortNotFound(port_id=port, net_id=network)
    except aiclib.nvp.NVPException:
        raise exception.QuantumException()
    return resp


def update_port(network, port_id, **params):
    controller = params["controller"]
    if isinstance(controller, aicq.blue.Blue):
        blue = controller
    admin_status = True
    if "state" in params:
        state = params["state"]
        check_port_state(state)
        if state == "DOWN":
            admin_status = False
    try:
        resp = blue.update_port(network, port_id, state=admin_status)
    except aiclib.nvp.ResourceNotFound as e:
        LOG.error("Port or Network not found, Error: %s" % str(e))
        raise exception.PortNotFound(port_id=port_id, net_id=network)
    except aiclib.nvp.NVPException:
        raise exception.QuantumException()
    resp['port-op-status'] = get_port_status(controller, network, resp["uuid"])
    return resp


def create_port(tenant, network, port_init_state, **params):
    check_port_state(port_init_state)

    controller = params["controller"]
    if isinstance(controller, aicq.blue.Blue):
        blue = controller

    try:
        if port_init_state == "DOWN":
            port = blue.create_disabled_port(tenant, network, params)
        else:
            port = blue.create_enabled_port(tenant, network, params)
    except aiclib.nvp.ResourceNotFound as e:
        LOG.error("Network not found, Error: %s" % str(e))
        raise exception.NetworkNotFound(net_id=network)
    except aiclib.nvp.NVPException:
        raise exception.QuantumException()
    port['port-op-status'] = get_port_status(controller, network, port['uuid'])
    return port


def get_port_status(controller, lswitch_id, port_id):
    if isinstance(controller, aicq.blue.Blue):
        blue = controller
    try:
        if not blue.check_network_existance(lswitch_id):
            LOG.error("Network not found, Error")
            raise exception.NetworkNotFound(net_id=lswitch_id)
    except aiclib.nvp.NVPException:
        raise exception.QuantumException
    try:
        status = blue.get_port_link_status(lswitch_id, port_id)
    except aiclib.nvp.ResourceNotFound as e:
        LOG.error("Port not found, Error: %s" % str(e))
        raise exception.PortNotFound(port_id=port_id, net_id=lswitch_id)
    except aiclib.nvp.NVPException:
        raise exception.QuantumException()
    return status
