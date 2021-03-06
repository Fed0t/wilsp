import traceback

import gevent
from gevent import monkey
monkey.patch_all()

import requests
import redis
import time

from feeder.base import CamFeeder


class FrameGrabbingException(Exception):
    def __init__(self, msg, cause=None):
        super().__init__(msg, cause)


class ImageRefreshCamFeeder(CamFeeder):
    """
    The ImageRefreshCamFeeder retrieves images by simply repeteadly requesting the image URL of the camera.
    (Most IP cameras provide such an URL).
    """

    REQUEST_TIMEOUT = 15

    def __init__(self, rdb: redis.StrictRedis, redis_prefix: str, cam_name: str, url: str, max_fps: int,
                 rotation: float = None):
        super().__init__(rdb, redis_prefix, cam_name, url, max_fps, rotation)

        self.rsess = requests.session()
        self.rsess.keep_alive = False

        if max_fps <= 0:
            raise Exception('0 is not an acceptable max_fps')

    def _run_until_inactive(self):
        """
        Will just keep pushing images and checking the active status until
        the camera should not be active anymore.
        :return:
        """
        fails = 0
        while self._active:

            update_start_time = time.time()
            try:
                frame = self._grab_frame()
                frame = self._rotated(frame, self._rotation)
                self._put_frame(frame)
            except Exception as exc:
                fails += 1
                print("Failed to grab frame. Failed frames: {}".format(fails))
                # traceback.print_exc()

            self._check_active()

            elapsed = time.time() - update_start_time
            intended_period = 1 / self._max_fps  # That's the approximate time a frame should take.

            time_left = intended_period - elapsed
            # print("Time left: {}".format(time_left))
            if time_left < 0:
                # We are simply not managing to keep up with the intended frame rate, but for this
                # cam feeder, that is not a (big) problem.
                gevent.sleep(0)
            else:
                gevent.sleep(time_left)

            # gevent.sleep(0)

    def _grab_frame(self) -> bytes:
        """
        Grabs a frame. It will use the specified URL. Some special protocols may eventually be supported.
        :return:
        """
        try:
            r = self.rsess.get(self._url, stream=True, timeout=ImageRefreshCamFeeder.REQUEST_TIMEOUT)
            # print("[dbg] {}".format([r.status_code, r.text, self._url, r.url]))
            if r.status_code != 200:
                raise FrameGrabbingException("Status code is not 200")
            content = r.content
            if len(content) < 100:
                raise FrameGrabbingException("Retrieved content is too small")
            return content
        except FrameGrabbingException:
            raise
        except Exception as exc:
            raise FrameGrabbingException("Exception occurred", exc)
