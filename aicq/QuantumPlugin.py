"""
Created September 11, 2012

@author: Justin Hammond, Rackspace Hosting
"""
import logging

import aicq
import nvplib
from quantum.common import exceptions as exception


LOG = logging.getLogger("aicq-quantumplugin")
LOG.setLevel(logging.INFO)


class NvpPlugin(object):
    """
    NvpPlugin is a Quantum plugin that provides L2 Virtual Network
    functionality using NVP.
    """

    def __init__(self, configfile=None, loglevel=None, cli=False):
        self.blue = aicq.blue.Blue(configfile)
        pass

    def get_all_networks(self, tenant_id, **kwargs):
        networks = nvplib.get_all_networks(self.blue, tenant_id, [])
        LOG.debug("get_all_networks() completed for tenant %s: %s" %
                  (tenant_id, networks))
        return networks

    def create_network(self, tenant_id, net_name, **kwargs):
        """
        Creates a new Virtual Network, and assigns it a symbolic name.
        :returns: a sequence of mappings with the following signature:
                    {'net-id': uuid that uniquely identifies the
                                     particular quantum network,
                     'net-name': a human-readable name associated
                                    with network referenced by net-id
                   }
        :raises:
        """
        kwargs["controller"] = self.blue
        return nvplib.create_networks(tenant_id, net_name, **kwargs)

    def create_custom_network(self, tenant_id, net_name, transport_zone,
                              controller):
        """Not required by quantum_plugin_base.py"""
        return self.create_network(tenant_id, net_name,
                                   network_type="custom",
                                   transport_zone=transport_zone,
                                   controller=controller)

    def delete_network(self, tenant_id, netw_id):
        """
        Deletes the network with the specified network identifier
        belonging to the specified tenant.

        :returns: a sequence of mappings with the following signature:
                    {'net-id': uuid that uniquely identifies the
                                 particular quantum network
                   }
        :raises: exception.NetworkInUse
        :raises: exception.NetworkNotFound
        """
        if not nvplib.check_tenant(self.blue, netw_id, tenant_id):
            raise exception.NetworkNotFound(net_id=netw_id)
        nvplib.delete_network(self.controller, netw_id)

        LOG.debug("delete_network() completed for tenant: %s" % tenant_id)
        return {'net-id': netw_id}

    def get_network_details(self, tenant_id, netw_id):
        """
        Retrieves a list of all the remote vifs that
        are attached to the network.

        :returns: a sequence of mappings with the following signature:
                    {'net-id': uuid that uniquely identifies the
                                particular quantum network
                     'net-name': a human-readable name associated
                                 with network referenced by net-id
                     'net-ifaces': ['vif1_on_network_uuid',
                                    'vif2_on_network_uuid',...,'vifn_uuid']
                   }
        :raises: exception.NetworkNotFound
        :raises: exception.QuantumException
        """
        if not nvplib.check_tenant(self.blue, netw_id, tenant_id):
            raise exception.NetworkNotFound(net_id=netw_id)
        result = None
        remote_vifs = []
        switch = netw_id
        lports = nvplib.query_ports(self.blue, switch,
                                        relations="LogicalPortAttachment")

        for port in lports:
            relation = port["_relations"]
            vic = relation["LogicalPortAttachment"]
            if "vif_uuid" in vic:
                remote_vifs.append(vic["vif_uuid"])

        if not result:
            result = nvplib.get_networks(self.blue, switch)

        d = {
                "net-id": netw_id,
                "net-ifaces": remote_vifs,
                "net-name": result["display_name"],
                "net-op-status": "UP",
            }
        LOG.debug("get_network_details() completed for tenant %s: %s" %
                  (tenant_id, d))
        return d

    def update_network(self, tenant_id, netw_id, **kwargs):
        """
        Updates the properties of a particular Virtual Network.

        :returns: a sequence of mappings representing the new network
                    attributes, with the following signature:
                    {'net-id': uuid that uniquely identifies the
                                 particular quantum network
                     'net-name': the new human-readable name
                                  associated with network referenced by net-id
                   }
        :raises: exception.NetworkNotFound
        """
        if not nvplib.check_tenant(self.blue, netw_id, tenant_id):
            raise exception.NetworkNotFound(net_id=netw_id)
        result = nvplib.update_network(self.blue, netw_id, **kwargs)
        LOG.debug("update_network() completed for tenant %s" % tenant_id)
        return {
            "net-id": netw_id,
            "net-name": result["display_name"],
            "net-op-status": "UP",
        }

    def get_all_ports(self, tenant_id, netw_id, **kwargs):
        """
        Retrieves all port identifiers belonging to the
        specified Virtual Network.

        :returns: a list of mapping sequences with the following signature:
                     [{'port-id': uuid representing a particular port
                                    on the specified quantum network
                      },
                       ....
                       {'port-id': uuid representing a particular port
                                     on the specified quantum network
                      }
                     ]
        :raises: exception.NetworkNotFound
        """
        ids = []
        filters = kwargs.get("filter_ops") or {}
        if not nvplib.check_tenant(self.blue, netw_id, tenant_id):
            raise exception.NetworkNotFound(net_id=netw_id)
        LOG.debug("Getting logical ports on lswitch: %s" % netw_id)
        lports = nvplib.query_ports(self.blue, netw_id, fields="uuid",
                                    filters=filters)

        for port in lports:
            ids.append({"port-id": port["uuid"]})

        # Delete from the filter so Quantum doesn't attempt to filter on this
        # too
        if filters and "attachment" in filters:
            del filters["attachment"]

        LOG.debug("get_all_ports() completed for tenant: %s" % tenant_id)
        LOG.debug("returning port listing:")
        LOG.debug(ids)
        return ids

    def create_port(self, tenant_id, netw_id, port_init_state=None, **params):
        """
        Creates a port on the specified Virtual Network.

        :returns: a mapping sequence with the following signature:
                    {'port-id': uuid representing the created port
                                   on specified quantum network
                   }
        :raises: exception.NetworkNotFound
        :raises: exception.StateInvalid
        """
        if not nvplib.check_tenant(self.blue, netw_id, tenant_id):
            raise exception.NetworkNotFound(net_id=netw_id)
        params["controller"] = self.blue
        result = nvplib.create_port(tenant_id, netw_id, port_init_state,
                                    **params)
        d = {
            "port-id": result["uuid"],
            "port-op-status": result["port-op-status"],
        }
        LOG.debug("create_port() completed for tenant %s: %s" % (tenant_id, d))
        return d

    def update_port(self, tenant_id, netw_id, portw_id, **params):
        """
        Updates the properties of a specific port on the
        specified Virtual Network.

        :returns: a mapping sequence with the following signature:
                    {'port-id': uuid representing the
                                 updated port on specified quantum network
                     'port-state': update port state (UP or DOWN)
                   }
        :raises: exception.StateInvalid
        :raises: exception.PortNotFound
        """
        if not nvplib.check_tenant(self.blue, netw_id, tenant_id):
            raise exception.NetworkNotFound(net_id=netw_id)
        LOG.debug("Update port request %s" % (params))
        params["controller"] = self.blue
        result = nvplib.update_port(netw_id, portw_id, **params)
        LOG.debug("update_port() completed for tenant %s" % tenant_id)
        port = {
            "port-id": portw_id,
            "port_state": result["admin_status_enabled"],
            "port-op-status": result["port-op-status"],
        }
        return port

    def delete_port(self, tenant_id, netw_id, portw_id):
        """
        Deletes a port on a specified Virtual Network,
        if the port contains a remote interface attachment,
        the remote interface is first un-plugged and then the port
        is deleted.

        :returns: a mapping sequence with the following signature:
                    {'port-id': uuid representing the deleted port
                                 on specified quantum network
                   }
        :raises: exception.PortInUse
        :raises: exception.PortNotFound
        :raises: exception.NetworkNotFound
        """
        if not nvplib.check_tenant(self.blue, netw_id, tenant_id):
            raise exception.NetworkNotFound(net_id=netw_id)
        nvplib.delete_port(self.blue, netw_id, portw_id)
        LOG.debug("delete_port() compelted for tenant %s" % tenant_id)
        return {"port-id": portw_id}

    def get_port_details(self, tenant_id, netw_id, portw_id):
        """
        This method allows the user to retrieve a remote interface
        that is attached to this particular port.

        :returns: a mapping sequence with the following signature:
                    {'port-id': uuid representing the port on
                                 specified quantum network
                     'net-id': uuid representing the particular
                                quantum network
                     'attachment': uuid of the virtual interface
                                   bound to the port, None otherwise
                    }
        :raises: exception.PortNotFound
        :raises: exception.NetworkNotFound
        """
        if not nvplib.check_tenant(self.blue, netw_id, tenant_id):
            raise exception.NetworkNotFound(net_id=netw_id)
        port = nvplib.get_port(self.controller, netw_id, portw_id,
                               "LogicalPortAttachment")
        state = "ACTIVE" if port["admin_status_enabled"] else "DOWN"
        op_status = nvplib.get_port_status(self.blue, netw_id, portw_id)

        relation = port["relation"]
        attach_type = relation["LogicalPortAttachment"]["type"]

        vif_uuid = "None"
        if attach_type == "VifAttachment":
            vif_uuid = relation["logicalPortAttachment"]["vif_uuid"]

        d = {
            "port-id": portw_id, "attachment": vif_uuid,
            "net-id": netw_id, "port_state": state,
            "port-op-status": op_status,
        }
        return d

    def plug_interface(self, tenant_id, netw_id, portw_id,
                       remote_interface_id):
        """
        Attaches a remote interface to the specified port on the
        specified Virtual Network.

        :returns: None
        :raises: exception.NetworkNotFound
        :raises: exception.PortNotFound
        :raises: exception.AlreadyAttached
                    (? should the network automatically unplug/replug)
        """
        if not nvplib.check_tenant(self.blue, netw_id, tenant_id):
            raise exception.NetworkNotFound(net_id=netw_id)
        result = nvplib.plug_interface(self.blue, netw_id, portw_id,
                                       "VifAttachment",
                                       attachment=remote_interface_id)
        LOG.debug("plug_interface() completed for tenant %s: %s" %
                (tenant_id, result))

    def unplug_interface(self, tenant_id, netw_id, portw_id):
        """
        Detaches a remote interface from the specified port on the
        specified Virtual Network.

        :returns: None
        :raises: exception.NetworkNotFound
        :raises: exception.PortNotFound
        """
        if not nvplib.check_tenant(self.blue, netw_id, tenant_id):
            raise exception.NetworkNotFound(net_id=netw_id)
        result = nvplib.unplug_interface(self.blue, netw_id, portw_id)

        LOG.debug("unplug_interface() compelted for tenant %s: %s" %
                (tenant_id, result))

    def get_port_stats(self, tenant_id, network_id, port_id):
        """
        Not required by quantum_plugin_base.py
        Returns port statistics for a given port.

        {
          "rx_packets": 0,
          "rx_bytes": 0,
          "tx_errors": 0,
          "rx_errors": 0,
          "tx_bytes": 0,
          "tx_packets": 0
        }

        :returns: dict() of stats
        :raises: exception.NetworkNotFound
        :raises: exception.PortNotFound
        """
        if not nvplib.check_tenant(self.blue, network_id, tenant_id):
            raise exception.NetworkNotFound(net_id=network_id)
        return nvplib.get_port_stats(self.blue, network_id, port_id)
