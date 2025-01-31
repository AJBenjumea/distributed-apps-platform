#!/usr/bin/env python
# Copyright (c) 2019 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2 License
# The full license information can be found in LICENSE.txt
# in the root directory of this project.


import logging
from queue import Queue

import rpyc
from rpyc.utils.server import ThreadPoolServer

from lydian.apps import config
from lydian.apps.interface import InterfaceApp
from lydian.apps.internal.hostinfo import HostInfo
from lydian.apps.iperf import Iperf
from lydian.apps.netperf import Netperf
from lydian.apps.mocktraffic import MockTraffic
from lydian.apps.monitor import ResourceMonitor
from lydian.apps.namespace import NamespaceApp
from lydian.apps.pentest.lynis import Lynis
from lydian.apps.recorder import RecordManager
from lydian.apps.results import Results
from lydian.apps.rules import RulesApp
from lydian.apps.tcpdump import TCPDump
from lydian.apps.pentest.rapidscan import Rapidscan
from lydian.apps.traffic_controller import TrafficControllerApp
from lydian.apps.watch.threat import ThreatMonitor
from lydian.apps.vmkping import VMKPing
from lydian.utils import logger, common


rpyc.core.protocol.DEFAULT_CONFIG['allow_pickle'] = True


class LydianServiceBase(rpyc.Service):

    RPYC_PROTOCOL_CONFIG = rpyc.core.protocol.DEFAULT_CONFIG

    def __init__(self):
        super(LydianServiceBase, self).__init__()

    def on_connect(self, conn):
        print("Connected to %r", conn)

    def on_disconnect(self, conn):
        print("Disconnected from %r", conn)


class LydianService(LydianServiceBase):
    RECORD_QUEUE_SIZE = 50000

    EXPOSED = [
        'configs',
        'controller',
        'hostinfo',
        'interface',
        'iperf',
        'lynis',
        'monitor',
        'namespace',
        'rapidscan',
        'results',
        'rules',
        'tcpdump',
        'threatmonitor',
        'vmkping',
        'netperf'
    ]

    def __init__(self):
        super(LydianService, self).__init__()

        self._traffic_records = Queue(self.RECORD_QUEUE_SIZE)
        self._resource_records = Queue(self.RECORD_QUEUE_SIZE)

        self.recorder = RecordManager(self._traffic_records,
                                      self._resource_records)

        self.hostinfo = HostInfo()
        self.namespace = NamespaceApp()
        self.interface = InterfaceApp()
        self.rules = RulesApp()

        # Third party traffic generators.
        self.mocktraffic = MockTraffic(self._traffic_records)

        self._traffic_tools = {
            'mock': self.mocktraffic
        }

        # Traffic Controller
        self.controller = TrafficControllerApp(self._traffic_records,
                                               self.rules, self._traffic_tools)
        self.monitor = ResourceMonitor(self._resource_records)
        self.tcpdump = TCPDump()
        self.iperf = Iperf()
        self.netperf = Netperf()
        self.vmkping = VMKPing()
        self.results = Results()
        self.configs = config.get_configs()

        self.lynis = Lynis()
        self.threatmonitor = ThreatMonitor()
        self.rapidscan = Rapidscan()

        self.expose()

    def expose(self):
        for key in self.EXPOSED:
            setattr(self, 'exposed_' + key, getattr(self, key))

    def start(self):
        try:
            self.monitor.start()
            self.recorder.start()
        except Exception as err:
            self.logger.exception("Error in starting Services %r", err)

    def stop(self):
        try:
            self.monitor.stop()
            self.recorder.stop()
        except Exception as err:
            self.logger.exception("Error while stopping Services %r", err)


class LydianController(object):

    LYDIAN_PORT = config.get_param('LYDIAN_PORT')

    def __init__(self):
        self.service = LydianService()
        self.lydian_port = self.LYDIAN_PORT
        self.protocol_config = self.service.RPYC_PROTOCOL_CONFIG
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.WARN)
        self.lydian_service = ThreadPoolServer(
            self.service,
            port=self.lydian_port,
            reuse_addr=True,
            protocol_config=self.protocol_config,
            logger=self.logger, nbThreads=50)

        if not common.is_port_already_in_use(self.lydian_port):
            common.write_pid_file('/var/run/lydian.pid')

    def start(self):
        self.service.start()
        self.lydian_service.start()

    def stop(self):
        self.service.stop()
        self.lydian_service.close()


def main():
    logger.setup_logging(log_dir=config.get_param('LOG_DIR'),
                         log_file=config.get_param('LOG_FILE'))
    lydian_service = LydianController()
    lydian_service.start()


if __name__ == '__main__':
    main()
