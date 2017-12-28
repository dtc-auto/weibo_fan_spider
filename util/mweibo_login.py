# coding=utf-8
"""
----------------------------------------------------
author: Mike
init date: 20170211
description: 模拟登陆微博移动版，获取登录表单
====================================================
Weibo_login模块方法说明
util: post登录所需参数，返回带cookie的登录表单
====================================================
version:
v1.0(20170211): 实现功能
"""

import requests


class Mweibo_login:

    def __init__(self):
        self.session = self.login()

    def login(self):
        '''
        这里直接使用了浏览器登录获取的参数
        '''
        post_data = {
            'action': 'util',
            'callback': 'jsonpcallback1482394789502',
            'entry': 'mweibo',
            'proj': 1,
            'savestate': 1,
            'ticket': 'ST-NTg5ODUxMjMxMA%3D%3D-1482476108-tc-A885AE06F3FFD6344DB1FF90A967E3A1-1'
        }
        url = 'https://passport.weibo.com/sso/crossdomain?'
        session = requests.session()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:50.0) Gecko/20100101 Firefox/50.0'
        }
        session.get(url, data=post_data, headers=headers)
        return session

if __name__ == '__main__':
    login = Mweibo_login()
    resp = login.session.get('http://m.weibo.cn/container/getIndex?type=uid'
                      '&value=3088704885&containerid=1076033088704885')
    print resp.text




