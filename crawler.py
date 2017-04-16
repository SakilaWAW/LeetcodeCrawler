# -*- coding:utf-8 -*-
import requests
from bs4 import BeautifulSoup
import re
import threading
import os
import time

"""
Q & A:
1. Max retries exceeded with url-同一ip短时间内请求次数太多,服务器会拒绝请求.等一段时间即可.
2. 正则表达式出现换行符无法匹配的问题,用.在默认情况下是不匹配换行的,要用[\s\S]*的形式才可以.使用
的时候分清r''是指python字符串的raw,和正则表达式无关!
3. 出现遍历时候删除列表项不正确的情况,因为删除元素会造成长度改变,会出问题.筛选条件简单的时候尽量用
filter(lambda表达式)或者列表推导式来写会比较好.筛选条件复杂的时候可以考虑用列表将要删元素存起来,
最后一起删除.
4. 使用多线程的时候出现只能启动单子线程的情况,注意区分threading.join()和setDaemon()的用法!
t1.join()<==>wait_until_finish(t1),会阻断当前程序,t1.setDaemon(True)意味着当前线程完成后,
t1将被强制终止.
5. 在使用多线程做requests请求的时候,请求速度太快可能会被网站认为是非法访问,用在线程开启后time.sleep()
可以避免这个问题.??可能??
6. object is not subscriptable通常是运行时的操作与对象类型不符

TIPS:
1. TrueOutput if Expression else falseOutput 三元表达式写法.
2. if __name__ == '__main__'的作用类似于main()函数,让文件可以单独调试,不至于被import就启动调试程序.
3. __filter()中sort的用法,棒棒哒.

TODO:
1. post请求405问题
2. 如何避免js中的特殊字符
3. requests.exceptions.ConnectionError: HTTPSConnectionPool如何解决
"""


