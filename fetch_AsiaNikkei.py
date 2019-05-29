#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import datetime
import json
from pytz import timezone
from robobrowser import RoboBrowser
import subprocess
import gc
import boto3

from pil_for_kindle import image_process
from send_from_gmail import create_message, send_gmail
from delete_files import delete_html, delete_toc, delete_img, delete_docx


with open('/home/ubuntu/newspaper/newspaper_kindle/secret.json') as sf:
    data = json.load(sf)

root = '/home/ubuntu/newspaper/work/'

# 設定項目1:見出しページをリストに格納
lstSectionURL = ['/Editor-s-Picks/', '/Business/', '/Economy/', '/Politics/']

# 設定項目5:GmailのID
gmail_id = data['gmail_id']

# 設定項目6:Kindleのメールアドレス ※必ずリストで指定する
kindle_add = data['kindle_addresses']

# メインのブラウザ
br = RoboBrowser(parser='lxml', user_agent='a python robot', cache=True, history=True)
strRoot = 'http://asia.nikkei.com'  # 固定

# 画像を保存するときのファイル名に使うカウンタ
img_cnt = 0

# ページ内リンクを貼るためのカウンタ
link_cnt = 0

# 前回実行日時を読み込む
fileLastDate = open('/home/ubuntu/newspaper/newspaper_kindle/LastSubmitDate_AsiaNikkei.txt', 'r')
strLastDate = fileLastDate.read()
dtLastDate = datetime.datetime.strptime(strLastDate[0:19], '%Y-%m-%d %H:%M:%S').astimezone(timezone('Asia/Tokyo'))
fileLastDate.close()
print("/---" + str(strLastDate) + "以降に更新された記事を読み込みます")

# ファイル名を設定
today = datetime.datetime.today()
strToday = today.strftime('%Y.%m.%d')

ppr_name = strToday + '_NikkeiAsianReview'
path = root + ppr_name + '.html'

# HTMLファイルを作る
html = open(path, 'w')

# 目次格納用のテキストを作る
toc = open(root + 'toc.txt', 'w')
toc.write("<ul>\n")

