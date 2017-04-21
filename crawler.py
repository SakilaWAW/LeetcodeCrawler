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
8. [Errno -3],系统dns配置问题,ubuntu16.04不能在设置里面配置,要在/etc/network/interfaces中添加形如dns-nameservers 8.8.8.8的dns.
9. Comparison with None performed with equality operators 和None比较的话一定是is或者is not.
10. 在获取一道题的题目地址时获取不到,这是由于业务逻辑上有问题,带()的题目化成的url名字,由于因为url中不能包含括号所以要把()去掉.

TIPS:
1. TrueOutput if Expression else falseOutput 三元表达式写法.
2. if __name__ == '__main__'的作用类似于main()函数,让文件可以单独调试,不至于被import就启动调试程序.
3. __filter()中sort的用法,棒棒哒.
4. 使用BeautifulSoup时可以适度的用lxml解析器代替html.parser,速度快而且可以用文档树的形式,很方便.使用tag.string还可以
用对应编码直接输出文本,讲html的转义字符也一并转化了.
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
'''
solution source code:
<div class="content" component="post/content" itemprop="text">
			<p>AKA, the general idea to find some max is to go through all cases where max value can possibly occur and keep updating the max value. The efficiency of the scan depends on the size of cases you plan to scan.<br/>
To increase efficiency, all we need to do is to find a smart way of scan to cut off the useless cases and meanwhile 100% guarantee the max value can be reached through the rest of cases.<br/></p>
<p>In this problem, the smart scan way is to set two pointers initialized at both ends of the array. Every time move the smaller value pointer to inner array. Then after the two pointers meet, all possible max cases have been scanned and the max situation is 100% reached somewhere in the scan. Following is a brief prove of this.</p>
<p>Given a1,a2,a3.....an as input array. Lets assume a10 and a20 are the max area situation. We need to prove that a10 can be reached by left pointer and during the time left pointer stays at a10, a20 can be reached by right pointer. That is to say, the core problem is to prove: when left pointer is at a10 and right pointer is at a21, the next move must be right pointer to a20.</p>
<p>Since we are always moving the pointer with the smaller value, i.e. if a10 &gt; a21, we should move pointer at a21 to a20, as we hope. Why a10 &gt;a21? Because if a21&gt;a10, then area of a10 and a20 must be less than area of a10 and a21. Because the area of a10 and a21 is at least height[a10] * (21-10) while the area of a10 and a20 is at most height[a10] * (20-10). So there is a contradiction of assumption a10 and a20 has the max area. So, a10 must be greater than a21, then next move a21 has to be move to a20. The max cases must be reached.</p>
<pre><code>public int maxArea(int[] height) &#123;
    int left = 0, right = height.length - 1;
	int maxArea = 0;

	while (left &lt; right) {
		maxArea = Math.max(maxArea, Math.min(height[left], height[right])
				* (right - left));
		if (height[left] &lt; height[right])
			left++;
		else
			right--;
	&#125;

	return maxArea;
}</code></pre>

		</div>
'''

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

def parse():
    html = '''
<div class="content" component="post/content" itemprop="text">
			<p>AKA, the general idea to find some max is to go through all cases where max value can possibly occur and keep updating the max value. The efficiency of the scan depends on the size of cases you plan to scan.<br/>
To increase efficiency, all we need to do is to find a smart way of scan to cut off the useless cases and meanwhile 100% guarantee the max value can be reached through the rest of cases.</p>
<p>In this problem, the smart scan way is to set two pointers initialized at both ends of the array. Every time move the smaller value pointer to inner array. Then after the two pointers meet, all possible max cases have been scanned and the max situation is 100% reached somewhere in the scan. Following is a brief prove of this.</p>
<p>Given a1,a2,a3.....an as input array. Lets assume a10 and a20 are the max area situation. We need to prove that a10 can be reached by left pointer and during the time left pointer stays at a10, a20 can be reached by right pointer. That is to say, the core problem is to prove: when left pointer is at a10 and right pointer is at a21, the next move must be right pointer to a20.</p>
<p>Since we are always moving the pointer with the smaller value, i.e. if a10 &gt; a21, we should move pointer at a21 to a20, as we hope. Why a10 &gt;a21? Because if a21&gt;a10, then area of a10 and a20 must be less than area of a10 and a21. Because the area of a10 and a21 is at least height[a10] * (21-10) while the area of a10 and a20 is at most height[a10] * (20-10). So there is a contradiction of assumption a10 and a20 has the max area. So, a10 must be greater than a21, then next move a21 has to be move to a20. The max cases must be reached.</p>
<pre><code>public int maxArea(int[] height) &#123;
    int left = 0, right = height.length - 1;
	int maxArea = 0;

	while (left &lt; right) {
		maxArea = Math.max(maxArea, Math.min(height[left], height[right])
				* (right - left));
		if (height[left] &lt; height[right])
			left++;
		else
			right--;
	&#125;

	return maxArea;
}</code></pre>

		</div>
		<div>test</div>
'''

    text = html.replace('<br/>', '')
    soup = BeautifulSoup(text, 'lxml')
    div_tag = soup.div
    for s in div_tag.find_all('p'):
        print("  " + s.string)
    print('-------------------------------------------------------')
    print(div_tag.pre.code.string)


