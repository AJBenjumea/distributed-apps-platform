#!/usr/bin/env python
# Copyright (c) 2020-2021 VMware, Inc. All Rights Reserved.
# SPDX-License-Identifier: BSD-2 License
# The full license information can be found in LICENSE.txt
# in the root directory of this project.
"""
App for running netperf server or client.
"""
import logging
import random
import time

from lydian.apps.base import exposify
import lydian.apps.console as console

log = logging.getLogger(__name__)


@exposify
class Netperf(console.Console):

    _START_RAND_PORT = 5600
    _END_RAND_PORT = 6000
    _STARTING_JOB_ID = 1000

    def __init__(self):
        super(Netperf, self).__init__()
        # {<port>: <popen obj>}
        self._server_handles = {}

        # {<job_id>: {'popen_obj': <popen obj>,
        #             'state': 'running' | 'done',
        #             'result': < None | JSON output>,
        #             'cmd': <command>
        #             }
        self._client_handles = {}
        self._job_id = None
        self._gen_rand_port = self._gen_rand_port(self._START_RAND_PORT,
                                                  self._END_RAND_PORT)

    def start_netperf_server(self, netserver_bin, server_ip=None, port=None, args=''):
        """
        Start netperf server on given port. If port is not
        provided, random port will be used.

        Parameters:
        ----------
            server_ip: str
                Ip on which server should be listening
            port: int
                Port number (default: None)
            args: str
                Additional netperf supported args
            netserver_bin: str
                netperf bin file path (e.g. netserver, /automation/bin/x86_64/linux/netserver)
        Returns:
            port: int
                Port number being used for netperf server
        """
        if not port:
            port = next(self._gen_rand_port)
        if self.is_running(port):
            log.info("Server is already running on port: %d Skip starting server.", port)
            return port
        if server_ip:
            cmd = netserver_bin + ' -L %s' % server_ip
        else:
            cmd = netserver_bin
        cmd += ' -p %s' % str(port)
        if args:
            cmd += ' ' + args
        log.info("Starting Netperf Server on port:%d with '%s'", port, cmd)
        p = self._start_subprocess(cmd)
        # Check server is running
        for _ in range(3):
            if self.is_running(port):
                self._server_handles[port] = p
                log.info("Running Netperf Server on port:%d with '%s'", port, cmd)
                break
            time.sleep(1)
        else:
            msg = "unable to start netperf server. check port:%d is available." % port
            log.error(msg)
            raise RuntimeError(msg)
        return port

    def _gen_rand_port(self, start_port, end_port):

        for _ in range(start_port, end_port + 1):
            port = random.randint(start_port, end_port)
            if port not in self._server_handles:
                yield port
        msg = "Running out of random port between starting port: %d - \
              ending port: %d" % (start_port, end_port)
        log.error(msg)
        raise ValueError(msg)

    def get_server_ports(self):
        """
        Get running server ports.
        :return:
        list of currently running server ports
        """
        return list(self._server_handles.keys())

    def stop_netperf_server(self, port):
        """
        Stop netperf server for given port.
        """
        proc = self._server_handles.get(port)
        if proc:
            self._kill_subprocess(proc)
            self._server_handles.pop(port)

            # TODO: In netperf when it returns the process ID, it is always 2 less than the actual process ID,
            # and hence we should add 2 to the result. As per handling present in vdnet.
            proc.pid += 2
            # Alternate approach to above, if required in future.
            # cmd = "kill -9 $(sudo lsof -t -i:%d)" % port
            # p = self._start_subprocess(['bash', '-c', cmd])
            # op, err = p.communicate()
            self._kill_subprocess(proc)

    def stop_netperf_client(self, job_id):
        """
        Stop netperf client for given job_id.
        """
        job = self._client_handles.get(job_id)
        if job:
            self._kill_subprocess(job.get('popen_obj'))
            self._client_handles.pop(job_id)

    def start_netperf_client(self, dst_ip, dst_port, netperf_bin, src_ip=None,
                             src_port=None, duration=10, udp=False,
                             message_size=None, args=''):
        """
        Start netperf client to given dst_ip and port.

        Parameters:
        -----------
            dst_ip: str
                IP address of netperf server
            dst_port: int
                netperf server port to connect to
            src_ip: str
                IP address of netperf client
            src_port: int
                netperf client port to connect to
            duration: int
                test duration
            udp: bool
                enable udp
            message_size: int
                size of message in bytes.
            args: str
                additional args supported by netperf client command
            netperf_bin: str
                netperf bin file path (e.g. netperf, /usr/bin//automation/bin/x86_64/linux/netperf)
        Returns:
            job_id: int
        """
        cmd = netperf_bin + ' -H %s' % (str(dst_ip))
        if src_ip:
            cmd += ' -L %s' % (str(src_ip))
        cmd += ' -p %d' % dst_port
        if src_port:
            cmd += ',%d' % src_port
        cmd += ' -l %d' % duration
        if udp:
            cmd += " -t UDP_STREAM"
        else:
            cmd += " -t TCP_STREAM"
        if args:
            cmd += ' ' + args
        if message_size:
            if '--' in cmd:
                cmd += " -m %d" % message_size
            else:
                cmd += " -- -m %d" % message_size
        p = self._start_subprocess(cmd)
        self._job_id = self._STARTING_JOB_ID if not self._job_id \
            else self._job_id + 1

        self._client_handles[self._job_id] = {'popen_obj': p,
                                              'state': 'running',
                                              'result': None,
                                              'cmd': cmd}
        log.info("Running netperf client job(%s) with command (%s).",
                 self._job_id, cmd)
        return self._job_id

    def get_client_jobs(self):
        return list(self._client_handles.keys())

    def get_client_job_info(self, job_id):
        """
        Get client job info on given job id.

        :param job_id: (int)
        :return:
        job_details: (dict)
            # {'popen_obj': <popen obj>,
            #  'state': 'running' | 'done',
            #  'result': < None | JSON output>,
            #  'cmd': <command>
            # }
        """
        if job_id not in self._client_handles:
            log.error("Job ID:%d not found", job_id)
            return None
        p = self._client_handles[job_id].get('popen_obj')
        if not self._is_alive(p):
            if self._client_handles[job_id].get('result') is None:
                result = p.communicate()[0].decode('utf-8')
                self._client_handles[job_id]['result'] = result
            self._client_handles[job_id]['state'] = 'done'

        return self._client_handles[job_id]

    def stop(self):
        """
        Stop netperf app.
        """
        server_ports = self.get_server_ports()
        client_jobs = self.get_client_jobs()

        for port in server_ports:
            log.info("Stopping netperf server on port %s", port)
            self.stop_netperf_server(port)

        for job_id in client_jobs:
            log.info("Stopping netperf client process for job: %s", job_id)
            self.stop_netperf_client(job_id)

    def is_running(self, port):
        """
        Check netperf server is running on given port
        """
        netstat = self._start_subprocess('netstat -lnp')
        grep = self._start_subprocess('grep :%s' % port, stdin=netstat.stdout)
        netstat.stdout.close()  # Allow netstat to receive a SIGPIPE if grep exits.
        output = grep.communicate()[0].decode('utf-8')
        return 'netserver' in output
