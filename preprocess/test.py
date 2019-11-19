import json
import os

import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from preprocess.firebase_manager import FBManager
import preprocess.if_executor as ie
from preprocess.aws_manager import AWSManager as am

from time import sleep
import numpy as np
from PIL import Image
from datetime import datetime
import sys
sys.path.append(r'C:\Users\DeepLearning_3\PycharmProjects\firebase_dump1\lib')
from tinydb_manager import TinyDBManager
from tinydb import Query, TinyDB


import cv2

from tqdm import tqdm

cred = credentials.Certificate('keys/i-find-521d7-firebase-adminsdk-wemsi-4fca9d0fb8.json')
firebase_admin.initialize_app(cred)
fm = FBManager(firestore.client())
inst = am.getInstance()
if inst.checkConnected() is False:
    inst.connect('ifind', 'IFCollection')

root_path = r'C:\Users\DeepLearning_3\PycharmProjects\ipcgan_clone\preprocess\posts'
db = TinyDBManager(db_file=r'D:\Data\TinyDB\db.json', default_table='ganQueue')
table = db.getTable()
Request = Query()

while True:
    # firebase 체크하기
    # 5초마다 grabbed=False 인 것을 가져옴.
    # gan_list = fm.readCollection(fm.getCollection(u'ganStack'))
    if table.count(Request.grabbed == False) > 0:
        waiting_list = []
        count = 0
        gan_list = table.search((Request.grabbed == False))
        for i in gan_list:
            if count >= 10:
                break
            waiting_list.append(i)
            count += 1
        if not waiting_list:
            print("\n[INFO] 0 Grabbed")
            sleep(5)
            continue
        print("\n[INFO] "+str(count)+" Grabbed")

        # 사진 저장
        target = []
        for w in waiting_list:
            # path = 'users/'+w['id']+'/Missing_long_post/'+w['key']

            # s3에서 사진 다운로드 받기
            results = ie.downloadImg(inst, w['key'], 'posts', True, True)

            # 필요없는 사진은 삭제
            if w['type2'] is 0 and os.path.exists(os.path.join(root_path, w['key'] + '_2.jpg')):
                os.remove(os.path.join(root_path, w['key'] + '_2.jpg'))
            if w['type2'] is 1 and os.path.exists(os.path.join(root_path, w['key'] + '_1.jpg')):
                os.remove(os.path.join(root_path, w['key'] + '_1.jpg'))

            filename = w['key'] + ("_1.jpg" if w['type2'] is 0 else "_2.jpg")
            img_path  = os.path.join(root_path, filename)
            with Image.open(img_path) as img:
                width, height = img.size
                if width > 900 or height > 900:
                    npimage = None
                    try:
                        npimage = np.array(img)
                    except Exception as ex:
                        continue
                    crop_img=cv2.resize(npimage,(900,900))
                    Image.fromarray(crop_img.astype(np.uint8)).save(img_path)


            if not results['photo1'] and not results['photo2']:
                print("[ERROR] Both PHOTO1 And PHOTO2 : None")
                continue
            # db.update({'value': 2}, doc_ids=[1, 2])
            table.upsert({'grabbed': True}, Request.key == w['key'])
            # firebase 업데이트
            # fm.updateDocument(fm.getDocument(u'ganStack/' + k), {'grabbed': True})
            t_result = datetime.now() - datetime.strptime(w['date'].split()[0], '%Y-%m-%d')
            age = int(w['age']) + (((int(t_result.days / 365))+1) if t_result.days > 0 else 0)
            filename = w['key'] + ('_1.jpg' if w['type2'] is 1 else '_2.jpg')
            if w['type2'] is 1:
                age = w['age']

            category = 0
            age = int(age)
            if 20 <= age < 30:
                category = 1
            elif 30 <= age < 40:
                category = 2
            elif 40 <= age < 50:
                category = 3
            elif 50 <= age:
                category = 4
            print("[INFO] ", w['key'], '==> Category : ', category, ', age : ', age)
            target.append((w, filename, category))

        filenames = ""; categories = ""; types = ""
        for idx, (w, filename, category) in enumerate(target):
            filenames += w['key'] + ("," if idx+1 != len(target) else "")
            categories += str(category) + ("," if idx+1 != len(target) else "")
            types += str(w['type2']) + ("," if idx+1 != len(target) else "")
        os.system("python model_test.py " +filenames + " "+categories + " "+types)

        while True:
            notExist = False
            for idx, (w, filename, category) in enumerate(target):
                if not os.path.exists(os.path.join(root_path, w['key']+('_2' if w['type2'] == 0 else '_1') + '.jpg')):
                    notExist = True

            if not notExist:
                break
            sleep(3)
        for idx, (w, filename, category) in enumerate(target):
            ie.uploadImg(inst, w['key'], 'posts', None if w['type2'] is 0 else 'dsdsds', 'dsaasasdsda' if w['type2'] is 0 else None,
                         True, False, True)

            table.remove(doc_ids=[table.get(Request.key == w['key']).doc_id])
            if os.path.exists(os.path.join(root_path, w['key'] + '_1.jpg')):
                os.remove(os.path.join(root_path, w['key'] + '_1.jpg'))
                print("[INFO] Deleted : ", w['key'] + '_1.jpg')
            if os.path.exists(os.path.join(root_path, w['key'] + '_2.jpg')):
                os.remove(os.path.join(root_path, w['key'] + '_2.jpg'))
                print("[INFO] Deleted : ", w['key'] + '_2.jpg')

    else:
        print(".", end='', flush=True)
        sleep(5)
        continue











# 원본 삭제

# s3에 업로드

# firebase 삭제
