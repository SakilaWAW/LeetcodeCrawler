# -*- coding:utf-8 -*-
import requests
from bs4 import BeautifulSoup
import time
import re
import threading

"""
Q & A:
1. Max retries exceeded with url-同一ip短时间内请求次数太多,服务器会拒绝请求.等一段时间即可.
2. 正则表达式出现换行符无法匹配的问题,用.在默认情况下是不匹配换行的,要用[\s\S]*的形式才可以,使用
的时候记得不要用raw字符串!
3. 出现遍历时候删除列表项不正确的情况,因为删除元素会造成长度改变,会出问题.筛选条件简单的时候尽量用
filter(lambda表达式)或者列表推导式来写会比较好.筛选条件复杂的时候可以考虑用列表将要删元素存起来,
最后一起删除.
4. 使用多线程的时候出现只能启动单子线程的情况,注意区分threading.join()和setDaemon()的用法!
t1.join()<==>wait_until_finish(t1),会阻断当前程序,t1.setDaemon(True)意味着当前线程完成后,
t1将被强制终止.

TIPS:
1. TrueOutput if Expression else falseOutput 三元表达式写法.
2. if __name__ == '__main__'的作用类似于main()函数,让文件可以单独调试,不至于被import就启动调试程序.
3. __filter()中sort的用法,棒棒哒.

TODO:
1. post请求405问题
"""


class Crawler:
    LOGIN_URL = 'https://leetcode.com/accounts/login/'
    SUBMISSIONS_DIR_URL = 'https://leetcode.com/submissions/'
    SUBMISSIONS_LIST_JSON_REQUEST_URL = 'https://leetcode.com/api/submissions/'
    SESSION_MANAGE_URL = 'https://leetcode.com/session/'
    SUBMISSION_PAGE_BASE_URL = 'https://leetcode.com'

    def __init__(self):
        self.session = requests.session()

    def get_all_submission(self):
        """
        对外接口1:获得所有submission
        :return 返回内容待定
        """
        self.__check_status_and_login()
        submissions_catalog = self.__get_submission_catalog_dict()['submissions_dump']
        self.__filter(submissions_catalog)
        self.__get_submission_code_as_file(submissions_catalog)

    def __get_submission_code_as_file(self, submission_catalog):
        """
        :param submission_catalog: 提交答案概览 
        """
        threads = []
        for submission in submission_catalog[:]:
            submission_thread = threading.Thread(target=self.__get_page_by_submission_url,
                                                 args=(submission['url'],))
            threads.append(submission_thread)
        for t in threads:
            t.start()

    def __get_submission_catalog_dict(self):
        payload = {'offset': 0, 'limit': 100}
        submission_dir_page = self.session.get(self.SUBMISSIONS_LIST_JSON_REQUEST_URL, params=payload)
        return eval(submission_dir_page.text.replace('true', 'True').replace('false', 'False'))

    def __filter(self, submission_list):
        """
        去掉提交代码列表中的重复部分
        submission_list会直接被更改
        """
        submission_list.sort(key=lambda submission_info: self.__turn_runtime(submission_info['runtime']))
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
    def __turn_runtime(runtime):
        return int(runtime.replace('ms', '')) if runtime != 'N/A' else 10000

    def __get_page_by_submission_url(self, submission_url):
        print("开始获得", submission_url, "的提交代码")
        self.__check_status_and_login()
        submission_page = self.session.get(self.SUBMISSION_PAGE_BASE_URL+submission_url,
                                           headers={'Referer': 'https://leetcode.com/submissions/'}
                                           )
        print("当前线程:", threading.current_thread().name)
        self.__get_code_from_page_source_code(submission_page.
                                              text.encode(submission_page.encoding).decode('utf-8'))
        print("当前所有线程:", threading.enumerate())

    def __check_status_and_login(self):
        if requests.utils.dict_from_cookiejar(self.session.cookies) == {}:
            self.__login()

    def __login(self):
        """模拟登录,结果就是session对象中存有cookie"""
        login_msg = {'csrfmiddlewaretoken': self.__get_csrf_code_from_login_page(),
                     'login': 'SakilaWAW',
                     'password': 'Greedisgood'
                     }
        response = ''
        while response == '':
            try:
                response = self.session.post(self.LOGIN_URL,
                                             headers={'Referer': 'https://leetcode.com/accounts/login/'},
                                             data=login_msg)
            except requests.exceptions.ConnectionError:
                print('request refused by server.', 'sleep 5 seconds')
                time.sleep(5)
                continue
        print('登录返回码:', response.status_code)

    def __get_csrf_code_from_login_page(self):
        login_page = self.session.get(self.LOGIN_URL)
        soup = BeautifulSoup(login_page.text, 'html.parser')
        return soup.input['value']

    @staticmethod
    def __get_code_from_page_source_code(page_source_code):
        """
        TODO
        从网页源码中获得已提交的代码
        """
        code = re.search("submissionData:([\s\S]*)nonSufficientMsg:", page_source_code)
        dict_str = code.group(0).replace('nonSufficientMsg:', '}')
        dict_str = dict_str.replace('submissionData: ', '{submissionData: ')
        return dict_str

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



