#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import datetime
import json
from robobrowser import RoboBrowser
import subprocess

from send_from_gmail import create_message, send_gmail
from delete_files import delete_html, delete_toc

with open('secret.json') as sf:
    data = json.load(sf)

# 設定項目1：丸三証券のログインID・PWを変数に
koza_id = data['telecom_id']
koza_pw = data['telecom_pw']

# 設定項目2：新聞の種類をタプルに格納
ppr_tpl = ('NKM', 'NSS', 'NRS', 'NKL')
# ppr_tpl=('NKM','NKE','NSS','NRS','NKL','NKP')
# NKM：日本経済新聞朝刊
# NKE：日本経済新聞夕刊
# NSS：日経産業新聞
# NRS：日経ＭＪ（流通新聞）
# NKL：日経地方経済面
# NKP：日経プラスワン


# 設定項目3:何日前の新聞を取得するか
ppr_bfr = 0

# 設定項目4:ファイルの保存フォルダを指定
root = '/home/ubuntu/newspaper/store_Telecom/'

# 設定項目5:GmailのID
gmail_id = data['gmail_id']

# 設定項目6:Kindleのメールアドレス ※必ずリストで指定する
kindle_add = data['kindle_addresses']

# ページ内リンクを貼るためのカウンタ
link_cnt = 0

# ファイル名を設定
today = datetime.datetime.today()
strToday = today.strftime('%Y.%m.%d')

ppr_name = strToday + '_日本経済新聞'
path = root + ppr_name + '.html'

# ファイルを開いておく
html = open(path, 'w')
toc = open(root + 'toc.txt', 'w')
toc.write("<ul>\n")


# 読み込み処理開始
# 取得する日の日付を取得
today = datetime.datetime.now()
today -= datetime.timedelta(days=ppr_bfr)
tgt_dt = today.strftime('%Y%m%d')

# ロボブラウザを起動
br = RoboBrowser(parser='lxml', user_agent='a python robot', cache=True, history=False)

# ログイン処理
br.open('https://trade.03trade.com/web/')
form = br.get_form(action='/web/cmnCauSysLgiAction.do')
form['loginTuskKuzNo'].value = koza_id
form['gnziLoginPswd'].value = koza_pw
br.submit_form(form)
print(br.find('title').text)

# 日経テレコンのページへ移動。いくつか遷移する。
br.open('https://trade.03trade.com/web/cmnCauSysLgiSelectAction.do')
tel_url = br.find('a', title='日経テレコン')['onclick'].replace('javascript:window.open(', '') \
    .replace('\'', '').split(',')[0]
br.open(tel_url)

meta_url = br.find_all('meta')[0]['content'].replace('0; url=', '')
br.open(meta_url)

form = br.get_form(action='http://t21.nikkei.co.jp/g3/p03/LCMNDF11.do')
br.submit_form(form)

form = br.get_form(action='LATCA011.do')
br.submit_form(form)

