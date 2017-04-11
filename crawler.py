# -*- coding:utf-8 -*-

"""
Q & A:
1. Max retries exceeded with url-同一ip短时间内请求次数太多,服务器会拒绝请求.等一段时间即可

"""

import requests
from bs4 import BeautifulSoup
import time

LOGIN_URL = 'https://leetcode.com/accounts/login/'
SUBMISSIONS_DIR_URL = 'https://leetcode.com/submissions/'
SUBMISSIONS_LIST_JSON_REQUEST_URL = 'https://leetcode.com/api/submissions/'
SESSION_MANAGE_URL = 'https://leetcode.com/session/'
SUBMISSION_PAGE_BASE_URL = 'https://leetcode.com/submissions/detail/'

SUBMISSIONS_COUNT__REQUEST_HEADER = {
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'zh-CN,zh;q=0.8',
    'Connection': 'keep-alive',
    'Content-Length': '2',
    'Content-Type': 'application/json',
    'Host': 'leetcode.com',
    'Origin': 'https://leetcode.com',
    'Referer': 'https://leetcode.com/session/',
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36',
}


def get_submission_json():
    payload = {'offset': 0, 'limit': 100}
    submission_dir_page = session.get(SUBMISSIONS_LIST_JSON_REQUEST_URL, params=payload)
    return submission_dir_page.json()


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


def login():
    """模拟登录,结果就是session对象中存有cookie"""
    login_msg = {'csrfmiddlewaretoken': get_csrf_code_from_login_page(),
                 'login': 'SakilaWAW',
                 'password': 'Greedisgood'
                 }
    response = ''
    while response == '':
        try:
            response = session.post(LOGIN_URL,
                                    headers={'Referer': 'https://leetcode.com/accounts/login/'},
                                    data=login_msg)
        except requests.exceptions.ConnectionError:
            print('request refused by server.', 'sleep 5 seconds')
            time.sleep(5)
            continue
    print('登录返回码:', response.status_code)


'''
def get_submission_count_request_cookie():
    count_request_cookie_dict = requests.utils.dict_from_cookiejar(session.cookies)
    count_request_cookie_dict.update({'_ga': 'GA1.2.1772446811.1491917861'})
    del count_request_cookie_dict['messages']
    print(count_request_cookie_dict)
    requests.utils.cookiejar_from_dict(count_request_cookie_dict, session.cookies)
    return session.cookies
'''


def get_csrf_code_from_login_page():
    login_page = session.get(LOGIN_URL)
    soup = BeautifulSoup(login_page.text, 'html.parser')
    return soup.input['value']


'''
def get_xcsrf_token_from_cookie():
    cookie_dict = requests.utils.dict_from_cookiejar(session.cookies)
    print('cookie', cookie_dict)
    return cookie_dict['csrftoken']
'''


def get_page_by_submission_id(submission_id):
    submission_page = session.get(SUBMISSION_PAGE_BASE_URL+submission_id,
                                  headers={'Referer': 'https://leetcode.com/submissions/'}
                                  )
    soup = BeautifulSoup(submission_page.text, 'html.parser')
    print(soup.prettify())


requests.adapters.DEFAULT_RETRIES = 30
session = requests.session()
login()
print(get_page_by_submission_id('98710488'))

