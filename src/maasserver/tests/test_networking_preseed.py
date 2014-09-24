# Copyright 2014 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for networking preseed code."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

str = None

__metaclass__ = type
__all__ = [
    ]

from maasserver import networking_preseed
from maasserver.networking_preseed import (
    extract_network_interfaces,
    generate_ethernet_link_entry,
    generate_networking_config,
    normalise_mac,
    )
from maasserver.testing.factory import factory
from maasserver.testing.testcase import MAASServerTestCase
from maastesting.matchers import MockCalledOnceWith


def make_denormalised_mac():
    return ' %s ' % factory.make_mac_address().upper()


class TestExtractNetworkInterfaces(MAASServerTestCase):

    def test__returns_nothing_if_no_lshw_output_found(self):
        node = factory.make_Node()
        self.assertEqual([], extract_network_interfaces(node))

    def test__returns_nothing_if_no_network_description_found_in_lshw(self):
        node = factory.make_Node()
        lshw_output = """
            <list xmlns:lldp="lldp" xmlns:lshw="lshw">
              <lshw:list>
              </lshw:list>
            </list>
            """
        factory.make_NodeResult_for_commissioning(
            node=node, name='00-maas-01-lshw.out', script_result=0,
            data=lshw_output.encode('ascii'))
        self.assertEqual([], extract_network_interfaces(node))

    def test__extracts_interface_data(self):
        node = factory.make_Node()
        interface = factory.make_name('eth')
        mac = factory.make_mac_address()
        lshw_output = """
            <node id="network" claimed="true" class="network">
             <logicalname>%(interface)s</logicalname>
             <serial>%(mac)s</serial>
            </node>
            """ % {'interface': interface, 'mac': mac}
        factory.make_NodeResult_for_commissioning(
            node=node, name='00-maas-01-lshw.out', script_result=0,
            data=lshw_output.encode('ascii'))
        self.assertEqual([(interface, mac)], extract_network_interfaces(node))

    def test__finds_network_interface_on_motherboard(self):
        node = factory.make_Node()
        interface = factory.make_name('eth')
        mac = factory.make_mac_address()
        # Stripped-down version of real lshw output:
        lshw_output = """
            <!-- generated by lshw-B.02.16 -->
            <list>
            <node id="mynode" claimed="true" class="system" handle="DMI:0002">
              <node id="core" claimed="true" class="bus" handle="DMI:0003">
               <description>Motherboard</description>
                <node id="pci" claimed="true" class="bridge" \
                      handle="PCIBUS:0000:00">
                 <description>Host bridge</description>
                  <node id="network" claimed="true" class="network" \
                      handle="PCI:0000:00:19.0">
                   <description>Ethernet interface</description>
                   <product>82566DM-2 Gigabit Network Connection</product>
                   <vendor>Intel Corporation</vendor>
                   <logicalname>%(interface)s</logicalname>
                   <serial>%(mac)s</serial>
                   <configuration>
                    <setting id="ip" value="10.99.99.1" />
                   </configuration>
                  </node>
                </node>
              </node>
            </node>
            </list>
            """ % {'interface': interface, 'mac': mac}
        factory.make_NodeResult_for_commissioning(
            node=node, name='00-maas-01-lshw.out', script_result=0,
            data=lshw_output.encode('ascii'))
        self.assertEqual([(interface, mac)], extract_network_interfaces(node))

    def test__finds_network_interface_on_pci_bus(self):
        node = factory.make_Node()
        interface = factory.make_name('eth')
        mac = factory.make_mac_address()
        # Stripped-down version of real lshw output:
        lshw_output = """
            <!-- generated by lshw-B.02.16 -->
            <list>
            <node id="mynode" claimed="true" class="system" handle="DMI:0002">
              <node id="core" claimed="true" class="bus" handle="DMI:0003">
               <description>Motherboard</description>
                <node id="pci" claimed="true" class="bridge" \
                    handle="PCIBUS:0000:00">
                 <description>Host bridge</description>
                  <node id="pci:2" claimed="true" class="bridge" \
                      handle="PCIBUS:0000:07">
                   <description>PCI bridge</description>
                    <node id="network" claimed="true" class="network" \
                        handle="PCI:0000:07:04.0">
                     <description>Ethernet interface</description>
                     <logicalname>%(interface)s</logicalname>
                     <serial>%(mac)s</serial>
                     <configuration>
                      <setting id="ip" value="192.168.1.114" />
                     </configuration>
                    </node>
                  </node>
                </node>
              </node>
            </node>
            </list>
            """ % {'interface': interface, 'mac': mac}
        factory.make_NodeResult_for_commissioning(
            node=node, name='00-maas-01-lshw.out', script_result=0,
            data=lshw_output.encode('ascii'))
        self.assertEqual([(interface, mac)], extract_network_interfaces(node))

    def test__ignores_nodes_without_interface_name(self):
        node = factory.make_Node()
        mac = factory.make_mac_address()
        lshw_output = """
            <node id="network" claimed="true" class="network">
             <serial>%s</serial>
            </node>
            """ % mac
        factory.make_NodeResult_for_commissioning(
            node=node, name='00-maas-01-lshw.out', script_result=0,
            data=lshw_output.encode('ascii'))
        self.assertEqual([], extract_network_interfaces(node))

    def test__ignores_nodes_without_mac(self):
        node = factory.make_Node()
        interface = factory.make_name('eth')
        lshw_output = """
            <node id="network" claimed="true" class="network">
             <logicalname>%s</logicalname>
            </node>
            """ % interface
        factory.make_NodeResult_for_commissioning(
            node=node, name='00-maas-01-lshw.out', script_result=0,
            data=lshw_output.encode('ascii'))
        self.assertEqual([], extract_network_interfaces(node))

    def test__normalises_mac(self):
        node = factory.make_Node()
        interface = factory.make_name('eth')
        mac = make_denormalised_mac()
        self.assertNotEqual(normalise_mac(mac), mac)
        lshw_output = """
            <node id="network" claimed="true" class="network">
             <logicalname>%(interface)s</logicalname>
             <serial>%(mac)s</serial>
            </node>
            """ % {'interface': interface, 'mac': mac}
        factory.make_NodeResult_for_commissioning(
            node=node, name='00-maas-01-lshw.out', script_result=0,
            data=lshw_output.encode('ascii'))
        [entry] = extract_network_interfaces(node)
        _, extracted_mac = entry
        self.assertEqual(normalise_mac(mac), extracted_mac)