cmp_pprs = []  # 処理済新聞リスト
cnt = 0
for ppr_elm in ppr_tpl:
    cnt += 1
    ppr_url = 'http://t21.nikkei.co.jp/g3/p03/LATCB012.do?mediaCode=' + ppr_elm
    print(ppr_url)

    # 新聞記事のページへ
    br.open(ppr_url)

    # 一番最初の記事から、日付を取得（yyyy/㎜/dd形式）
    info = br.find('li', class_='AttInfoBody').text.replace(u'\xa0', u' ').split(u' ')
    dt = info[0]

    # パンくずリストから新聞名を取得
    ppr = br.find('p', class_='topicPath').find_all('a')[1].text
    print(dt + ppr)

    # 新聞名が取得済リストにないならやる。←無い新聞のページに行ったら朝刊が表示される対策
    if (ppr in cmp_pprs) == False:

        # 日付が取得対象日付だったらやる。違ったらやらない。
        date = datetime.datetime.strptime(dt, '%Y/%m/%d')
        ppr_dt = datetime.date(date.year, date.month, date.day)
        ppr_dt = ppr_dt.strftime('%Y%m%d')

        if tgt_dt == ppr_dt:

            # 面タイトルをリストに格納
            Nav = []
            newsNavs = br.find_all('div', class_='newsNav')
            for newsNav in newsNavs:
                try:
                    newsNav_text = newsNav.find('label').text
                    Nav.append(newsNav_text)
                    print(newsNav_text)
                except:
                    pass

            # 面ごとのタイトルリスト・URLリスト・記事本文リスト・ソースリストを、それぞれリストで格納
            Ttls = []
            Srcs = []
            Txts = []
            newsBlks = br.find_all('ul', class_='listNews valCheck')
            for newsBlk in newsBlks:
                Ttl = []
                Src = []
                Txt = []
                newsIdxs = newsBlk.find_all('li', class_='headlineTwoToneA js-toggle')
                for newsIdx in newsIdxs:
                    try:
                        newsTtl = newsIdx.find('p').find('a').text
                        Ttl.append(newsTtl)
                        newsSrc = newsIdx.find('li', class_='AttInfoBody').text.split(u'\xa0')[1].replace('　', ' ')
                        Src.append(newsSrc)
                        newsUrl = 'http://t21.nikkei.co.jp'+newsIdx.find('a')['href']
                        br.open(newsUrl)
                        print(br.find('h2').text)
                        art_text = br.find('div', class_='col col10 artCSS_Highlight_on').find('p')
                        art_text = str(art_text)  # 注:文字型に変換してあげないとoutertextを扱えない
                        art_text = re.sub(r'</?p?(br)?/?>', '\n', art_text)  # pタグとbrタグを改行に置換
                        Txt.append(art_text)
                    except:
                        pass
                Ttls.append(Ttl)
                Srcs.append(Src)
                Txts.append(Txt)

            # ファイル書き出し処理
            print('ファイル更新中...' + dt + ppr)

            # 見出し1(新聞名)を作る
            html.write('<div style="page-break-after:always;"></div>\n')
            link_cnt += 1
            link_id = '{:0=8}'.format(link_cnt)
            html.write('<h1 id="' + link_id + '">' + ppr + '</h1>\n')
            toc.write('<li><a href="#' + link_id + '">' + ppr + '</a></li>\n')
            toc.write('<ul>\n')
            html.write('<div style="page-break-after:always;"></div>\n')

            for i in range(len(Nav)):
                # 見出し2(カテゴリ)を作る
                link_cnt += 1
                link_id = '{:0=8}'.format(link_cnt)
                html.write('<h2 id="' + link_id + '">' + Nav[i] + '</h2>\n')
                toc.write('<li><a href="#' + link_id + '">' + Nav[i] + '</a></li>\n')
                toc.write('<ul>\n')
                html.write('<div style="page-break-after:always;"></div>\n')

                for j in range(len(Ttls[i])):
                    # 見出し3(記事タイトル)を作る
                    link_cnt += 1
                    link_id = '{:0=8}'.format(link_cnt)
                    html.write('<h3 id="' + link_id + '">' + Ttls[i][j] + '</h3>\n')
                    toc.write('<li><a href="#' + link_id + '">' + Ttls[i][j]+ '</a></li>\n')
                    html.write('<hr>\n')

                    # 日付を入れる
                    html.write('<div class="date">' + Srcs[i][j] + '</div>\n')

                    # 記事本文を入れる
                    html.write('<p>' + Txts[i][j] + '</p>\n')
                    html.write('<div style="page-break-after:always;"></div>\n')

                toc.write('</ul>\n')

            toc.write('</ul>\n')

        # 日付が取得対象日付じゃなかったらパス
        else:
            pass

        cmp_pprs.append(ppr)  # 処理済み新聞リストに追加

    # 新聞名が取得済リストにあったらパス
    else:
        pass

toc.write('</ul>\n')

# 目次を更新
print('/---目次挿入中')
s = '<!DOCTYPE html>\n' \
    '<html lang="ja">\n ' \
    '<head>\n ' \
    '<meta charset="utf-8">\n ' \
    '<title>' + ppr_name + '</title>\n' \
    '<link rel="stylesheet" type="text/css" href="../newspaper_kindle/style.css">\n' \
    '</head>\n' \
    '<body>\n'

with open(root + 'toc.txt') as toc:
    s = s + toc.read()

with open(path) as html:
    line = html.readlines()

line.insert(0, s)

with open(path, mode='w') as html:
    html.writelines(line)

with open(path, mode='a') as html:
    html.write('</body>\n</html>')

# pandocでdocxに変換
print('/---docxファイル作成中')
res = subprocess.run(['pandoc', path, '-o', root + ppr_name + '.docx'])

# Kindleへメールで送る
subject = ppr_name
body = "kindleへ送信"
filename = ppr_name + '.docx'
filepath = path.replace('.html', '.docx')
mine = {'type': 'application', 'subtype': 'vnd.openxmlformats-officedocument.wordprocessingml.document'}
attach_file = {'name': filename, 'path': filepath}
print('/---メール送信中：' + ppr_name)

msg = create_message(gmail_id, kindle_add, subject, body, mine, attach_file)
send_gmail(gmail_id, kindle_add, msg)

# ログアウト
br.open('https://trade.03trade.com/web/cmnCauSysLgoAction.do')
print(br.find('title').text)
prompt = br.find('h3', class_='function_name').text.encode('shift-jis').decode('shift-jis','replace')
print(prompt)

# 不要ファイルを削除する
print('/---不要ファイル削除中')
delete_html(path)
delete_toc(root)

print('/---処理を終了しました。')
