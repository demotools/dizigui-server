# coding: utf-8


def token_encode(data):
    return '%s|%s' % (data['_id'], data['uno'])


def token_decode(data):
    data = data.split('|')
    return {'_id': data[0], 'uno': data[1]}
