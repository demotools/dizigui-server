import datetime
import os.path
import subprocess
import logging
import Image
import ImageStat
import ImageEnhance
from threading import Thread


IMG_BRIGHT = 140.0
MAX_EM = 1.3


class AudioConvertThread(Thread):

    def __init__(self, f):
        Thread.__init__(self)
        self.audio = f

    def run(self):
        logging.info('[Audio Info]: begin convert file - %s' % self.audio)
        try:
            success = amr2mp3(self.audio)
            if success:
                logging.info('[Auido Info]: conver success')
            else:
                raise Exception
        except Exception as ex:
            logging.error('[Audio Error]: convert file to mp3 Failed - %s' % str(ex))


def to_str(d, format='%Y-%m-%d %H:%M:%S'):
    return d.strftime(format)


def to_date(s, format='%Y-%m-%d %H:%M:%S'):
    return datetime.datetime.strptime(s, format)


def amr2mp3(amr_path, mp3_path=None):
    """ convert amr to mp3 just amr file to mp3 file
    """
    path, name = os.path.split(amr_path)
    if name.split('.')[-1] != 'amr':
        logging.error('Not a amr file exist!!')
        return 0
    if mp3_path is None or mp3_path.split('.')[-1] != 'mp3':
        mp3_path = os.path.join(path, name + '.mp3')
    error = subprocess.call(['ffmpeg', '-i', amr_path, mp3_path])  # success return status 0
    if error:
        logging.error('[Convert Error]:Convert file-%s to mp3 failed' % amr_path)
        return 0
    return mp3_path


def get_bright(img_path=None, img=None):
    """ get image brightness """
    assert (img_path is not None or img is not None)
    img = img if img else Image.open(img_path)
    img = img.convert('L')
    stat = ImageStat.Stat(img)
    return stat.rms[0]


def adjust_bright(img_path=None, img=None):
    assert (img_path is not None or img is not None)
    img = Image.open(img_path) if img_path else img
    bright = get_bright(img=img)
    if bright < IMG_BRIGHT and int(bright):
        br = ImageEnhance.Brightness(img)
        em = IMG_BRIGHT / bright
        if em > MAX_EM:
            em = MAX_EM
        return br.enhance(em)
    return img
