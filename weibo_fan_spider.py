# coding=utf-8
import ConfigParser
import json
import re
import pymongo

from lxml import etree
from util.form_request import Request
from start_urls import start_urls
from datetime import datetime


class Get_fan_info:

    form_request = Request()  # 实例化发送请求，内部包含必要的代理和cookie信息

    def __init__(self):
        # 连接数据库，这部分包含两个数据库
        self.mongo_uri = self.get_config('DATA  BASE', 'mongo_uri')
        self.mongo_db = self.get_config('DATABASE', 'mongo_database')
        self.connection = pymongo.MongoClient(self.mongo_uri)
        self.db = self.connection[self.mongo_db]
        # db_userinfo保存单个账户的信息
        self.mongo_db_userinfo = self.get_config('DATABASE', 'mongo_database_userinfo')
        self.db_userinfo = self.connection[self.mongo_db_userinfo]
        self.collection_userinfo = self.db_userinfo['userinfo']
        # 域
        self.base_url = 'http://weibo.com'

    # 配置文件读取方法
    @classmethod
    def get_config(cls, section, key):
        config = ConfigParser.ConfigParser()
        config.read('util/weibo.cfg')
        return config.get(section, key)

    # 文字处理方法
    @classmethod
    def replace(cls, x):
        # 去除\r
        removeR = re.compile('\r')
        # 去除英语引号
        removeQuote = re.compile(r'"')
        # 去除连续空格
        removeSpace = re.compile('\s+')
        # 去除分隔符\u003cbr/\u003e，去除目标文本标签内容
        removeSegmentor = re.compile(r'\\u003cbr\/\\u003e')
        x = re.sub(removeSegmentor, "", x)
        x = re.sub(removeR, "", x)
        x = re.sub(removeQuote, "", x)
        x = re.sub(removeSpace, " ", x)
        return x.strip()

    @classmethod
    def str_to_list(cls, str):
        """
        输入一个包含空格的字符串，返回以空格为断点形成的列表
        :param str:
        :return:
        """
        return re.split(' ', str)

    def get_userlist(self, fans_url):
        """
        从目标微博的粉丝列表读入粉丝信息，包括user_id，粉丝页面能看到的信息等
        :param fans_url:
        :return:
        """
        # 这部分对url发送请求，对响应使用正则匹配选取网页内容，之后用json加载，
        # 取其中html的部分用etree加载，以便之后用xpath进行检索
        while True:
            resp_text_to_process = self.form_request.process_request(fans_url)
            pattern = re.compile('FM.view\((\{"ns":"pl\.content\.followTab\.index".*?\"\})')
            result = re.search(pattern, resp_text_to_process).group(1)
            js = json.loads(result)  # 将html文档转换为json格式（类似于python字典）
            html = js['html']  # 读js中html的 KEY 对应的值
            response = etree.HTML(html)  # 返回
            # 开始检索信息，user_items为所有的粉丝条目
            user_items = response.xpath('.//li[@class="follow_item S_line2"]')
            for user_item in user_items:
                personal_info = user_item.xpath('./@action-data')[0]
                # 个人属性
                user_id = re.search('uid=(.+?)&', personal_info)
                nick_name = re.search('fnick=(.+?)&', personal_info)
                gender = re.search('sex=(.*)', personal_info)
                # 个人主页
                main_page = user_item.xpath('.//div[@class="info_name W_fb W_f14"]/a/@href')[0]
                # 达人，会员，V
                daren = '1' if user_item.xpath('.//i[contains(@node-type, "daren")]') else '0'
                membership = '1' if user_item.xpath('.//em[contains(@class, "member")]') else '0'
                v_corporation = '1' if user_item.xpath('.//i[contains(@class, "approve_co")]') else '0'
                v_individual = '1' if user_item.xpath('.//i[@class="W_icon icon_approve"]') else '0'
                # 关注粉丝微博数
                numbers = user_item.xpath('.//div[@class="info_connect"]/span/em/a/text()')
                links = user_item.xpath('.//div[@class="info_connect"]/span/em/a/@href')
                follow = numbers[0] if numbers else ''
                fan = numbers[1] if numbers else ''
                weibo = numbers[2] if numbers else ''
                follow_link = links[0] if links else ''
                fan_link = links[1] if links else ''
                # 地址信息
                address = user_item.xpath('.//div[@class="info_add"]/span/text()')
                # 简介
                brief_intro = user_item.xpath('.//div[@class="info_intro"]/span/text()')
                # 来源
                source = user_item.xpath('.//div[@class="info_from"]/a/text()')
                item = dict(
                    user_id=user_id.group(1) if user_id else '',
                    nick_name=nick_name.group(1) if nick_name else '',
                    gender=gender.group(1) if gender else '',
                    main_page=self.base_url + main_page.encode('utf-8'),
                    daren=daren,
                    membership=membership,
                    v_corporation=v_corporation,
                    v_individual=v_individual,
                    follow=follow,
                    fan=fan,
                    weibo=weibo,
                    follow_link=self.base_url + follow_link,
                    fan_link=self.base_url + fan_link,
                    address=address[0] if address else '',
                    brief_intro=brief_intro[0] if brief_intro else '',
                    source=source[0] if source else '',
                    follow_list=[],
                    fan_list=[],
                    time_of_crawl=str(datetime.now())
                )
                yield item  # 循环输出，节省内存
            # 获取限制页面标签
            limited_page = response.xpath(
                '//div[@class="W_pages"]/a[@class="page next S_txt1 S_line1"]/@page-limited')
            next_page = response.xpath('//div[@class="W_pages"]/a[@class="page next S_txt1 S_line2341"]/@href')
            if limited_page or (not next_page):
                break
            else:
                fans_url = self.base_url + next_page[0]  # 获取下一页

    def get_detail_userinfo(self, main_page):
        """
        输入主页，返回详细信息，中间经过一次转发
        :param main_page: 主页
        :return:
        """
        detail_userinfo = dict(
            register_date='',
            birthday='',
            tag='',
            education='',
            corporation='',
            level='',
            experience_point='',
            point_to_upgrade='',
            sexual_orientation='',
            create_time=str(datetime.now())
        )
        # 进入个人页面，寻找“查看更多”的链接
        print '进入主页：%s' % main_page.encode('utf-8')
        resp_text_to_process = self.form_request.process_request(main_page)
        if resp_text_to_process == '302':  # 解析到别的网站
            print '页面出错'
            return None
        pattern = re.compile('FM.view\((\{.*?\"domid\":\"Pl_Core_UserInfo.*?\"\})')
        result = re.findall(pattern, resp_text_to_process)
        if not result:
            print '未找到更多内容链接'
            return None
        result = result[0]
        js = json.loads(result)
        html = js['html']
        response = etree.HTML(html)
        pedit_more = response.xpath('.//a[@class="WB_cardmore S_txt1 S_line1 clearfix"]/@href')[0]
        if not re.findall('about', pedit_more):  # 包含about代表为企业级公号，不需要添加base_url
            pedit_more_url = self.base_url + pedit_more.encode('utf-8')
        else:  # 包含about代表为企业级公号，不需要添加base_url
            pedit_more_url = pedit_more
        # 进入详细内容页面进行爬取
        print '进入详细内容页：%s' % pedit_more_url
        resp_text_detail = self.form_request.process_request(pedit_more_url)
        # 抓取等级信息
        pattern_level = re.compile('FM.view\((\{.*?\"domid\":\"Pl_Core_UserInfo.*?\"\})')
        result_level = re.findall(pattern_level, resp_text_detail)
        if not result_level:  # 有的时候没有Pl_Core_UserInfo，则搜寻Pl_Official_RightGrowNew
            pattern_level = re.compile('FM.view\((\{.*?\"domid\":\"Pl_Official_RightGrowNew.*?\"\})')
            result_level = re.findall(pattern_level, resp_text_detail)
        js_level = json.loads(result_level[0])
        html_level = js_level['html']
        response_level = etree.HTML(html_level)
        level_info_list = response_level.xpath('.//p[@class="level_info"]/span/span[@class="S_txt1"]/text()')
        if level_info_list:

            detail_userinfo['level'] = level_info_list[0]
            detail_userinfo['experience_point'] = level_info_list[1] if len(level_info_list) == 3 else ''
            detail_userinfo['point_to_upgrade'] = level_info_list[2] if len(level_info_list) == 3 else level_info_list[1]
        # 抓取个人信息
        pattern_info = re.compile('FM.view\((\{.*?\"domid\":\"Pl_Official_PersonalInfo.*?\"\})')
        result_info = re.findall(pattern_info, resp_text_detail)
        if not result_info:  # 有的时候没有Pl_Core_UserInfo，则搜寻Pl_Official_RightGrowNew
            pattern_info = re.compile('FM.view\((\{.*?\"domid\":\"Pl_Official_Header.*?\"\})')
            result_info = re.findall(pattern_info, resp_text_detail)
        js_info = json.loads(result_info[0])
        html_level = js_info['html']
        response_info = etree.HTML(html_level)
        user_info = response_info.xpath('.//li[@class="li_1 clearfix"]')
        for item in user_info:
            user_tag = item.xpath('.//span[@class="pt_title S_txt2"]/text()')
            tag_content = item.xpath('.//span[@class="pt_detail"]//text()')
            if user_tag:
                if u'注册时间' in user_tag[0]:
                    detail_userinfo['register_date'] = tag_content[0].strip().encode('utf-8')
                if u'生日' in user_tag[0]:
                    detail_userinfo['birthday'] = tag_content[0].strip().encode('utf-8')
                if u'标签' in user_tag[0]:
                    tag = ' '.join(tag_content).strip().encode('utf-8')
                    tag = self.replace(tag)
                    detail_userinfo['tag'] = self.str_to_list(tag)
                if u'大学' in user_tag[0]:
                    education = ' '.join(tag_content)
                    detail_userinfo['education'] = self.replace(education)
                if u'公司' in user_tag[0]:
                    corporation = ' '.join(tag_content)
                    detail_userinfo['corporation'] = self.replace(corporation)
                if u'性取向' in user_tag[0]:
                    detail_userinfo['sexual_orientation'] = tag_content[0].strip().encode('utf-8')
        return detail_userinfo

    def process_fan_list(self):
        for name, fans_url in start_urls.iteritems():
            collection = self.db[name]
            print '============================================='
            print '当前处理：', name
            for item in self.get_userlist(fans_url):
                # 判断当前用户为新增粉丝
                # 判断加入关系数据库
                if not self._is_duplicate(self.mongo_db, name, 'user_id', item['user_id']):
                    print '写入%s 信息至 %s' % (item['nick_name'].encode('utf-8'), name)
                    collection.insert(item)
                else:
                    print '%s 中已存在用户 %s' % (name, item['nick_name'].encode('utf-8'))
                # 判断加入结点数据库
                if not self._is_duplicate(self.mongo_db_userinfo, 'userinfo', 'user_id', item['user_id']):
                    print '%s 为新用户，加入本地用户信息数据库' % item['nick_name'].encode('utf-8')
                    self.collection_userinfo.insert(item)
                else:
                    print '%s 中已存在用户 %s' % (self.mongo_db_userinfo, item['nick_name'].encode('utf-8'))
                print '-------------------------------------------------------------------'

    def process_fan_fansandfollows(self):
        """
        输入粉丝或关注者列表的首页url，返回单条信息的生成器
        :return:
        """
        # 遍历所有粉丝
        for collection_name in self.db.collection_names():
            collection = self.db[collection_name]
            for document in collection.find():
                user_id = document['user_id']
                # 读取粉丝和关注页面第一页的url
                follow_link = document['follow_link']
                fan_link = document['fan_link']
                counter = 0
                follow_list = []
                fan_list = []
                # 处理关注者
                print '============================================='
                print '当前处理：%s 的关注者列表' % document['nick_name'].encode('utf-8')
                for item in self.get_userlist(follow_link):
                    # 判断是否已经获取过该用户信息
                    if item['user_id'] in set(document['follow_list']):
                        print '%s 中已存在用户 %s' % (document['nick_name'].encode('utf-8'),
                                                item['nick_name'].encode('utf-8'))
                        counter += 1
                        continue
                    else:
                        counter = 0
                        print '加入%s 信息至 %s' % (item['nick_name'].encode('utf-8'), collection_name.encode('utf-8'))
                        follow_list.append(str(item['user_id']))
                    # 放入用户信息数据库库
                    if not self._is_duplicate(self.mongo_db_userinfo, 'userinfo', 'user_id', item['user_id']):
                        print '%s 为新用户，加入本地用户信息数据库' % item['nick_name'].encode('utf-8')
                        print '-------------------------------------------------------------------'
                        self.collection_userinfo.insert(item)
                    else:
                        print '%s 中已存在用户 %s' % (self.mongo_db_userinfo, item['nick_name'].encode('utf-8'))
                    if counter >= 5:
                        counter = 0
                        print '判断后续内容已经全部抓取，进入下一环节'
                        break
                print '============================================='
                print '当前处理：%s 的粉丝列表' % document['nick_name'].encode('utf-8')
                for item in self.get_userlist(fan_link):
                    # 判断是否已经获取过该用户信息
                    if item['user_id'] in set(document['fan_list']):
                        print '%s 中已存在用户 %s' % (document['nick_name'].encode('utf-8'), item['nick_name'].encode('utf-8'))
                        counter += 1
                        continue
                    else:
                        counter = 0
                        print '加入%s 信息至 %s' % (item['nick_name'].encode('utf-8'), collection_name.encode('utf-8'))
                        fan_list.append(str(item['user_id']))
                    # 放入用户信息数据库库
                    if not self._is_duplicate(self.mongo_db_userinfo, 'userinfo', 'user_id', item['user_id']):
                        print '%s 为新用户，加入本地用户信息数据库' % item['nick_name'].encode('utf-8')
                        print '-------------------------------------------------------------------'
                        self.collection_userinfo.insert(item)
                    else:
                        print '%s 中已存在用户 %s' % (self.mongo_db_userinfo, item['nick_name'].encode('utf-8'))
                    # 判断是否连续出现已存在用户
                    if counter >= 5:
                        print '判断后续内容已经全部抓取，进入下一环节'
                        break

                # 将粉丝的粉丝和关注user_id写入文档
                print '将粉丝的粉丝和关注写入文档 %s' % collection_name.encode('utf-8')
                collection.update({'user_id': user_id}, {'$set': {'follow_list': follow_list, 'fan_list': fan_list}})

    def process_fan_detailinfo(self):
        collection = self.db_userinfo['userinfo']
        pattern = re.compile('[^\d]')
        for document in collection.find():
            if 'detail_userinfo' in document:
                print '已处理 %s 的信息' % document['nick_name'].encode('utf-8')
                continue
            if not re.match(pattern, document['user_id']):
                try:
                    print '-------------------------------------------------------------------'
                    print '当前处理 %s 的详细信息' % document['nick_name'].encode('utf-8')
                    detail_userinfo = self.get_detail_userinfo(document['main_page'])
                    if detail_userinfo is not None:
                        collection.update({'user_id': document['user_id']}, {'$set': {'detail_userinfo': detail_userinfo}})
                        print '插入 %s 的详细信息成功' % document['nick_name'].encode('utf-8')
                        for key, value in detail_userinfo.iteritems():
                            print key, ':', value
                    else:
                        collection.update({'user_id': document['user_id']}, {'$set': {'detail_userinfo': detail_userinfo}})
                        print '当前用户 %s 的详细信息获取失败' % document['nick_name'].encode('utf-8')
                except Exception:
                    self.process_fan_detailinfo()

    def _is_duplicate(self, database, collection_name, key, value):
        """
        判断数据是否在特定聚集中存在
        :param database:
        :param collection_name:
        :param key:
        :param value:
        :return: boolean
        """
        db = self.connection[database]
        collection = db[collection_name]
        if any(collection.find({key: value})):
            return True
        else:
            return False

    def clear_key(self, field):
        """
        清除userinfo数据库内的某一个field
        :param field:
        :return:
        """
        collection = self.db_userinfo['userinfo']
        for document in collection.find(projection={field: False}):
            collection.save(document)
            print document

if __name__ == "__main__":
    getfan = Get_fan_info()
    # getfan.process_fan_list()
    # getfan.process_fan_fansandfollows()
    getfan.process_fan_detailinfo()
    # getfan.clear_key('detail_userinfo')
