
1. 安装oss python sdk
    下载：https://github.com/aliyun/aliyun-oss-python-sdk
    文档：https://help.aliyun.com/document_detail/32026.html?spm=5176.doc31890.6.227.IS3jWM

2. 安装mns python sdk
    下载：http://docs-aliyun.cn-hangzhou.oss.aliyun-inc.com/assets/attach/32305/cn_zh/1473754989466/aliyun-mns-python-sdk-1.1.3.zip?spm=5176.doc32305.2.1.BzuvcS&file=aliyun-mns-python-sdk-1.1.3.zip

    文档：https://help.aliyun.com/document_detail/32305.html?spm=5176.product27412.6.203.CkRdkC

3.  配置ffmpeg 
    https://ffmpeg.org/releases/ffmpeg-3.0.5.tar.gz
	执行完./configure后，需要修改配置文件：
	config.mak: HAVE_TERMIOS_H=yes -->  !HAVE_TERMIOS_H=yes
	config.h: #define HAVE_TERMIOS_H 1 --> #define HAVE_TERMIOS_H 0
	然后 make & make install

4. 配置 rtmp_proxy.cfg 文件
    
5. 运行： python rtmp_proxy.py &

6. 配置日志监控： 
    网址：https://sls.console.aliyun.com/#/
    日志位置： logs/rtmp_access.log
    日志格式：time|url|status|error_message

7. 配置其他监控：
    执行 crontab -e 增加定时任务：
    */10 * * * * cd /xxxx/rtmp_proxy; python rtmp_proxy_monitor.py --exec_name rtmp_proxy.py &> /dev/null &


6. 查看日志：logs/rtmp_proxy.log  logs/rtmp_access.log