# ---- 見出し毎の繰り返しここから
for SectionURL in lstSectionURL:
    print('/---' + SectionURL.replace('/', ' ') + 'を実行します')
    # 見出しページの2ページ目まで読み込んで、記事の日付とURLを取得し、それぞれリストに格納
    lstTitle = []
    lstArticleUrl = []
    lstDt = []
    for i in range(2):
        strSect = SectionURL + '?page=' + str(i + 1)
        br.open(strRoot + strSect)
        strCntnt = br.find('header', class_='content__header').find('span', class_='ezstring-field').text
        objCntnt = br.find('section', id='article-stream')
        # aタグかつ、title属性があって、テキストもあるものを全て拾う。写真のリンクは拾いたくない。
        tagTitles = objCntnt.find_all('a', title=re.compile('\w*'), text=re.compile('\w*'))
        for tagTitle in tagTitles:
            if tagTitle.parent.name != 'li':
                lstTitle.append(tagTitle.text)
                lstArticleUrl.append(tagTitle.parent.find('a')['href'])
                strArticleDate = tagTitle.find_next('time')['data-time-utc']
                dtArticleDate = (datetime.datetime.strptime(strArticleDate, '%B %d, %Y %H:%M %Z')
                                 + datetime.timedelta(hours=9)).astimezone(timezone('Asia/Tokyo'))
                lstDt.append(dtArticleDate)

    # 見出し1を作る
    html.write('<div style="page-break-after:always;"></div>\n')
    link_cnt += 1
    link_id = '{:0=8}'.format(link_cnt)
    html.write('<h1 id="' + link_id + '">' + strCntnt + '</h1>\n')
    toc.write('<li><a href="#' + link_id + '">' + strCntnt + '</a></li>\n')
    toc.write('<ul>\n')
    html.write('<div style="page-break-after:always;"></div>\n')

    # 記事日付が前回実行日時より新しいものを読み込んで、htmlに書き出し。
    for j in range(len(lstDt)):
        print("/---" + str(j + 1) + "個目の記事を処理します")
        print("/---記事日付：" + str(lstDt[j]))
        print("/---タイトル：" + lstTitle[j])

        print(lstDt[j], dtLastDate)
        if lstDt[j] > dtLastDate:
            print("/---読み込みます")
            print("/---記事URL：" + strRoot + lstArticleUrl[j])

            # 記事URLを開いて、NOT FOUNDだったらスキップ
            br.open(strRoot + lstArticleUrl[j])
            if '200' not in str(br.response):
                print("/---記事URLがNot Foundでした")
                continue

            # タイトル見出し2
            strTitle = br.find('h1', class_='article__title').text
            link_cnt += 1
            link_id = '{:0=8}'.format(link_cnt)
            html.write('<h2 id="' + link_id + '">' + strTitle + '</h2>\n')
            toc.write('<li><a href="#' + link_id + '">' + strTitle + '</a></li>\n')
            html.write('<hr>\n')

            # 日付+見出し
            strTopic = br.find('span', class_='article__topic').text.strip()
            strDate = br.find('div', class_='article__details').find('time').text
            strDate = re.sub(r"\n|  ", '', strDate).strip()
            html.write('<h5>' + strDate + ' | ' + strTopic + '</h5>\n')

            # サブタイトル
            try:
                strSubtitle = br.find('p', class_='article__sub-title').text
                html.write('<h4>' + strSubtitle + '</h4>\n')
            except:
                print('/---Note:サブタイトル無かった')

            # Articleタグ配下で最初に出てくる画像を探す。
            # 本文の画像は別途取得するので、親タグのクラスが"article" "article__content"のどっちか。
            # ただし、無いかもしれない。
            try:
                objImg = br.find('div', class_='article').find('img')
                if objImg.parent['class'][0] in ['article', 'article__content']:
                    strImgSrc = objImg['src']
                    img_cnt += 1
                    img_name = '{:0=4}'.format(img_cnt) + '.jpg'
                    img_path = root + img_name
                    image_process(strImgSrc, img_path)
                    html.write('<img src="' + root + img_name + '">\n')

                else:
                    print('/---Note:画像無かったよ')
            except:
                print('/---Note:画像無かったよ')

            # 画像説明文
            try:
                objImgCpt = br.find('div', class_='article').find('span', class_='article__caption')
                if objImgCpt.parent['class'][0] in ['article', 'article__content']:
                    strImgCpt = objImgCpt.text
                    strImgCpt = re.sub(r"\t|\n|\xa0|\xa9|  ", '', strImgCpt).strip()
                    html.write('<h6">' + strImgCpt + '</h6>\n')
                else:
                    print('/---Note:画像説明文無かったよ')
            except:
                print('/---Note:画像説明文無かったよ')

            # 本文中のテキスト・画像・画像説明文
            objArticle = br.find('div', class_='ezrichtext-field')
            for objElm in objArticle.descendants:
                if objElm.name == 'p':
                    strArticleText = objElm.text
                    html.write('<p>' + strArticleText + '</p>\n')

                elif objElm.name == 'img':
                    strImgSrc = objElm['src']
                    img_cnt += 1
                    img_name = '{:0=4}'.format(img_cnt) + '.jpg'
                    img_path = root + img_name
                    image_process(strImgSrc, img_path)
                    html.write('<img src="' + root + img_name + '">\n')

                elif objElm.name == 'span' and objElm['class'][0] == 'article__caption':
                    strImgCpt = objElm.text
                    strImgCpt = re.sub(r"\t|\n|\xa0|\xa9|  ", '', strImgCpt).strip()
                    html.write('<h6>' + strImgCpt + '</h6>\n')

            # author
            try:
                strAuthor = br.find('div', class_='article__details').find('span', class_='article__author').text.strip()
                html.write('<p>(' + strAuthor + ')</p>\n')
            except:
                print('/---Note:Author無かった')

            html.write('<div style="page-break-after:always;"></div>\n')

            # ひとつの記事ここまで

        else:
            print("/---読み込みません")

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
bucket.upload_file(filepath, 'AsiaNikkei/' + filename)

# 今回実行日時をファイルに書き込む
fileLastDate = open('/home/ubuntu/newspaper/newspaper_kindle/LastSubmitDate_AsiaNikkei.txt', 'w')
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
