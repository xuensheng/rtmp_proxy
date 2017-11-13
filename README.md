
1. 安装oss python sdk
    下载：https://github.com/aliyun/aliyun-oss-python-sdk
    文档：https://help.aliyun.com/document_detail/32026.html?spm=5176.doc31890.6.227.IS3jWM

2. 安装mns python sdk
    下载：http://docs-aliyun.cn-hangzhou.oss.aliyun-inc.com/assets/attach/32305/cn_zh/1473754989466/aliyun-mns-python-sdk-1.1.3.zip?spm=5176.doc32305.2.1.BzuvcS&file=aliyun-mns-python-sdk-1.1.3.zip

    文档：https://help.aliyun.com/document_detail/32305.html?spm=5176.product27412.6.203.CkRdkC

3.  配置ffmpeg 

    https://ffmpeg.org/releases/ffmpeg-3.0.5.tar.gz
	执行完./configure后，需要修改配置文件：
	<pre><code>
	config.mak: HAVE_TERMIOS_H=yes -->  !HAVE_TERMIOS_H=yes
	config.h: #define HAVE_TERMIOS_H 1 --> #define HAVE_TERMIOS_H 0
	</code></pre>

    打上如下补丁：
	<pre><code>
	diff --git a/ffmpeg-3.0.5-org/ffmpeg.c b/ffmpeg-3.0.5/ffmpeg.c
	index 4d1a972..926494b 100644
	--- a/ffmpeg-3.0.5-org/ffmpeg.c
	+++ b/ffmpeg-3.0.5/ffmpeg.c
	@@ -1659,7 +1659,7 @@ static void print_report(int is_last_report, int64_t timer_start, int64_t cur_ti
	     if (print_stats || is_last_report) {
		 const char end = is_last_report ? '\n' : '\r';
		 if (print_stats==1 && AV_LOG_INFO > av_log_get_level()) {
	-            fprintf(stderr, "%s    %c", buf, end);
	+            fprintf(stderr, "%s    %c", buf, '\n');
		 } else
		     av_log(NULL, AV_LOG_INFO, "%s    %c", buf, end);


		然后 make & make install
	</code></pre>

4. 配置 rtmp_proxy.cfg 文件
    
5. 运行： python rtmp_proxy.py &

6. 配置日志监控： 
    监控推流的情况
    阿里云日志服务网址：https://sls.console.aliyun.com/#/
    访问日志位置： logs/rtmp_access.log
    日志格式：time|url|status|error_message

7. 配置其他监控：

    执行 crontab -e 增加定时任务, 每十分钟执行一次, 例如：
    */10 * * * * cd /home/rtmp_proxy; python rtmp_proxy_monitor.py --exec_name rtmp_proxy.py &> /dev/null &


6. 查看日志：
运行日志：logs/rtmp_proxy.log  
访问日志：logs/rtmp_access.log

7. 资源占用：
ECS测试： 以540kbps码率流为例， 单路流占用内存：10MB  CPU: 0.4%


