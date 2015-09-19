import os
import re
import requests
import tempfile
import lxml.html
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from prettytable import PrettyTable

''' ------------------------ You can edit these lines --------------------- '''

session_code = 'a76o51tg4gdjp07n4avkqhj8s4'
catalog = 'GEC'

head = {
    'User-Agent':
    'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.1'
}

''' ----------------------------------------------------------------------- '''


def http(method, url, **kwargs):
    resp = requests.request(method, url, headers=head, **kwargs)
    resp.encoding = 'big5'
    return resp


def task_map(*args):
    return list(map(*args))


def magic_self_edit_session(code):
    with open(__file__, 'r+', encoding='utf8') as f:
        s = f.read()
        r = re.sub("(session_code = )'(.*?)'", r"\1'%s'" % code, s)
        not f.seek(0) and not f.write(r)


class SessionTimeout(Exception):
    pass


class NTHU_AIS():

    index = 'https://www.ccxp.nthu.edu.tw/ccxp/INQUIRE/'
    query_url = urljoin(index, '/ccxp/COURSE/JH/7/7.2/7.2.7/JH727002.php')
    login_url = urljoin(index, 'pre_select_entry.php')
    auth_img_url = urljoin(index, 'auth_img.php')

    def __init__(self, catalog, session_code):
        self.account = None
        self.catalog = catalog
        self.session = session_code

    def query(self):
        resp = http('POST', self.query_url, data=self.get_payload('query'))
        if 'session is interrupted!' in resp.text:
            raise SessionTimeout()
        return self._parse(resp.text)

    def _parse(self, content):

        def remove_en(td):
            brs = td.find_all('br')[-1:]
            [br.extract() for br in brs]
            return td.text

        soup = BeautifulSoup(content, 'html.parser')
        table = [
            [remove_en(e) for e in row.find_all('td')]
            for row in soup.select('table')[1].find_all('tr')
        ]
        return self._create_table(titles=table[0], content=table[1:])

    def _create_table(self, titles, content):

        def make_titles(data):
            focus = data.index('目前剩餘名額')
            dont_show = ['目前選上人數', '目前待亂數人數']
            show_cols = [i for i, _ in enumerate(data) if _ not in dont_show]
            task_map(titles.remove, dont_show)
            return focus, show_cols

        def gen_row(row):
            n = row[focus]
            if not n.isdigit() or int(n) > 0:
                return [row[i] for i in show_cols]

        def add_row(row):
            e = gen_row(row)
            x.add_row(e) if e else None

        focus, show_cols = make_titles(titles)
        x = PrettyTable(titles)
        task_map(add_row, content)
        return x

    def login_sys(self, account, password):
        self.account = {'account': account, 'passwd': password}
        resp = http('POST', self.login_url, data=self.get_payload('login'))
        match = re.search('url=(.*?\?ACIXSTORE=(.*?)&hint=\d*)', resp.text)
        if not match:
            return ('登入失敗')
        self._invoke_session(match.group(1))
        self._update_session_code(match.group(2))

    def man_captcha(self, param):
        content = http('GET', self.auth_img_url, params=param).content
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            not tmp.write(content) and not tmp.flush()
            os.startfile(tmp.name)
        return input('驗證碼> ')

    def get_payload(self, action):
        return {
            'login': self._get_login_payload,
            'query': self._get_query_payload,
        }[action]()

    def _get_query_payload(self):
        return {'ACIXSTORE': self.session, 'select': self.catalog, 'act': '1'}

    def _get_login_payload(self):

        def get_fnstr():
            doc = lxml.html.fromstring(http('GET', self.index).text)
            return doc.xpath('//input[@name="fnstr"]')[0].value

        fnstr = get_fnstr()
        captcha = self.man_captcha({'pwdstr': fnstr})
        payload = {'fnstr': fnstr, 'passwd2': captcha}
        payload.update(self.account)
        return payload

    def _invoke_session(self, invoke_url):
        resp = http('GET', urljoin(self.index, invoke_url))
        alert = re.search('alert\((.*?)\)', resp.text)
        if alert:
            print(alert.group(1))

    def _update_session_code(self, acixstore):
        print('new session code:', acixstore)
        self.session = acixstore
        magic_self_edit_session(acixstore)


def main():
    try:
        nthu_ais = NTHU_AIS(catalog, session_code)
        x = nthu_ais.query()
    except SessionTimeout:
        try:
            import secret
            account = secret.NTHU_AIS_ID
            password = secret.NTHU_AIS_PWD
        except ImportError:
            import getpass
            account = input('帳號: ')
            password = getpass.getpass('密碼: ')
        state = nthu_ais.login_sys(account, password)
        x = state or nthu_ais.query()
    finally:
        print(x)

if __name__ == '__main__':
    main()
