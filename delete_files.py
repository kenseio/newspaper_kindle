#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import glob


def delete_html(path):
    if os.path.isfile(path):
        os.remove(path)

def delete_toc(root):
    if os.path.isfile(root + 'toc.txt'):
        os.remove(root + 'toc.txt')

def delete_img(root):
    for p in glob.glob(root + '*.jpg'):
        if os.path.isfile(p):
            os.remove(p)

def delete_docx(filepath):
    if os.path.isfile(filepath):
        os.remove(filepath)

if __name__ == '__main__':
    print("このコードはインポートして使ってね。")
