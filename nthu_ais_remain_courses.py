import os
import re
import lxml.html
import requests
import tempfile
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from prettytable import PrettyTable


session_code = 'mf8qg139sb6he4b1mvf99puqa7'
catalog = 'GEC'

head = {
    'User-Agent':
    'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.1'
}


class SessionTimeout(Exception):
    pass


def http(method, url, **kwargs):
    return requests.request(method, url, headers=head, **kwargs)


def magic_self_edit_session(code):
    with open(__file__, 'r+', encoding='utf8') as f:
        s = f.read()
        r = re.sub("(session_code = )'(.*?)'", r"\1'%s'" % code, s)
        not f.seek(0) and not f.write(r) and not f.truncate()


class NTHU_AIS():

    index = 'https://www.ccxp.nthu.edu.tw/ccxp/INQUIRE/'
    query_url = urljoin(index, '/ccxp/COURSE/JH/7/7.2/7.2.7/JH727002.php')
    login_url = urljoin(index, 'pre_select_entry.php')
    auth_img_url = urljoin(index, 'auth_img.php')

    def __init__(self, account=None, password=None):
        self.account = account
        self.password = password
        self.payload = self._get_query_payload()

    def _get_query_payload(self):
        return {
            'ACIXSTORE': session_code,
            'select': catalog,
            'act': '1'
        }

    def query(self):
        resp = http('POST', self.query_url, data=self.payload)
        resp.encoding = 'big5'
        if 'session is interrupted!' in resp.text:
            raise SessionTimeout()
        soup = BeautifulSoup(resp.text, 'html.parser')
        return soup.select('table')[1].find_all('tr')

    def man_captcha(self, param):
        content = http('GET', self.auth_img_url, params=param).content
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            not tmp.write(content) and not tmp.flush()
            os.startfile(tmp.name)
        return input('驗證碼> ')

    def _get_fnstr(self):
        doc = lxml.html.fromstring(http('GET', self.index).text)
        return doc.xpath('//input[@name="fnstr"]')[0].value

    def _get_login_payload(self):
        fnstr = self._get_fnstr()
        captcha = self.man_captcha({'pwdstr': fnstr})
        return {
            'account': self.account,
            'passwd': self.password,
            'fnstr': fnstr,
            'passwd2': captcha
        }

    def _set_user(self, account, password):
        self.account = account
        self.password = password

    def _invoke_session(self, invoke_url):
        resp = http('GET', urljoin(self.index, invoke_url))
        print(re.search('alert\((.*?)\)', resp.text).group(1))

    def login_sys(self, account, password):
        self._set_user(account, password)
        resp = http('POST', self.login_url, data=self._get_login_payload())
        match = re.search('url=(.*?\?ACIXSTORE=(.*?)&hint=\d*)', resp.text)
        if match:
            self._invoke_session(match.group(1))
            self.update_session_code(match.group(2))

    def update_session_code(self, acixstore):
        print('new session code:', acixstore)
        self.payload.update({'ACIXSTORE': acixstore})
        magic_self_edit_session(acixstore)

    def print_table(self, titles, results):
        N = ['目前選上人數', '目前待亂數人數']
        T = [t for t in titles if t not in N]
        x = PrettyTable(T)
        for r in results:
            n = r['目前剩餘名額']
            if not n.isdigit() or int(n) > 0:
                x.add_row([r[k] for k in T])
        print(x)


def main():
    try:
        nthu_ais = NTHU_AIS()
        rows = nthu_ais.query()
    except SessionTimeout:
        import secret
        nthu_ais.login_sys(secret.NTHU_AIS_ID, secret.NTHU_AIS_PWD)
        rows = nthu_ais.query()

    def remove_en(td):
        if td.find('br'):
            td.find_all('br')[-1].extract()
        return td.text

    titles = [remove_en(td) for td in rows[0].find_all('td')]
    results = [
        {key: remove_en(td)
         for key, td in zip(titles, tr.find_all('td'))}
        for tr in rows[1:]
    ]
    nthu_ais.print_table(titles, results)


if __name__ == '__main__':
    # main()
    nthu_ais = NTHU_AIS()
    nthu_ais.login_sys('10255102', '22')
    nthu_ais.login_sys('10255102', '22')
