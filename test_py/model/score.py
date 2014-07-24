#!/usr/bin/env python
# coding: utf-8

import logging

from hqby.util import HqOrm
from hqby.config import configs


class Score(HqOrm):

    _table_name = 'score'
    _rows = ['id', 'current', 'total', 'user_id', 'title', 'updated']

    _level1 = 0
    _level2 = 220
    _level3 = 920
    _level4 = 2100
    _level5 = 3760
    _level6 = 5900

    _levels = [_level1, _level2, _level3, _level4, _level5, _level6]

    _titles = {
        _level1: u'小画童',  # 0-219
        _level2: u'小画匠',  # 220-919
        _level3: u'小画师',  # 920-2099
        _level4: u'小画家',  # 2100-3759
        _level5: u'天才画家',  # 3760-5899
        _level6: u'宝贝主播',  # 5900-7819
    }

    _action_scores = configs['action_scores']  # 行为以及积分规则

    @classmethod
    def init_score(cls, user_id):
        """ 初始化积分: 未存在新建, 存在的清空
        """
        us = cls.get(user_id=user_id)
        if us:
            #logging.warning('[Score Warning]: empty exist score record-%s' % user_id)
            us.current = 0
            us.total = 0
            us.title = cls._titles[cls._level1]
            return us.save()
        return cls.new(
            current=0,
            total=0,
            user_id=user_id,
            title=cls._titles[cls._level1],
        )

    @classmethod
    def get(cls, **kwargs):
        us = super(Score, cls).get(**kwargs)
        if us:
            return us
        else:
            assert 'user_id' in kwargs
            user_id = kwargs['user_id']
            return cls.new(current=0, total=0, user_id=user_id, title=cls._titles[cls._level1],)

    @property
    def next_level(self):
        """ 下个等级所需的分数
        """
        index = self._get_level()
        if (index+1) >= len(self._levels) or self.current >= self._level6:  # 最高等级, 返回0
            return 0
        return self._levels[index+1] - self.current

    def _get_level(self, score=None):
        if score is None:
            score = self.current
        assert score >= 0
        for index, v in enumerate(self._levels):
            if score < v:
                return index - 1

    @classmethod
    def add(cls, score, user_id):
        score = int(score)
        if not score:
            return None
        su = cls.get(user_id=user_id)
        su.be_clean()
        if score > 0:  # 累计积分不减
            su.total += score
        su.current += score
        su.title = su.get_title(su.current)
        return su.save()

    def get_title(self, score=None):
        """ 获取称号: 字符串
        """
        level = self._levels[self._get_level(score)]
        return self._titles.get(level)