def get_csrf_code_from_login_page(session):
    login_header = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
                                  'Chrome/57.0.2987.133 Safari/537.36',
                    'Referer': 'https://leetcode.com/accounts/login/'}
    login_page = session.get('https://leetcode.com/accounts/login/', headers=login_header)
    soup = BeautifulSoup(login_page.text, 'html.parser')
    return soup.input['value']


def discuss_request_test(session):
    login_msg = {'csrfmiddlewaretoken': get_csrf_code_from_login_page(session),
                 'login': 'SakilaWAW',
                 'password': 'Greedisgood'
                 }
    '''
    login_header = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
                                  'Chrome/57.0.2987.133 Safari/537.36',
                    'Referer': 'https://leetcode.com/accounts/login/'}
    response = session.post('https://leetcode.com/accounts/login/',
                            headers=login_header,
                            data=login_msg,
                            timeout=15)
    print('登录返回码:', response.status_code)'''
    all_discuss_info_api_url = 'https://discuss.leetcode.com/api/category/540'
    all_discuss_json = session.get(all_discuss_info_api_url).json()
    info_html = all_discuss_json['topics'][0]['teaser']['content']
    soup = BeautifulSoup(info_html, 'lxml')
    print(soup)


def crawl_question_test():
    question_html = requests.get('https://leetcode.com/problems/compare-version-numbers/')
    soup = BeautifulSoup(question_html.text, 'lxml')
    text = soup.find(attrs={"name": "description"})['content']
    parser = html_parser_utils.HtmlParserUtils()
    print(parser.unescape_html(text))


def crawl_and_save_submission_code_test(session):
    login_msg = {'csrfmiddlewaretoken': get_csrf_code_from_login_page(session),
                 'login': 'SakilaWAW',
                 'password': 'Greedisgood'
                 }
    login_header = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
                                  'Chrome/57.0.2987.133 Safari/537.36',
                    'Referer': 'https://leetcode.com/accounts/login/'}
    response = session.post('https://leetcode.com/accounts/login/',
                            headers=login_header,
                            data=login_msg,
                            timeout=15)
    print('登录返回码:', response.status_code)
    submission_page_code = session.get("https://www.leetcode.com/submissions/" + 'detail/99989050/').text
    code = re.search("submissionCode: '([\s\S]*)editCodeUrl:", submission_page_code)
    parser = html_parser_utils.HtmlParserUtils()
    submission_info = code.group(0)
    submission_info = re.sub('\',(\s)*?editCodeUrl:', '', submission_info)
    submission_info = submission_info.replace("submissionCode: '", "")
    print(parser.unescape_js(submission_info))


def crawl_best_solution_test():
    submission = Crawler.Submission(requests.session(), 'java')
    submission.crawl_and_save_info()


def main():
    # crawl_best_solution_test()
    # crawl_question_test()
    # session = requests.session()
    # crawl_and_save_submission_code_test(session)
    # discuss_request_test(session)
    # parse()
    crawler = Crawler()
    crawler.get_all_submission()

if __name__ == '__main__':
    main()
