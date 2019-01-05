#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
from PIL import Image
from robobrowser import RoboBrowser
import gc


# 画像の下処理。サイズを小さくして、グレースケールにする。クオリティは変えない
def image_process(img_src, img_path):
    br = RoboBrowser(parser='lxml', user_agent='a python robot2', history=True)
    request = br.session.get(img_src, stream=True)

    try:
        with open(img_path, "wb") as img_file:
            img_file.write(request.content)

        time.sleep(0.3)
        im = Image.open(img_path)
        # print(im.format, im.size, im.mode)

        if im.size[0] > 500:
            rate = 500 / im.size[0]
        else:
            rate = 1
        # print(str(rate))
        size = (int(im.size[0] * rate), int(im.size[1] * rate))
        new_img = im.resize(size).convert('L')
        # print(new_im.format, new_im.size, new_im.mode)
        new_img.save(img_path)

        del img_file
        del new_img
        gc.collect()

    except:
        print('/---Warning:画像読み込みできなかったよ')

    del br
    gc.collect()
    

if __name__ == '__main__':
    print("このコードはインポートして使ってね。")
