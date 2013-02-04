"""
Created September 10, 2012

@author: Justin Hammond, Rackspace Hosting

The purpose of this class is to add functionality to the aiclib classes:
    - The ability to load configuration from a file, in nvp.ini format, or
    from a database
    - Make the library aware of a tenant construct
    - Make the library aware of the possibility of multiple controller nodes
    and allow for automated fail-over (this is provided by the config loader)

This class will be wrapped to have the same interface as nvplib.py from the
quantum/plugins/nicera variety.
"""
import csv
import ConfigParser
import logging
import sys

import aiclib
# from quantum.common import exceptions as exception

LOG = logging.getLogger("aicq-blue")
LOG.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(message)s')
ch.setFormatter(formatter)
LOG.addHandler(ch)
LOG.propagate = True


DEFAULT_REQUEST_TIMEOUT = 30
DEFAULT_HTTP_TIMEOUT = 10
DEFAULT_RETRIES = 2
DEFAULT_REDIRECTS = 2
API_REQUEST_POOL_SIZE = 10000
CONFIG_FILE = "my.ini"
CONFIG_KEYS = ["DEFAULT_TZ_UUID", "NVP_CONTROLLER_IP", "PORT", "USER",
               "PASSWORD"]


class Blue(object):

    def __init__(self, config_file=None):
        self.connections = []
        self.conn_count = 0
        self.conn_error = False
        self.aic = None
        try:
            self.load_config(config_file)
            self.conn = self.connections[0]
        except Exception, e:
            LOG.fatal("Configuration invalid. Unable to continue. %s" % e)

# --------------------------------
# Config functions
# --------------------------------

    def load_config(self, config_file):
        """Will handle loading the config from file or from a database"""
        if False:   # would be a check if loading for database
            pass
        else:       # load from file
            self.config = ConfigParser.ConfigParser()

            if config_file is None:
                config_file = CONFIG_FILE
            if config_file is None:
                raise Exception("Could not locate configuration file")
            LOG.info("Loading config file %s" % config_file)
            self.config.read(config_file)
            self._parse_config_file()
            LOG.info("Loaded config: %s" % self.output_config())

    def create_connection_object(self, ip, port, username, password, tzuuid,
                                 request_timeout=20, http_timeout=10,
                                 retries=2, redirects=2):
        info = [ip, port, username, password, request_timeout, http_timeout,
                retries, redirects]
        self._create_connection_object(info, tzuuid)

    def _create_connection_object(self, info, tzuuid):
        try:
            conn = {}
            conn['ip'] = info[0]
            conn['port'] = info[1]
            conn['username'] = info[2]
            conn['password'] = info[3]
            conn['request_timeout'] = info[4]
            conn['http_timeout'] = info[5]
            conn['retries'] = info[6]
            conn['redirects'] = info[7]
            conn['default_tz'] = tzuuid
            conn['conn_id'] = self.conn_count
            conn['errors'] = 0
        except Exception, e:
            raise AttributeError("Invalid conneciton parameters, %s", e)
        self.conn_count += 1
        self.connections.append(conn)

    def _create_legacy_connection_object(self, info):
        try:
            conn = {}
            conn['ip'] = info["NVP_CONTROLLER_IP"]
            conn['port'] = info["PORT"]
            conn['username'] = info["USER"]
            conn['password'] = info["PASSWORD"]
            conn['default_tz'] = info["DEFAULT_TZ_UUID"]
        except Exception, e:
            raise AttributeError("Invalid connection parameters, %s" % e)

    def _parse_config_file(self):
        """This configuration parser is modeled after the legacy nicera
        QuantumPlugin.py:parse_config method. It intends to do everything
        that the previous did but handle the errors in a better way. It
        does not need to return anything in particular since this version
        is in a class.
        """
        #self.failover_time # not used because not eventlet based
        #self.concurrent_connections # not used because not eventlet based

        #connection information
        try:
            #attempt to load new style connection information
            default_tz = self.config.get("NVP", "DEFAULT_TZ_UUID")
            conf_conn_key = "NVP_CONTROLLER_CONNECTIONS"
            defined_connections = self.config.get("NVP", conf_conn_key)

            for conn_key in defined_connections.split():
                csv_string = self.config.get("NVP", conn_key)
                csv_reader = csv.reader([csv_string], delimiter=':',
                                        quotechar='"')
                for row in csv_reader:
                    conn_info = row
                try:
                    self._create_connection_object(conn_info, default_tz)
                except AttributeError, e:
                    LOG.fatal("Invalid connection parameters: %s" % e)
                    raise e
        except Exception, e:
            msg = "Could not find new config format (%s), trying old"
            LOG.info(msg % e)
            try:
                args = [self.config.get("NVP", k) for k in CONFIG_KEYS]
                self._create_legacy_connection_object(args)
            except Exception, e:
                LOG.fatal("Invalid connection parameters: %s" % e)
                raise e

    def output_config(self):
        output = "CONFIG:\nCONNECTIONS:\n"
        for conn in self.connections:
            output += "%s" % conn
        return output

