import os
import re
import lxml.html
import requests
import tempfile
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from prettytable import PrettyTable


session_code = 'b96956vnm5h86v6nk5rjn5c6v0'
catalog = 'GEC'

head = {
    'User-Agent':
    'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.1'
}


class SessionTimeout(Exception):
    pass


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
        return {'ACIXSTORE': session_code, 'select': catalog, 'act': '1'}

    def query(self):
        resp = http('POST', self.query_url, data=self.payload)
        if 'session is interrupted!' in resp.text:
            raise SessionTimeout()
        return self._parse(resp.text)

    def _parse(self, content):

        def remove_en(td):
            brs = td.find_all('br')[-1:]
            [br.extract() for br in brs]
            return td.text

        soup = BeautifulSoup(content, 'html.parser')
        rows = soup.select('table')[1].find_all('tr')
        titles = task_map(remove_en, rows[0].find_all('td'))
        table = [
            {k: remove_en(v) for k, v in zip(titles, row.find_all('td'))}
            for row in rows[1:]
        ]
        return self._create_table(titles, table)

    def _create_table(self, titles, table):
        dont_show = ['目前選上人數', '目前待亂數人數']
        task_map(titles.remove, dont_show)
        x = PrettyTable(titles)
        for r in table:
            n = r['目前剩餘名額']
            if not n.isdigit() or int(n) > 0:
                x.add_row(task_map(r.get, titles))
        return x

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
        alert = re.search('alert\((.*?)\)', resp.text)
        if alert:
            print(alert.group(1))

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


def main():
    try:
        nthu_ais = NTHU_AIS()
        x = nthu_ais.query()
    except SessionTimeout:
        import secret
        nthu_ais.login_sys(secret.NTHU_AIS_ID, secret.NTHU_AIS_PWD)
        x = nthu_ais.query()
    print(x)

if __name__ == '__main__':
    main()
