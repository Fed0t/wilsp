import subprocess

import gevent


class MPEGFeeder(object):
    """
    The MPEG feeder will control a ffmpeg instance, direct it through stdout pipe, and push it to redis.
    the stream in REDIS.
    """

    def __init__(self, rdb, cam_name, mjpeg_source):
        self._g = []
        self._cam_name = cam_name
        self._mjpeg_source = mjpeg_source
        self._rdb = rdb

    def _run(self):
        # Redis channel
        redis_channel = '{}/mpeg'.format(self._cam_name)

        # For debugging only.
        self._mjpeg_source = "http://cams.weblab.deusto.es/webcam/fishtank1/video.mjpeg"

        ffmpeg_command = ['/opt/local/bin/ffmpeg', '-r', '30', '-i', self._mjpeg_source, '-f', 'mpeg1video', '-b', '800k', '-r', '30', "pipe:1"]

        print("Running FFMPEG command: {}".format(ffmpeg_command))

        p = subprocess.Popen(ffmpeg_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE)

        while True:
            # TODO: Consider whether we should read in some other way.
            packet = p.stdout.read(2048)
            self._rdb.publish(redis_channel, packet)

        print("MPEG greenlet is OUT")

    def start(self):
        g = gevent.Greenlet(self._run)
        g.start()
        self._g.append(g)