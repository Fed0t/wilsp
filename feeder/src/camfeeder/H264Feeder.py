import subprocess
import gevent

import config


class H264Feeder(object):
    """
    The H264 feeder will control a ffmpeg instance, direct it through stdout pipe, and push it to redis.
    the stream in REDIS. An MJPEG source from the webcam is currently REQUIRED.
    """

    def __init__(self, rdb, cam_name, mjpeg_source):
        self._g = []
        self._cam_name = cam_name
        self._mjpeg_source = mjpeg_source
        self._rdb = rdb

        self._ffmpeg_bin = config.FFMPEG_BIN

    def _run(self):
        # Redis channel
        redis_channel = '{}/h264'.format(self._cam_name)

        # For debugging only.
        # self._mjpeg_source = "http://cams.weblab.deusto.es/webcam/fishtank1/video.mjpeg"

        ffmpeg_command = [self._ffmpeg_bin, '-r', '30', '-f', 'mjpeg', '-i', self._mjpeg_source, '-c:v', 'libx264', '-r', '30', "-f", "h264", "pipe:1"]

        print("Running FFMPEG command: {}".format(ffmpeg_command))

        p = subprocess.Popen(ffmpeg_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE)

        while True:
            # TODO: Consider whether we should read in some other way.
            packet = p.stdout.read(2048)
            self._rdb.publish(redis_channel, packet)

        print("H.264 greenlet is OUT")

    def start(self):
        g = gevent.Greenlet(self._run)
        g.start()
        self._g.append(g)