# -*- coding: utf-8 -*-

import sys
import os
from subprocess import Popen, PIPE
import time
import socket
import ConfigParser
from xml.dom import minidom
import xml.dom.minidom
import smtplib  
from email.mime.text import MIMEText  
import logging
import logging.handlers

def get_config(section, name):
    cfg_fn = os.path.join(os.path.dirname(os.path.abspath(__file__)) + "/rtmp_proxy.cfg")
    parser = ConfigParser.ConfigParser()
    parser.read(cfg_fn)
    return parser.get(section, name)

def get_tag_text(element, tag):
    nodes = element.getElementsByTagName(tag)
    if len(nodes) == 0:
        return ""
    else:
        node = nodes[0]
    rc = ""
    for node in node.childNodes:
        if node.nodeType in ( node.TEXT_NODE, node.CDATA_SECTION_NODE):
            rc = rc + node.data
    if rc == "true":
        return True
    elif rc == "false":
        return False
    return rc

def get_xml_tag(xml_string, tag):
    xml = minidom.parseString(xml_string)
    content = get_tag_text(xml, tag)
    return content

def runcmd(cmd, collect_output):
    proc = None
    if collect_output:
        proc = Popen(cmd, shell=True, executable="/bin/bash", stdout=PIPE, stderr=PIPE)
    else:
        proc = Popen(cmd, shell=True, executable="/bin/bash", stderr=PIPE)

    stdout, stderr = proc.communicate()
    status = proc.wait()
    
    return (status, stdout, stderr)

def init_logger(logger, filename, loglevel = logging.INFO, fmt = None):
        logger = logging.getLogger(logger)
        logger.setLevel(logging.DEBUG)

        if not fmt:
            fmt = '[%(asctime)-15s] [%(levelname)s] [%(filename)s:%(lineno)d] [%(thread)d] %(message)s'
        handler = logging.handlers.RotatingFileHandler(filename, maxBytes = 1024*1024*100, backupCount = 5)
        formatter = logging.Formatter(fmt)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

def send_mail(content):  
    mail_host = get_config('MONITOR', 'mail_host')
    mail_user = get_config('MONITOR', 'mail_user')
    mail_pass = get_config('MONITOR', 'mail_password')
    to_list = get_config('MONITOR', 'mail_to_list')

    me = "rtmp_proxy_monitor" + "<" + mail_user + ">"  
    msg = MIMEText(content, _subtype = 'plain', _charset = 'utf-8')  
    sub = 'rtmp proxy 监控事件'
    msg['Subject'] = sub
    msg['From'] = me  
    msg['To'] = to_list
    try:  
        server = smtplib.SMTP()  
        server.connect(mail_host)  
        server.login(mail_user,mail_pass)  
        server.sendmail(me, to_list, msg.as_string())  
        server.close()  
        return (True, 'send mail success')  
    except Exception, e:  
        print 'send mail failed. %s' % str(e)
        return (False, str(e))  

def get_local_ip():
    try:
        csock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        csock.connect(('8.8.8.8', 80))
        (addr, port) = csock.getsockname()
        csock.close()
        return addr
    except:
        return ""
