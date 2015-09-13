import os
import re
import requests
import tempfile
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from prettytable import PrettyTable


session_code = '382f3uss4jkp043t6jlt8mr1u7'
catalog = 'GEC'

head, payload = {
    'User-Agent':
    'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.1'
}, {
    'ACIXSTORE': session_code,
    'select': catalog,
    'act': '1'
}


class SessionTimeout(Exception):
    pass


def http(method, url, **kwargs):
    return requests.request(method, url, headers=head, **kwargs)


def magic_self_edit_session(code):
    with open(__file__, 'r+', encoding='utf8') as f:
        s = f.read()
        r = re.sub("(session_code = )'(.*?)'", r"\1'%s'" % code, s)
        f.seek(0)
        f.write(r)
        f.truncate()


def update_session_code(resp):
    session_code = re.search('ACIXSTORE=([^&]*)', resp.text).group(1)
    payload.update({'ACIXSTORE': session_code})
    magic_self_edit_session(session_code)
    print('new session code:', session_code)


def print_table(titles, results):
    N = ['目前選上人數', '目前待亂數人數']
    T = [t for t in titles if t not in N]
    x = PrettyTable(T)
    for r in results:
        n = r['目前剩餘名額']
        if (n.isdigit() and int(n) > 0) or not n.isdigit():
            x.add_row([r[k] for k in T])
    print(x)


class NTHU_AIS():

    home = 'https://www.ccxp.nthu.edu.tw/ccxp/INQUIRE/'
    query_url = urljoin(home, '/ccxp/COURSE/JH/7/7.2/7.2.7/JH727002.php')
    login_url = urljoin(home, 'pre_select_entry.php')

    def query(self):
        resp = http('POST', self.query_url, data=payload)
        resp.encoding = 'big5'
        if 'session is interrupted!' in resp.text:
            raise SessionTimeout()
        soup = BeautifulSoup(resp.text, 'html.parser')
        return soup.select('table')[1].find_all('tr')

    def man_auth_code(self, img_url):
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            tmp.write(http('GET', img_url).content)
            tmp.flush()
            os.startfile(tmp.name)
        return input('驗證碼> ')

    def login_sys(self, uid, pwd):
        resp = http('GET', self.home)
        r = re.search('auth_img.php\?pwdstr=([\d-]*)', resp.text)
        auth_img = urljoin(self.home, r.group(0))
        resp = http('POST', self.login_url, data={
            'account': uid, 'passwd': pwd,
            'fnstr': r.group(1), 'passwd2': self.man_auth_code(auth_img)})
        r = re.search('url=(.*?)>', resp.text)
        invoke_url = urljoin(self.home, r.group(1))
        http('GET', invoke_url)
        update_session_code(resp)


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
    print_table(titles, results)


if __name__ == '__main__':
    main()
