#!/usr/bin/env python
# Copyright (c) 2020-2021 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2 License
# The full license information can be found in LICENSE.txt
# in the root directory of this project.
"""
App for running vmkping operations on ESX.
"""
import logging

from lydian.apps.base import exposify
import lydian.apps.console as console

log = logging.getLogger(__name__)


class VMKPingError(Exception):
    pass


@exposify
class VMKPing(console.Console):

    def __init__(self):
        super(VMKPing, self).__init__()

    def run_vmkping(self, dst_ip="", src_vmk="", netstack="vxlan", duration=10, args=''):
        """
        Run VMKPing from current ESX VMK to a given vmk

        Parameters:
        ----------
            dst_ip: str
                IP for the destination VMK
            src_vmk: str
                VMK name for the Source vmk
            netstack: str
                Netstack to be used
            duration: int
                Duration for the ping operation
        Returns:
            return_code: int
                0 for Pass else Failure
            stdout: str
                Stdout for ping operation
        """

        if dst_ip == "" or src_vmk == "":
            log.error("Destination IP or Source VMK not provided.")
            raise VMKPingError

        # Command used for reference -
        # vmkping ++netstack=vxlan -I vmk10 128.62.97.69 -c 30
        #
        # If additional changes are needed they would need to be passed into
        # the args parameter.

        cmd = "vmkping ++netstack=%s -I %s %s -c %s" % (
            netstack, src_vmk, dst_ip, duration)
        log.info("Running VMKping command - %s", cmd)
        return_code, stdout = self.run_command(cmd)
        return return_code, stdout