class TestNormaliseMAC(MAASServerTestCase):

    def test__normalises_case(self):
        mac = factory.make_mac_address()
        self.assertEqual(
            normalise_mac(mac.lower()),
            normalise_mac(mac.upper()))

    def test__strips_whitespace(self):
        mac = factory.make_mac_address()
        self.assertEqual(
            normalise_mac(mac),
            normalise_mac(' %s ' % mac))

    def test__is_idempotent(self):
        mac = factory.make_mac_address()
        self.assertEqual(
            normalise_mac(mac),
            normalise_mac(normalise_mac(mac)))


class TestGenerateEthernetLinkEntry(MAASServerTestCase):

    def test__generates_dict(self):
        interface = factory.make_name('eth')
        mac = factory.make_mac_address()
        self.assertEqual(
            {
                'id': interface,
                'type': 'ethernet',
                'ethernet_mac_address': mac,
            },
            generate_ethernet_link_entry(interface, mac))


class TestGenerateNetworkingConfig(MAASServerTestCase):

    def patch_interfaces(self, interface_mac_pairs):
        patch = self.patch_autospec(
            networking_preseed, 'extract_network_interfaces')
        patch.return_value = interface_mac_pairs
        return patch

    def test__returns_config_dict(self):
        self.patch_interfaces([])
        config = generate_networking_config(factory.make_Node())
        self.assertIsInstance(config, dict)
        self.assertEqual("MAAS", config['provider'])

    def test__includes_links(self):
        node = factory.make_Node()
        interface = factory.make_name('eth')
        mac = factory.make_mac_address()
        patch = self.patch_interfaces([(interface, mac)])

        config = generate_networking_config(node)

        self.assertThat(patch, MockCalledOnceWith(node))
        self.assertEqual(
            [
                {
                    'id': interface,
                    'type': 'ethernet',
                    'ethernet_mac_address': mac,
                },
            ],
            config['network_info']['links'])

    def test__includes_networks(self):
        # This section is not yet implemented, so expect an empty list.
        self.patch_interfaces([])
        config = generate_networking_config(factory.make_Node())
        self.assertEqual([], config['network_info']['networks'])

    def test__includes_dns_servers(self):
        # This section is not yet implemented, so expect an empty list.
        self.patch_interfaces([])
        config = generate_networking_config(factory.make_Node())
        self.assertEqual([], config['network_info']['services'])