# --------------------------------
# Connection functions
# --------------------------------

    @property
    def connection(self):
        if self.aic is None or self.conn != self._get_connection():
            uri = self.conn['ip']
            if 'http' not in self.conn['ip']:
                scheme = "https" if self.conn['port'] == "443" else "http"
                uri = "%s://%s" % (scheme, self.conn['ip'])
            self.aic = aiclib.nvp.Connection(uri)
        return self.aic

    @property
    def connection_description(self):
        return self._get_connection

    def _get_connection(self):
        if not self.conn_error:
            return self.conn
        self.aic = None
        min_errors = sys.maxint
        ret = self.conn
        for conn in self.connections:
            if conn['errors'] < min_errors:
                ret = conn
                min_errors = conn['errors']
        self.conn = ret
        return self.conn

    @property
    def default_zone(self):
        return self._get_connection()['default_tz']

    def _connection_error(self, connection):
        self.conn_error = True
        connection['errors'] += 1

    def connection_test(self):
        return self.connection.nvp_function().logout()

# --------------------------------
# NVP utility functions
# --------------------------------

    def default_transport_zone_exists(self):
        """This will check if the default transport zone for the current
        connection actually exists"""
        try:
            self.connection.zone(self.default_zone).read()
        except aiclib.nvp.ResourceNotFound:
            return False
        return True

    def check_tenant(self, net_id, tenant_id):
        """Returns true of the tenant 'owns' this network"""
        network = self.get_network(net_id)
        for t in network["tags"]:
            if t["scope"] == "os_tid" and t["tag"] == tenant_id:
                return True
        return False

# --------------------------------
# Network (lswitch) functions
# --------------------------------

    def get_network(self, net_id):
        resp = self.connection.lswitch(net_id).read()
        return resp

    def check_network_existance(self, net_id):
        try:
            self.get_network(net_id)
            return True
        except Exception:
            pass
        return False

    def query_networks(self, tenant_id, fields="*", tags=None):
        """In regard to fields:
        Legacy expects a comma separated string. We expect a list of strings.
        """
        query = self.connection.lswitch().query()
        query.fields(fields)
        if tags:
            """In regard to tags:
            Legacy expects an list of arrays with tag index 0 and scope
            index 1. We do not expact that. We expect a list of dictionaries
            that look like: {'tag': <tag>, 'tag_scope': <scope>}
            If they don't give us a list but a single dictionary we will
            put it into a list for them (because we're so nice)
            """
            if not type(tags) is list:
                tags = [tags]
            query.tags(tags)
        results = query.results()
        return results

    def update_network(self, net_id, **kwargs):
        """Legacy only allows for updating the name, eventually this should
        and will support updating everything as long as they are given
        properly"""
        switch = self.connection.lswitch(net_id)
        if "name" in kwargs:
            switch.display_name(kwargs['name'])
        resp = switch.update()
        return resp

    def create_network(self, tenant_id, net_name, **kwargs):
        """Legacy only supports a single transport zone without binding
        configuration. Future support for that will require this function
        to change"""
        transport_zone = kwargs.get("transport_zone", self.default_zone)
        transport_type = kwargs.get("transport_type", "gre")
        zone = {'zone_uuid': transport_zone,
                'transport_type': transport_type}

        switch = self.connection.lswitch()
        switch.display_name(net_name)
        switch.transport_zones(zone)
        switch.tags({'tag': tenant_id, 'scope': 'os_tid'})
        resp = switch.create()
        return resp

    def delete_network(self, net_id):
        self.delete_networks([net_id])

    def delete_networks(self, net_ids):
        for net_id in net_ids:
            self.connection.lswitch(net_id).delete()

