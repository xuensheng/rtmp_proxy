# -*- coding: utf-8 -*-
import os
import time
import base64
import urllib
import urlparse
import threading
import thread
import fcntl
import logging
import logging.handlers
from subprocess import Popen, PIPE
import oss2
from mns.account import Account
from mns.queue import *
from common import *

class RtmpProxy:
    def __init__(self):
        self.set_logger()
        #加载阿里云相关配置
        self.mns_endpoint = get_config("MNS", "mns_endpoint");
        self.mns_access_id = get_config("MNS", "mns_access_id");
        self.mns_access_key = get_config("MNS", "mns_access_key");
        self.mns_queue_name = get_config("MNS", "mns_queue_name");

        self.oss_endpoint = get_config("OSS", "oss_endpoint");
        self.oss_access_id = get_config("OSS", "oss_access_id");
        self.oss_access_key = get_config("OSS", "oss_access_key");
        self.oss_bucket_name = get_config("OSS", "oss_bucket_name");

        #加载rtmp相关配置
        self.max_stream_count = int(get_config("Base", "max_stream_count")); 
        self.max_retries = 3

        #初始化 msn account, queue
        self.mns_account = Account(self.mns_endpoint, self.mns_access_id, self.mns_access_key)
        self.mns_queue = self.mns_account.get_queue(self.mns_queue_name)
        self.mns_queue.set_encoding(False)

        self.publish_count = 0
        self.publish_mutex = threading.Lock()

        self.bucket = oss2.Bucket(oss2.Auth(self.oss_access_id, self.oss_access_key), self.oss_endpoint, self.oss_bucket_name)

    def set_logger(self):
        self.access_logger = init_logger('access', 'logs/rtmp_access.log', fmt = '%(asctime)-15s|%(message)s')
        self.logger = init_logger('', 'logs/rtmp_proxy.log', self.get_loglevel())

    def get_loglevel(self):
        log_level = get_config("Base", "log_level");
        if log_level == "debug":
            return logging.DEBUG;
        elif log_level == "info":
            return logging.INFO;
        elif log_level == "warning":
            return logging.WARNING;
        elif log_level == "error":
            return logging.ERROR;
        return logging.INFO

    def main_loop(self):
        while True:
            try:
                while self.publish_count >= self.max_stream_count:
                    logging.error("exceed the max stream count, count: %d/%d" % (self.publish_count, self.max_stream_count))
                    self.print_access_log('-', 'fail', 'exceed the max stream count')
                    time.sleep(5)
                    logging.info("waiting for receive message")
                recv_msg = self.mns_queue.receive_message(3)
                try:
                    self.process_msg(recv_msg)
                except Exception,e:
                    logging.error("Process Message Fail! Exception:%s" % e)
            except MNSExceptionBase,e:
                if e.type == "QueueNotExist":
                    logging.error("Queue not exist, please create queue before receive message.")
                    sys.exit(0)
                elif e.type == "MessageNotExist":
                    logging.debug("Queue is empty!")
                    continue
                else :
                    logging.warning("Receive Message Fail! Exception:%s" % e)
                    continue
            except Exception,e:
                logging.error("Receive Message Fail! Exception: %s" % (e))
                continue

            try:
                self.mns_queue.delete_message(recv_msg.receipt_handle)
                logging.debug("Delete Message Succeed!  ReceiptHandle:%s" % recv_msg.receipt_handle)
            except MNSExceptionBase,e:
                logging.error("Delete Message Fail! Exception:%s" % e)
            except Exception,e:
                logging.error("Delete Message Fail! Exception: %s" % (e))

    def get_push_url(self, channel_id):
        expires = 600
        return self.bucket.sign_rtmp_url(channel_id, 'playlist.m3u8', expires)

    def get_channel_id(self, pull_url):
        proto, rest = urllib.splittype(pull_url)
        host, path = urllib.splithost(rest)
        paths = path.split('/')
        last_path = paths[len(paths) - 1]
        suffix = os.path.splitext(last_path)[1]
        if suffix == ".flv":
            #if url == www.abc.com/live/abcdefg.flv
            #return abcdefg
            return os.path.splitext(last_path)[0]
        elif suffix == ".m3u8":
            #if url == www.abc.com/live/abcdefg/playlist.m3u8
            #return abcdefg
            return paths[len(paths) - 2]
        else :
            return last_path

    def create_live_channel(self, channel_id, desc):
        for i in range(self.max_retries):
            try:
                create_result = self.bucket.create_live_channel(
                    channel_id,
                    oss2.models.LiveChannelInfo(
                        status = 'enabled',
                        description = desc,
                        target = oss2.models.LiveChannelInfoTarget(
                        playlist_name = 'playlist.m3u8',
                        frag_count = 12,
                        frag_duration = 5)))
                return True
            except Exception as e:
                logging.error("create_live_channel: %s failed. Exception: %s" % (channel_id, e))
        return False

    def print_access_log(self, pull_url, status, err_msg = '-'):
        self.access_logger.error('%s|%s|%s' % (pull_url, status, err_msg))

    def publish_stream(self, pull_url):
        channel_id = self.get_channel_id(pull_url)
        desc = "pull from %s" % pull_url
        if not self.create_live_channel(channel_id, desc):
            self.print_access_log(pull_url, 'fail', 'create live channel failed')
            return
        push_url = self.get_push_url(channel_id)
        if (self.publish_mutex.acquire()):
            self.publish_count += 1
            self.publish_mutex.release()

        try:
            thread.start_new_thread(self.do_publish, (channel_id, pull_url, push_url));
        except Exception as e:
            logging.error("start new thread failed. channel: %s Exception: %s" % (channel_id, e))
            self.print_access_log(pull_url, 'fail', 'start new thread failed')

    def run_ffmpeg(self, channel_id, pull_url, push_url):
        publish_cmd = 'ffmpeg -loglevel 24 -stats -i %s -c copy -bsf:a aac_adtstoasc -f flv "%s"' % (pull_url, push_url)
        logging.info("publish cmd is %s" % publish_cmd)

        ret = -1
        for i in range(self.max_retries):
            try:
                proc = Popen(publish_cmd, shell=True, executable="/bin/bash", stdout=PIPE, stderr=PIPE)

                flags = fcntl.fcntl(proc.stdout.fileno(), fcntl.F_GETFL)
                fcntl.fcntl(proc.stdout.fileno(), fcntl.F_SETFL, flags | os.O_NONBLOCK)

                flags = fcntl.fcntl(proc.stderr.fileno(), fcntl.F_GETFL)
                fcntl.fcntl(proc.stderr.fileno(), fcntl.F_SETFL, flags | os.O_NONBLOCK)

                last_report_time = time.time()
                while proc.poll() == None:
                    try:
                        logging.debug("channel[%s]: %s" % (channel_id, proc.stdout.readline()))
                        last_report_time = time.time()
                    except:
                        if time.time() - last_report_time > 60:
                            #ffmpeg may be hungup, terminate it.
                            proc.terminate()
                        time.sleep(1)

                    try:
                        logging.info("channel[%s]: %s" % (channel_id, proc.stderr.readline()))
                        last_read_time = time.time()
                    except:
                        #do nothing
                        continue

                #save the return code
                ret = proc.returncode

                #save the log
                while True:
                    try:
                        line = proc.stdout.readline()
                        if not line:
                            break;
                        logging.debug("channel[%s]: %s" % (channel_id, line))
                    except:
                        break

                while True:
                    try:
                        line = proc.stderr.readline()
                        if not line:
                            break;
                        logging.info("channel[%s]: %s" % (channel_id, line))
                    except:
                        break
                
                #get ffmpeg return code
                ret = proc.returncode
                if ret != 0:
                    logging.error("publish ret: %d, cmd %s, retry..%d" % (ret, publish_cmd, i))
                    continue
                else :
                    logging.info("publish success, cmd %s" % (publish_cmd))
                    break
            except Exception as e:
                logging.error("run ffmpeg failed. exception: %s" % e)
                ret = -1
        return ret

    def do_publish(self, channel_id, pull_url, push_url):
        #run ffmpeg
        start_time = int(time.time()) - 60;
        ret = self.run_ffmpeg(channel_id, pull_url, push_url)
        if ret == 0:
            #waiting for serval seconds
            time.sleep(10)

            #generate vod.m3u8
            end_time = int(time.time()) + 60
            for i in range(self.max_retries):
                try:
                    self.bucket.post_vod_playlist(channel_id,
                                                  'vod.m3u8',
                                                  start_time = start_time,
                                                  end_time = end_time)
                    play_list = 'http://' + self.oss_bucket_name + '.' + self.oss_endpoint + '/' + channel_id + '/' + 'vod.m3u8'
                    logging.info("generate vod playlist success, pull_url: %s plasylist: %s" % (push_url, play_list))
                    self.print_access_log(pull_url, 'success')
                    break
                except Exception as e:
                    logging.error("post_vod_playlist: %s Failed. Exception: %s" % (channel_id, e))
                    self.print_access_log(pull_url, 'fail', 'generate paly list failed')
        else:
            self.print_access_log(pull_url, 'fail', 'run ffmpeg failed')
            
        if (self.publish_mutex.acquire()):
            self.publish_count -= 1
            self.publish_mutex.release()

    def process_msg(self, msg):
        start_time = time.time()
        logging.info("Receive Message Succeed! ReceiptHandle:%s MessageBody:%s MessageID:%s" % (msg.receipt_handle, msg.message_body, msg.message_id))
        pull_url = msg.message_body
        logging.info("the rtmp url:%s, count: %d/%d" % (pull_url, self.publish_count, self.max_stream_count))
        pull_url = urllib.unquote(pull_url)
        self.publish_stream(pull_url)
        interval = time.time() - start_time
        logging.info("the rtmp url:%s, used: %d" % (pull_url, interval))

    def run(self):
        while True:
            try:
                self.main_loop()
            except Exception as e:
                logging.error("Exception: %s" % (e))

if __name__ == '__main__':
    RtmpProxy().run()
