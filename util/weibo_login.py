# -*- coding: utf-8 -*-
'''
----------------------------------------------------
author: Mike
init date: 20170210
description: 模拟登陆微博，获取登录表单
====================================================
Weibo_login模块方法说明
get_su: 模拟微博对输入用户名进行base64加密
get_sp_rsa: 模拟微博对输入的密码进行rsa2加密
get_prelogin_data: 获取prelogin响应，提取servertime等登陆用的参数
get_post_data: 合并包括加密后的用户名、密码、prelogin等需要post的data
get_response: 对微博登录模块post上述data，获取重定向url
get_session: 提取重定向url后利用session.get方法登录，获取带有cookie的session，便于之后打开网页用
====================================================
version:
v1.0(20170210): 实现功能
'''
import urllib
import requests
import json
import re
import base64
import rsa
import binascii
import ConfigParser


class Weibo_login:

    def __init__(self):
        self.prelogin_url = 'http://login.sina.com.cn/sso/prelogin.php?entry=weibo&callback=sinaSSOController.' \
                            'preloginCallBack&su=&rsakt=mod&client=ssologin.js(v1.4.18)'
        self.username = self.get_su(self.get_config('LOGIN_INFO', 'username'))
        self.password = self.get_sp_rsa(
            password=self.get_config('LOGIN_INFO', 'password'),
            pubkey=self.get_prelogin_data()['pubkey'],
            servertime=self.get_prelogin_data()['servertime'],
            nonce=self.get_prelogin_data()['nonce']
        )
        self.login_url = 'http://login.sina.com.cn/sso/login.php?client=ssologin.js(v1.4.18)'
        self.session = self.get_session()

    @classmethod
    def get_config(cls, section, key):  # 读取配置文档
        config = ConfigParser.ConfigParser()
        config.read('weibo.cfg')
        return config.get(section, key)

    def get_su(self, user_name):
        '''
        对用户名加密
        '''
        username_ = urllib.quote(user_name)  # html字符转义
        return base64.encodestring(username_)[:-1]

    def get_sp_rsa(self, password, pubkey, servertime, nonce):
        '''
        对密码加密，http://login.sina.com.cn/js/sso/ssologin.js中makeRequest的python实现
        '''
        # 公钥pubkey在prelogin得到,固定值
        key = rsa.PublicKey(int(pubkey, 16), 65537)  # 10001对应的10进制，创建公钥
        message = ('\t').join([str(servertime), str(nonce)]) + '\n' + password
        encropy_pwd = rsa.encrypt(message, key)
        return binascii.b2a_hex(encropy_pwd)  # 将加密信息转换为16进制

    def get_prelogin_data(self):
        '''
        登录前，获得之后要提交的数据
        :return:
        '''
        prelogin_url = self.prelogin_url
        post_ori_text = requests.get(prelogin_url).text
        json_data = re.search(r'\((.*?)\)', post_ori_text).group(1)
        json_data = json.loads(json_data)
        prelogin_data = dict(json_data)
        for key, value in prelogin_data.items():
            prelogin_data[key] = str(value)
        return prelogin_data

    def get_post_data(self):
        '''
        获取并返回登录所需参数
        '''
        prelogin_data = self.get_prelogin_data()
        post_data = {
            "encoding": "UTF-8",
            "entry": "weibo",
            "from": "",
            "gateway": "1",
            'nonce': prelogin_data['nonce'],
            'pagerefer': 'http://login.sina.com.cn/sso/logout.php?entry=miniblog'
                         '&r=http%3A%2F%2Fweibo.com%2Flogout.php%3Fbackurl%3D%252F',
            "prelt": "21",
            "pwencode": "rsa2",
            "returntype": "META",
            'rsakv': prelogin_data['rsakv'],
            "savestate": "7",
            'servertime': prelogin_data['servertime'],
            "service": "miniblog",
            'sp': self.password,
            "sr": "1280*800",
            'su': self.username,
            "url": "http://weibo.com/ajaxlogin.php?framelogin=1&callback=parent.sinaSSOController.feedBackUrlCallBack",
            "userticket": "1",
            "vsnf": "1"
        }
        return post_data

    def get_response(self):
        '''
        获取中转url的响应，其中包含下一步登录要用到的url
        '''
        session = requests.session()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:51.0) Gecko/20100101 Firefox/51.0',
            'Referer': 'http://weibo.com/'
        }
        resp = session.post(url=self.login_url, data=self.get_post_data(), headers=headers)
        return resp.text

    def get_session(self):
        '''
        获取新的登录地址并提交request访问, 自动写入cookie， 下次就可以直接访问其它网站了
        '''
        response_text = self.get_response()
        new_login_url = re.search(r"location.replace\(\'(.*?)\'\)", response_text).group(1)
        session = requests.session()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:51.0) Gecko/20100101 Firefox/51.0',
            'Referer': 'http://weibo.com/'
        }
        session.get(url=new_login_url, headers=headers)
        return session

if __name__ == '__main__':
    weibo = Weibo_login()
    print weibo.username
    print weibo.password
    session = weibo.session
    print session.cookies._cookies
    resp = session.get('http://weibo.com/aj/v6/mblog/info/big?ajwvr=6&id=4065617130249636&__rnd=1486804859931')
    print resp.text
