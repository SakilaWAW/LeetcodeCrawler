# -*- coding:utf-8 -*-
import requests
from bs4 import BeautifulSoup
import re
import threading
import os
import time
import html_parser_utils

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
7. 在爬取html的过程中,会遇到很多转义字符,比如html转义字符,js转义字符,目前没有很好的办法,只能依次替换.
8. [Errno -3],系统dns配置问题,ubuntu16.04不能在设置里面配置,要在
/etc/network/interfaces中添加形如dns-nameservers 8.8.8.8的dns.
9. Comparison with None performed with equality operators 和None比较的话一定是is或
者is not.
10. 在获取一道题的题目地址时获取不到,这是由于业务逻辑上有问题,带()的题目化成的url名字,由于因为url中不能包含括号所以要把()去掉.

TIPS:
1. TrueOutput if Expression else falseOutput 三元表达式写法.
2. if __name__ == '__main__'的作用类似于main()函数,让文件可以单独调试,不至于被import就启动调试程序.
3. __filter()中sort的用法,棒棒哒.
4. 使用BeautifulSoup时可以适度的用lxml解析器代替html.parser,速度快而且可以用文档树的形式,很方便.使用tag.string还
可以用对应编码直接输出文本,讲html的转义字符也一并转化了.
5. 很多类似代码的文本常被存在html页面head中的meta节点里,可以直接取得.
6. python中可以使用for,break,和else的配合来表达如果在for中没有break就做一件事的逻辑,很实用.

TODO:
1. post请求405问题
2. 如何避免js中的特殊字符
3. requests.exceptions.ConnectionError: HTTPSConnectionPool如何解决
4. ssl.SSLEOFError: EOF occurred in violation of protocol (_ssl.c:645)?
"""


class Crawler:
    LOGIN_URL = 'https://leetcode.com/accounts/login/'
    SUBMISSIONS_DIR_URL = 'https://leetcode.com/submissions/'
    SUBMISSIONS_LIST_JSON_REQUEST_URL = 'https://leetcode.com/api/submissions/'
    SESSION_MANAGE_URL = 'https://leetcode.com/session/'

    TYPE_INCREAMENT = 0
    TYPE_FULL_SCALE = 1

    LOGIN_HEADER = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) '
                                  'AppleWebKit/537.36 (KHTML, like Gecko) '
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
                     'password': '******'
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
        payload = {'offset': 0, 'limit': 9999}
        submission_dir_page = self.session.get(self.SUBMISSIONS_LIST_JSON_REQUEST_URL, params=payload)
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
            print(submission.question_title, '爬取完成')
        finally:
            file.close()

    class __Submission:
        """
        这个内部类的作用是保存提交代码的格式。
        """
        LEETCODE_BASE_URL = 'https://leetcode.com'
        DISCUSS_BASE_URL = 'https://discuss.leetcode.com/'

        # 形如xxx-xxx-xxx的名字,在请求中会用到 e.g Fizz Buzz => fizz-buzz
        question_slug_name = '暂无'
        submission_code = '暂无'
        question_body = '暂无'
        question_title = '暂无'
        submission_language = '暂无'
        best_solution_url = '暂无'
        _discuss_site_url = '暂无'

        def __init__(self, session, submission_info):
            self.question_title = submission_info['title']
            self.question_slug_name = self.question_title.lower().replace(' ', '-')\
                .replace('(', '').replace(')', '')
            self.submission_language = submission_info['lang']
            self.session = session
            self.submission_url = submission_info['url']

        def __str__(self):
            return '题目:' \
                   + self.question_title + '\n' \
                   + self.question_body + '\n' \
                   + '使用语言:' + self.submission_language + '\n' \
                   + '代码:\n' \
                   + self.submission_code + '\n' \
                   + '推荐答案url: ' + self.best_solution_url

        def crawl_and_save_info(self):
            """
            通过提交代码信息爬所需信息 并保存到对象
            """
            self.__crawl_and_save_submission_code()
            self.__crawl_and_save_question_info()
            self.__crawl_and_save_best_solution_url_in_needed_language()

        def __crawl_and_save_question_info(self):
            """
            爬取题目 同时为了下面爬取最佳答案不再重复请求url 记录下最佳答案论坛的url 并保存到对象
            """
            # 通过观察得到每道题目solution的格式
            problem_page = self.session.get('https://leetcode.com/problems/' + self.question_slug_name + '/')
            soup = BeautifulSoup(problem_page.text, 'lxml')
            self.__save_question_from_problem_page(soup)
            self.__save_discuss_site_url_from_problem_page(soup)

        def __save_question_from_problem_page(self, problem_page_soup):
            raw_question_body = problem_page_soup.find(attrs={"name": "description"})['content']
            self.question_body = html_parser_utils.HtmlParserUtils().unescape_html(raw_question_body)

        def __save_discuss_site_url_from_problem_page(self, problem_page_soup):
            section_tag = problem_page_soup.find('section', class_='action col-md-12')
            self._discuss_site_url = section_tag.a['href']

        def __crawl_and_save_submission_code(self):
            """
            获取已提交的代码 并保存到对象
            """
            submission_page = self.session.get(self.LEETCODE_BASE_URL + self.submission_url)
            submission_info = re.search("submissionCode: '([\s\S]*)editCodeUrl:", submission_page.text).group(0)
            submission_info = re.sub('\',(\s)*?editCodeUrl:', '', submission_info)
            submission_info = submission_info.replace("submissionCode: '", "")
            parser = html_parser_utils.HtmlParserUtils()
            self.submission_code = parser.unescape_js(submission_info)

        def __crawl_and_save_best_solution_url_in_needed_language(self):
            """
            获取推荐答案url 并保存
            """
            discuss_page = self.session.get(self._discuss_site_url)
            soup = BeautifulSoup(discuss_page.text, 'lxml')
            # find top voted answer in submission language
            for solution_tag in soup.body.find_all('li', attrs={'component': 'category/topic'}):
                title = solution_tag.meta['content']
                if re.search(self.submission_language, title.lower()) is not None:
                    related_solution_url = solution_tag.find('div', class_='col-md-6 col-sm-9 col-xs-10 content')\
                        .find('h2', class_='title').a['href']
                    self.best_solution_url = self.DISCUSS_BASE_URL + related_solution_url
                    break
            else:
                self.best_solution_url = 'Sorry, no best solution matches yet!'


def main():
    crawler = Crawler()
    crawler.get_all_submission()


if __name__ == '__main__':
    main()
