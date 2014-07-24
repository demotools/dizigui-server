#!/usr/bin/env python
# coding: utf-8

import tempfile

from tornado.web import HTTPError

import handler.api
import hqby.image
import hqby.auth
from hqby.config import configs
import model.user


def url_spec(**kwargs):
    return [
        (r'/image/?([\w\-]+)?', ImageHandler),
    ]

class ImageHandler(handler.api.ApiHandler):
    """（临时）图片处理"""

    WIDTH_RANGE = [50, 5000]
    HEIGHT_RANGE = [50, 5000]
    MAX_UPLOAD_SIZE = 1024 * 1024 * 5

    @handler.api.token_required(True)
    def post(self, *args, **kwargs):
        uid = kwargs['uid']
        #uid = 'wmW8yaHH'
        file_key = 'ax_file_input' if 'ax_file_input' in self.request.files else 'image'
        try:
            img_data = self.request.files[file_key][0]['body']
        except KeyError:
            img_data = self.request.files[file_key+'[]'][0]['body']
        #TODO: Upload tmp image
        if len(img_data) > self.MAX_UPLOAD_SIZE:
            raise HTTPError(413)
        try:
            refer_type = self.get_argument('refer_type').upper()
        except Exception:
            refer_type = 'ITEM'
        tmp_file = tempfile.TemporaryFile()
        tmp_file.write(img_data)
        tmp_file.seek(0)
        try:
            img = hqby.image.create_temp_image(tmp_file, refer_type, uid)
        except IOError as ex:
            raise HTTPError(500, str(ex))
        finally:
            tmp_file.close()
        img['class'] = 'image_upload'
        img['_id'] = img.pop('id')
        # 传文件插件使用的字段
        if file_key == 'ax_file_input':
            img['status'] = 1
            img['info'] = u'成功'
            img['name'] = img['_id']
        self.write(img)
        self.set_status(200)
        self.set_header('Content-Type', 'text/plain')

    def get(self, *args, **kwargs):
        token = self._get_token(False)
        uid = token['_id'] if token else 'anonymous'
        #uid = 'wmW8yaHH'
        if not uid:
            raise HTTPError(403)
        if not args[0]:
            raise HTTPError(400)
        row = hqby.image.get_temp_image(args[0])
        if not row:
            raise HTTPError(404)
        img = row['image']
        img['_id'] = img.pop('id', row['id'])
        img['class'] = 'image_upload'
        self.write(img)

