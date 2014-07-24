#!/usr/bin/env python
# coding: utf-8

import tempfile

from tornado.web import HTTPError

import handler.api
import hqby.audio
import hqby.auth
from hqby.config import configs
import model.user
import logging


def url_spec(**kwargs):
    return [
        (r'/audio/?([\w\-]+)?', AudioHandler),
    ]


class AudioHandler(handler.api.ApiHandler):
    """（临时）音频处理"""

    MAX_UPLOAD_SIZE = 1024 * 1024 * 5

    def post(self, *args, **kwargs):
        token = self._get_token()
        uid = token['_id']
        if not(model.user.get_user(user_id=uid)):
            raise HTTPError(404, 'can not found this user')
        file_key = 'ax_file_input' if 'ax_file_input' in self.request.files else 'audio'
        audio_data = self.request.files[file_key][0]['body']
        upload_filename = self.request.files[file_key][0]['filename']
        name_ext = upload_filename.split('.')
        audio_type = 'amr' if len(name_ext) < 2 else name_ext[-1]  # for web
        if audio_type != 'amr' and not configs['test_mode']:
            raise HTTPError(500, 'audio type must be amr')
        try:
            audio_len = self.get_argument('len').upper()
        except Exception:
            audio_len = 60  # for web
        #TODO: Upload tmp audio
        if len(audio_data) > self.MAX_UPLOAD_SIZE:
            raise HTTPError(413, 'audio too long')
        tmp_file = tempfile.TemporaryFile()
        tmp_file.write(audio_data)
        tmp_file.seek(0)
        try:
            audio = hqby.audio.create_temp_audio(tmp_file, audio_type, audio_len, uid)
        except IOError as ex:
            raise HTTPError(400, 'audio io error')
        finally:
            tmp_file.close()
        audio['class'] = 'audio_upload'
        audio['_id'] = audio.pop('id')
        # 前端传文件插件额外信息
        if file_key == 'ax_file_input':
            audio['status'] = 1
            audio['name'] = audio['_id']
        self.write(audio)
        self.set_status(200)
        self.set_header('Content-Type', 'text/plain')

    def get(self, *args, **kwargs):
        token = self._get_token(False)
        uid = token['_id'] if token else 'anonymous'
        if not uid:
            raise HTTPError(403)
        if not args[0]:
            raise HTTPError(400)
        row = hqby.audio.get_temp_audio(args[0])
        if not row:
            raise HTTPError(404)
        audio = row['audio']
        audio['_id'] = audio.pop('id', row['id'])
        audio['class'] = 'audio_upload'
        self.write(audio)
