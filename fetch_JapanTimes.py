#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import datetime
import json
from robobrowser import RoboBrowser
import subprocess
import gc
import boto3

from pil_for_kindle import image_process
from send_from_gmail import create_message, send_gmail
from delete_files import delete_html, delete_toc, delete_img

with open('/home/ubuntu/newspaper/newspaper_kindle/secret.json') as sf:
    data = json.load(sf)

root = '/home/ubuntu/newspaper/JapanTimes/'

# 設定項目1:見出しページをリストに格納
lstSectionURL = ['/news/national/', '/news/business/', '/news/world/', '/news/asia-pacific/', '/opinion/', '/life/']

# 設定項目5:GmailのID
gmail_id = data['gmail_id']

# 設定項目6:Kindleのメールアドレス ※必ずリストで指定する
kindle_add = data['kindle_addresses']

# メインのブラウザ
br = RoboBrowser(parser='lxml', user_agent='a python robot', cache=True, history=True)
strRoot = 'http://www.japantimes.co.jp'  # 固定

# 画像を保存するときのファイル名に使うカウンタ
img_cnt = 0

# ページ内リンクを貼るためのカウンタ
link_cnt = 0

# 前回実行日時を読み込む
fileLastDate = open('/home/ubuntu/newspaper/newspaper_kindle/LastSubmitDate_JapanTimes.txt', 'r')
dtLastDate = fileLastDate.read()
fileLastDate.close()
print("/---" + str(dtLastDate) + "以降に更新された記事を読み込みます")

# ファイル名を設定
today = datetime.datetime.today()
strToday = today.strftime('%Y.%m.%d')

ppr_name = strToday + '_JapanTimes'
path = root + ppr_name + '.html'

# HTMLファイルを作る
html = open(path, 'w')

# 目次格納用のテキストを作る
toc = open(root + 'toc.txt', 'w')
toc.write("<ul>\n")


# ---- 見出し毎の繰り返しここから

