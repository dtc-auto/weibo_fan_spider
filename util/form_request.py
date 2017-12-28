# coding=utf-8
'''
----------------------------------------------------
author: Mike
init date: 20170222
description: 利用模拟登陆微博获得的cookie以及代理生成request，获取页面响应内容
====================================================
Request模块方法说明
process_request: 加载代理服务器设置
====================================================
version:
v1.0(20170222): 实现功能
'''
import pickle
import random
import requests


from util.weibo_login import Weibo_login
from util.mweibo_login import Mweibo_login
from cookies import cookie_list


class Request:  # 利用weibo_login获取的session获取响应，附加代理服务器设置
    pkl_file = open('proxy.pkl', 'rb')
    proxy_list = pickle.load(pkl_file)

    def __init__(self):
        self.session = requests.session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:53.0) Gecko/20100101 Firefox/53.0',
            # 'Referer': 'http://weibo.com/',
            'Accept-Encoding': 'gzip'
        }

    def process_request(self, url):  # 附加代理并对响应结果进行判断
        random_proxy = random.choice(self.proxy_list)
        random_cookie = requests.utils.cookiejar_from_dict(cookie_dict=random.choice(cookie_list))
        try:
            resp = self.session.get(url, timeout=10, proxies={'http': random_proxy}, headers=self.headers, cookies=random_cookie, allow_redirects=False)
            if resp.status_code == 200:
                print '当前使用代理%s获取响应' % str(random_proxy)
                return resp.text
            elif resp.status_code == 302:
                print '出现跳转页面'
                return '302'
            else:
                print '代理%s页面连接错误，更换代理重试' % str(random_proxy)
                return self.process_request(url)
        except (Exception, requests.HTTPError), e:
            print '代理%s连接错误，更换代理重试' % str(random_proxy), e
            # time.sleep(10)
            return self.process_request(url)

class Request_m:  # 利用mweibo_login获取的session获取响应，附加代理服务器设置
    pkl_file = open('proxy.pkl', 'rb')
    proxy_list = pickle.load(pkl_file)

    def __init__(self):
        self.session = Mweibo_login().session
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:51.0) Gecko/20100101 Firefox/51.0',
            'Referer': 'http://weibo.com/'
        }

    def process_request(self, url):  # 附加代理并对响应结果进行判断
        random_proxy = random.choice(self.proxy_list)
        try:
            resp = self.session.get(url, timeout=10, proxies={'http': random_proxy}, headers=self.headers)
            if resp.status_code == 200:
                print '当前使用代理%s获取响应' % str(random_proxy)
                return resp.text
            else:
                print '代理%s页面连接错误，更换代理重试' % str(random_proxy)
                return self.process_request(url)
        except (Exception, requests.HTTPError), e:
            print '代理%s连接错误，更换代理重试' % str(random_proxy), e
            # time.sleep(10)
            return self.process_request(url)


if __name__ == '__main__':
    url = 'http://weibo.com/2125975485/fans?refer_flag=1001030201_'
    request = Request()
    print request.process_request(url)