class Crawler:
    LOGIN_URL = 'https://leetcode.com/accounts/login/'
    SUBMISSIONS_DIR_URL = 'https://leetcode.com/submissions/'
    SUBMISSIONS_LIST_JSON_REQUEST_URL = 'https://leetcode.com/api/submissions/'
    SESSION_MANAGE_URL = 'https://leetcode.com/session/'

    TYPE_INCREAMENT = 0
    TYPE_FULL_SCALE = 1

    LOGIN_HEADER = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
                                  'Chrome/57.0.2987.133 Safari/537.36',
                    'Referer': 'https://leetcode.com/accounts/login/'}

    ROOT_PATH = os.getcwd()

    def __init__(self, crawl_type=TYPE_INCREAMENT):
        self.session = requests.session()

    def get_all_submission(self):
        """
        对外接口1:获得所有submission
        登录->得到提交目录->筛选目录->通过目录存代码到文件
        :return 返回内容待定
        """
        self.__check_status_and_login()
        submissions_catalog = self.__get_submission_catalog()
        self.__filter(submissions_catalog)
        self.__crawl_and_save_submission_info_as_file_by_list(submissions_catalog)

    def __check_status_and_login(self):
        if requests.utils.dict_from_cookiejar(self.session.cookies) == {}:
            self.__login()

    def __login(self):
        """模拟登录,结果就是session对象中存有cookie"""
        login_msg = {'csrfmiddlewaretoken': self.__get_csrf_code_from_login_page(),
                     'login': 'SakilaWAW',
                     'password': 'Greedisgood'
                     }
        response = self.session.post(self.LOGIN_URL,
                                     headers=self.LOGIN_HEADER,
                                     data=login_msg,
                                     timeout=15)
        print('登录返回码:', response.status_code)

    def __get_csrf_code_from_login_page(self):
        login_page = self.session.get(self.LOGIN_URL)
        soup = BeautifulSoup(login_page.text, 'html.parser')
        return soup.input['value']

    def __get_submission_catalog(self):
        payload = {'offset': 0, 'limit': 100}
        submission_dir_page = self.session.get(self.SUBMISSIONS_LIST_JSON_REQUEST_URL, params=payload)
        print(submission_dir_page.text)
        return eval(submission_dir_page.text.replace('true', 'True').replace('false', 'False'))['submissions_dump']

    def __filter(self, submission_list):
        """
        去掉提交代码列表中的重复部分和失败代码部分并且进行排序
        submission_list会直接被更改
        """
        submission_list.sort(key=lambda submission_info: self.__format_runtime(submission_info['runtime']))
        temp_title_list = []
        temp_del_list = []
        for submission in submission_list[:]:
            title = submission['title']
            runtime = submission['runtime']
            if runtime == 'N/A':
                del submission_list[submission_list.index(submission):]
                break
            elif title in temp_title_list:
                temp_del_list.append(submission)
            else:
                temp_title_list.append(title)
        for del_submission in temp_del_list[:]:
            del submission_list[submission_list.index(del_submission)]

    @staticmethod
    def __format_runtime(runtime):
        return int(runtime.replace('ms', '')) if runtime != 'N/A' else 10000

    def __crawl_and_save_submission_info_as_file_by_list(self, submission_catalog):
        """
        开启多线程通过提交概览表将提交代码下载下来并存到文件
        :param submission_catalog: 所有提交答案的概览 
        """
        threads = []
        for submission_info in submission_catalog[:]:
            submission_thread = threading.Thread(target=self.__crawl_and_save_submission_as_file,
                                                 args=(submission_info,)
                                                 )
            threads.append(submission_thread)
        for thread in threads:
            thread.start()
            time.sleep(0.2)

    def __crawl_and_save_submission_as_file(self, submission_info):
        """
        根据url获得代码并保存到文件
        :param submission_info: 提交代码信息
        """
        print(threading.current_thread(), "开始进程")
        self.__check_status_and_login()
        submission = self.__Submission(self.session, submission_info)
        submission.crawl_and_save_info()
        self.__save_to_file(submission, threading.current_thread().name)

    def __save_to_file(self, submission, file_name):
        submission_file_dir = self.ROOT_PATH + '/.submission_files/'
        if not os.path.exists(submission_file_dir):
            os.mkdir(submission_file_dir)
        file_name = submission_file_dir + file_name
        file = open(file_name, 'w')
        try:
            file.write(submission.__str__())
            print(threading.current_thread(), '写入完成')
        finally:
            file.close()

    class __Submission:
        """
        这个内部类的作用是保存提交代码的格式。
        """
        SUBMISSION_PAGE_BASE_URL = 'https://leetcode.com'

        code = '暂无'
        question = '暂无'
        recommend_solution = '暂无'
        title = '暂无'
        language = '暂无'

        def __init__(self, session, submission_info):
            self.title = submission_info['title']
            self.language = submission_info['lang']
            self.session = session
            self.submission_url = submission_info['url']

        def __str__(self):
            return '题目:\n' \
                   + self.title + '\n' \
                   + self.question + '\n' \
                   + '使用语言:' + self.language + '\n' \
                   + '代码:\n' \
                   + self.code + '\n' \
                   + '推荐答案:\n' \
                   + self.recommend_solution

        def crawl_and_save_info(self):
            """
            通过提交代码信息爬所需信息并保存到对象
            :param submission_info: 提交代码信息
            :param session: 提交http请求的session
            """
            self.__save_submission_code()
            self.__save_recommend_solution()

        def __save_submission_code_from_url(self):
            """
             根据url获得已提交的代码 并保存
             """
            submission_page_code = self.session.get(self.SUBMISSION_PAGE_BASE_URL + self.submission_url).text
            code = re.search("submissionCode: '([\s\S]*)editCodeUrl:", submission_page_code)
            replace_dic = {"submissionCode: '": "",
                           r"\u000A": "\n", r"\u000D": "\r", r"\u0009": "\t", r"\u003D": "=",
                           r"\u003B": ";", r"\u003C": "<", r"\u0026": "&", r"\u0027": "'",
                           r"\u002D": "-", r"\u003E": ">", r"\u0022": "\"", r"\u005C": "\\"}
            submission_info = code.group(0)
            for key in replace_dic:
                submission_info = submission_info.replace(key, replace_dic[key])
            submission_info = re.sub('}\',(\s)*?editCodeUrl:', '', submission_info)
            self.code = submission_info

        

'''
def get_submission_count_request_cookie():
    count_request_cookie_dict = requests.utils.dict_from_cookiejar(session.cookies)
    count_request_cookie_dict.update({'_ga': 'GA1.2.1772446811.1491917861'})
    del count_request_cookie_dict['messages']
    print(count_request_cookie_dict)
    requests.utils.cookiejar_from_dict(count_request_cookie_dict, session.cookies)
    return session.cookies
'''
'''
def get_xcsrf_token_from_cookie():
    cookie_dict = requests.utils.dict_from_cookiejar(session.cookies)
    print('cookie', cookie_dict)
    return cookie_dict['csrftoken']
'''

'''
def get_submission_count():
    SUBMISSIONS_COUNT__REQUEST_HEADER['X-CSRFToken'] = get_xcsrf_token_from_cookie()
    SUBMISSIONS_COUNT__REQUEST_HEADER['X-Requested-With'] = 'XMLHttpRequest'
    submission_count_page = session.post(SESSION_MANAGE_URL,
                                         headers=SUBMISSIONS_COUNT__REQUEST_HEADER,
                                         cookies=get_submission_count_request_cookie()
                                         )
    print(submission_count_page.text)
    print('count请求返回码:', submission_count_page.status_code)
'''


def main():
    crawler = Crawler()
    crawler.get_all_submission()

if __name__ == '__main__':
    main()
