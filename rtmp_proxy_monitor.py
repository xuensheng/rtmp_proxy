# -*- coding: utf-8 -*-
import os
import sys
from optparse import OptionParser
from common import *

class Moniotor:
    def __init__(self, options):
        self.options = options

    def get_pid_from_file(self):
        try:
            with open('.rtmp_proxy.pid', 'r', 0) as fh:
                pid = fh.readline()
                fh.close()
                return pid
        except:
            return ""

    def record_pid(self, pid):
        try:
            f = open('.rtmp_proxy.pid', 'w')  
            f.write(pid)  
            f.close()
        except:
            pass

    def get_process_pid(self, exec_name):
        cmd = 'ps -eo pid,cmd | grep "%s" | grep -v grep | grep -v rtmp_proxy_monitor | grep -v log | grep -v vi | awk \'{ printf $1; exit }\'' % (exec_name)
        out = os.popen(cmd).read()
        return out;

    def monitor_process(self):
        cur_pid = self.get_process_pid(self.options.exec_name)
        if not cur_pid:
            #not running
            print '%s not running' % self.options.exec_name
            send_mail('%s %s is not running. machine IP: %s' %
                (time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())), 
                 self.options.exec_name,
                 get_local_ip()))

        old_pid = self.get_pid_from_file()
        if old_pid == "":
           self.record_pid(cur_pid)
        elif cur_pid != old_pid:
            #process restart
            print '%s restarted' % self.options.exec_name
            send_mail('%s %s restarted. machine IP: %s' %
                (time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())), 
                 self.options.exec_name,
                 get_local_ip()))

            self.record_pid(cur_pid)

    def run(self):
        self.monitor_process()

def parse_arguments():
    parser = OptionParser()
    parser.add_option("-e", "--exec_name", action="store", dest="exec_name", default='rtmp_proxy.py')
    (options, args) = parser.parse_args()
    return options

if __name__ == '__main__':
    options = parse_arguments()
    Moniotor(options).run()