# --------------------------------
# Port (lport) functions
# --------------------------------

    def create_enabled_port(self, tenant, net_id, **kwargs):
        return self._create_port(tenant, net_id, True)

    def create_disabled_port(self, tenant, net_id, **kwargs):
        return self._create_port(tenant, net_id, False)

    def _create_port(self, tenant_id, net_id, enabled, **kwargs):
        port = self.connection.lswitch_port(net_id)
        port.admin_status_enabled(enabled)
        resp = port.create()
        return resp

    def get_port_stats(self, net_id, port):
        port = self.connection.lswitch_port(net_id, port)
        stats = port.statsu()
        return stats

    def get_port(self, net_id, port, relations=None):
        port = self.connection.lswitch_port(net_id, port)
        if relations:
            port.relations(relations)
        resp = port.read()
        return resp

    def delete_port(self, net_id, port):
        if not self.check_network_existance(net_id):
            LOG.error("Network not found")
            raise aiclib.nvp.ResourceNotFound()
        port = self.connection.lswitch_port(net_id, port)
        port.delete()

    def delete_all_ports(self, net_id):
        if not self.check_network_existance(net_id):
            LOG.error("Network not found")
            raise aiclib.nvp.ResourceNotFound()
        resp = self.query_ports(net_id, fields=["uuid"])
        for port in resp["results"]:
            self.delete_port(net_id, port["uuid"])

    def unplug_interface(self, net_id, port):
        port = self.connection.lswitch_port(net_id, port)
        resp = port.unattach()
        return resp

    def plug_vif_interface(self, net_id, port, vifuuid):
        """Legacy only supports vif interfaces but supports passing a type
        which could turn it into a non-vif attachment. This is bad. We will
        force the user to only make a vif interface. If different attachment
        types are required a new function for each should be made.
        """
        port = self.connection.lswitch_port(net_id, port)
        resp = port.attach_vif(vifuuid)
        return resp

    def update_port(self, net_id, port, **params):
        port = self.connection.lswitch_port(net_id, port)
        if "state" in params:
            """In regard to 'state': in legacy it was the string, 'DOWN' or
            'UP'. We except a True or False.
            """
            admin_status = params["state"]
            port.admin_status(admin_status)
        resp = port.update()
        return resp

    def query_ports(self, net_id, relations=None, fields="*", filters=None):
        """In regard to fields:
        Legacy expects a comma separated string. We expect a list of strings.
        """
        query = self.connection.lswitch_port(net_id).query()
        query.fields(fields)
        if relations:
            query.relations(relations)
        if filters and "attachment" in filters:
            query.attachment_vifuuid("=", filters["attachment"])
        resp = query.results()
        return resp

    def get_port_status(self, net_id, port_id):
        if not self.check_network_existance(net_id):
            LOG.error("Network not found")
            raise aiclib.nvp.ResourceNotFound()
        port = self.connection.lswitch_port(net_id, port_id)
        resp = port.status()
        return resp

    def get_port_link_status(self, net_id, port_id):
        resp = self.get_port_status(net_id, port_id)
        return "UP" if resp['link_status_up'] else "DOWN"
