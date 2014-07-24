#!/usr/bin/env python
#coding: utf8
from random import randint

B64 = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-_'


def gen_id(n=8):
    l = []
    for i in range(n):
        l.append(B64[randint(0, 63)])
    return ''.join(l)