for strSectionUrl in lstSectionURL:
    print('/---' + strSectionUrl.replace('/', ' ') + 'を実行します')
    # 記事のURLを取得しリストに格納
    # OpinionとLifeは1ページだけ。
    # ほかも、メモリリークするので1ページだけ読み込む
    lstArticleUrl = []
    if strSectionUrl in ['/opinion/', '/life/']:
        br.open(strRoot + strSectionUrl)
        strCntnt = br.find('h1', class_='page-title').text
        strCntnt = re.sub(r"\n|  ", '', strCntnt).strip()
        objSect = br.find('div', id='wrapper')
        for objHgroup in objSect.find_all('hgroup'):
            lstArticleUrl.append(objHgroup.find('p').find('a')['href'])

    else:
        for i in range(1):
            br.open(strRoot + strSectionUrl + 'page/' + str(i+1) + '/')
            strCntnt = br.find('h1', class_='page-title').text
            strCntnt = re.sub(r"\n|  ", '', strCntnt).strip()
            objSect = br.find('section')
            for objHgroup in objSect.find_all('hgroup'):
                lstArticleUrl.append(objHgroup.find('p').find('a')['href'])

    # 見出し１を作る
    html.write('<div style="page-break-after:always;"></div>\n')
    link_cnt += 1
    link_id = '{:0=8}'.format(link_cnt)
    html.write('<h1 id="' + link_id + '">' + strCntnt + '</h1>\n')
    toc.write('<li><a href="#' + link_id + '">' + strCntnt + '</a></li>\n')
    toc.write('<ul>\n')
    html.write('<div style="page-break-after:always;"></div>\n')

    # リストに格納した記事のURLにアクセス
    # 記事の日付を最初に見て、前回実行日時以降のものだったら実行。
    # 前回実行日時以前だったらループを中断
    for strArtcleUrl in lstArticleUrl:
        try:
            br.open(strArtcleUrl)
        except:
            print("/---記事読み込み失敗 スキップします")
            continue

        objArticle = br.find('article', role='main')  # 記事のタイトル・画像・記者など
        objBody = br.find('div', id='jtarticle')  # 記事本文
        try:
            dtArticleDate = objArticle.find('time')['datetime'].replace('T', ' ')[0:19]

        except:
            dtArticleDate = dtLastDate  # 日付取得でエラーになったら、前回実行日時を指定してとりあえず読み込ませる

        print("/---記事日付：" + dtArticleDate)

        # タイトル
        try:
            strTitle = objArticle.find('h1').text
            print("/---タイトル：" + strTitle.replace('\xa5', '\\').replace('\u2014', '-').replace('\u20ac', 'euro'))
        except:
            print("/---記事読み込み失敗 スキップします")
            continue

        if dtArticleDate >= dtLastDate:  # 記事日時と前回実行日時を比較。ここで判定。
            print("/---読み込みます")
            # タイトル
            link_cnt += 1
            link_id = '{:0=8}'.format(link_cnt)
            html.write('<h2 id="' + link_id + '">' + strTitle + '</h2>\n')
            toc.write('<li><a href="#' + link_id + '">' + strTitle + '</a></li>\n')
            html.write('<hr>\n')

            # 記事日時と見出し
            dtDate = datetime.datetime.strptime(dtArticleDate[0:19], '%Y-%m-%d %H:%M:%S')
            strDate = datetime.datetime.strftime(dtDate, '%B %d, %Y  %H:%M:%S')
            html.write('<h5">' + strDate + ' | ' + strCntnt + '</h5>\n')

            # 画像
            try:
                strImgSrc = objArticle.find('figure').find('img')['src']
                img_cnt += 1
                img_name = '{:0=4}'.format(img_cnt) + '.jpg'
                img_path = root + img_name
                image_process(strImgSrc, img_path)
                html.write('<img src="' + root + img_name + '">\n')
            except:
                pass

            # 画像説明文
            try:
                strImgCpt = objArticle.find('figure').find('figcaption').text
                html.write('<h6">' + strImgCpt + '</h6>\n')
            except:
                pass

            # 記事本文
            for objElm in objBody.find_all('p'):
                strArticleText = objElm.text.strip()
                strArticleText = strArticleText.replace('’', '\'')
                strArticleText = strArticleText.replace('¥', '\\')
                html.write('<p>' + strArticleText + '</p>\n')

            # クレジットとライター
            try:
                strCredit = objArticle.find('p', class_='credit').text
            except:
                strCredit = ''
            try:
                strWriter = objArticle.find('h5').text
            except:
                strWriter = ''
            if len(strCredit + strWriter) > 0:
                html.write('<p>(' + strCredit + ' ' + strWriter + ')</p>\n')

            html.write('<div style="page-break-after:always;"></div>\n')

        else:
            print("/---処理をスキップします")
            continue

    # メモリ管理
    try:
        del objSect
        del objHgroup
        del objArticle
        del objBody
        del objElm

    except:
        pass

    gc.collect()

    # ---- 見出し毎の繰り返しここまで
    toc.write('</ul>\n')

toc.write('</ul>\n')
toc.close()
html.close()

# HTMLに必要なタグと目次を入れる
print('/---目次挿入中')
s = '<!DOCTYPE html>\n' \
    '<html lang="en">\n ' \
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

# メモリ管理
del br
del toc
del html
gc.collect()

# pandocでdocxに変換
print('/---docxファイル作成中')
res = subprocess.run(['pandoc', path, '-o', root + ppr_name + '.docx', '--reference-doc=/home/ubuntu/newspaper/reference/reference.docx'])

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

# S3へアップロード
print('/---S3にアップロード中：' + ppr_name)
s3 = boto3.resource('s3')
bucket = s3.Bucket('newspaper-kensei')
bucket.upload_file(filepath, 'JapanTimes/' + filename)

# 今回実行日時をファイルに書き込む
fileLastDate = open('/home/ubuntu/newspaper/newspaper_kindle/LastSubmitDate_JapanTimes.txt', 'w')
dtLastDate = fileLastDate.write(str(datetime.datetime.now()))
fileLastDate.close()
print('/---今回実行日時は：' + str(datetime.datetime.now()))

# 不要ファイルを削除する
print('/---不要ファイル削除中')
delete_html(path)
delete_toc(root)
delete_img(root)
delete_docx(filepath)

print('/---処理を終了しました。')
