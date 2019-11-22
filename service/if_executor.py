from datetime import datetime

import base64
import json
import requests
import boto3
import os

root_path = r'.'

# 미사용
def call_police_api():
    url = 'http://www.safe182.go.kr/api/lcm/findChildList.do'
    data = {'esntlId': '10000289', 'authKey': 'c30895abb641429f', 'rowSize': '100'}
    # data = {'esntlId': '10000289', 'authKey': 'c30895abb641429f', 'rowSize': '100', 'writngTrgetDscds': ['010','061']}
    # AWS Value
    bucketName = "ifind"
    collectionId = 'IFCollection'
    fileName = "source.jpg"
    s3fileName = "source1.jpg"

    r = requests.post(url, data)
    result = json.loads(r.content.decode('utf-8'))
    targets = result['list']
    targets.sort(key=lambda x: x['occrde'])
    # AWS 연결
    client = boto3.client('rekognition')

    for idx, i in enumerate(targets):
        if i['writngTrgetDscd'] in ['010', '061']:
            continue
        name = i['nm']
        occrde = i['occrde']
        age = i['age']
        gender = i['sexdstnDscd']
        userId = i['msspsnIdntfccd']
        feature = i['etcSpfeatr']
        address = i['occrAdres']
        photo_url = ''

        # 사진이 존재한다면 다운로드 후 AWS 얼굴 특징 등록
        if i['tknphotolength'] > 0:
            photo_name = 'dataset\\' + str(age) + '_' + ('0' if gender == '남자' else '1') + '_2_' + str(
                datetime.timestamp(datetime.now())) + '.jpg.chip.jpg'
            image_64_decode = base64.b64decode(i['tknphotoFile'])
            image_result = open(photo_name, 'wb')
            image_result.write(image_64_decode)
            # photo_url = "http://www.safe182.go.kr/api/lcm/imgView.do?msspsnIdntfccd=" + userId

            # 얼굴 특징 등록 (S3 버킷에 업로드 -> Rekognition에 등록)
            #    추후에 return 추가 필요
            # S3에 존재여부 확인
            # am.add_face_to_collection(client, collectionId, bucketName, photo_name)

def checkID(fm, uid):
    a = fm.collectionGroup(u'users').where(u'ID', u'==', uid)
    docs = a.stream()
    res = []
    for i in docs:
        res.append(i.to_dict())
        print(i.to_dict())
    if len(res) > 0:
        return True
    return False


def getIDInfo(fm, uid, isDocRef=False):
    a = fm.collectionGroup(u'users').where(u'ID', u'==', uid)
    docs = a.stream()
    res = []

    for i in docs:
        res.append(i.to_dict())
        docRef = i
        print(i.to_dict())
    if len(res) > 0:
        if isDocRef:
            return docRef
        return res[0]
    return None


def checkChildName(fm, uid, cname, infoOption=False):
    a = fm.readCollection(fm.getCollection(u'users/' + uid + u'/child'))
    # empty는 항상 제거
    del a['empty']

    for k, v in a.items():
        if 'name' in v:
            if v['name'] == cname:
                if infoOption:
                    return k, a[k]
                return True
    if infoOption:
        return None, None
    return False


def checkMissingName(fm, uid, mname, infoOption=False):
    a = fm.readCollection(fm.getCollection(u'users/' + uid + u'/Missing_post'))
    b = fm.readCollection(fm.getCollection(u'users/' + uid + u'/Missing_long_post'))
    # empty는 항상 제거
    del a['empty']
    del b['empty']

    for k, v in a.items():
        if 'name' in v:
            if v['name'] == mname:
                if infoOption:
                    a[k]['type'] = 0
                    return k, a[k]
                return True
    for k, v in b.items():
        if 'name' in v:
            if v['name'] == mname:
                if infoOption:
                    b[k]['type'] = 1
                    return k, b[k]
                return True
    if infoOption:
        return None, None
    return False


def checkComment(fm, pid, cid, name, infoOption=False):
    key, value = checkMissingName(fm, pid, name, True)
    a = fm.readCollection(fm.getCollection(
        u'users/' + pid + u'/Missing_' + (u'long_' if value['type'] is 1 else '') + u'post/' + key + u'/Report'))

    # empty는 항상 제거
    del a['empty']

    for k in a.keys():
        if k == cid:
            if infoOption:
                return u'users/' + pid + u'/Missing_' + ('long_' if value[
                                                                       'type'] is 1 else '') + 'post/' + key + u'/Report/' + k
            return True
    return False

def getMissingByFace(fm, faceID, isDocRef=False):
    short_result = fm.collectionGroup(u'Missing_post').where(u'face', u'==', faceID)

    docs = short_result.stream()

    res = []

    for i in docs:
        # res.append(i.to_dict())
        # docRef = i
        print(i)
        return i
    long_result = fm.collectionGroup(u'Missing_long_post').where(u'face', u'==', faceID)
    docs = long_result.stream()
    for i in docs:
        # res.append(i.to_dict())
        # docRef = i
        print(i)
        return i
    return None


def saveB64(photo, image_path):
    image_64_decode = base64.urlsafe_b64decode(photo)
    image_result = open(image_path, 'wb')
    image_result.write(image_64_decode)
    return image_result

def loadB64(image_path):
    image_result = open(image_path, 'rb').read()
    image_64_encode = base64.urlsafe_b64encode(image_result)
    return image_64_encode.decode()

def uploadImg(inst, key, directory, photo1, photo2=None, isImgIdx = True, isMissingFace = False):
    img_idx = '1'
    if photo1 is None and photo2:
        img_idx = '2'

    faceIDs = []
    while True:
        localPath = os.path.join(root_path, directory+'/' + key + ('_' + img_idx if isImgIdx else '')+'.jpg')
        s3path = directory+'/' + key + ('_' + img_idx if isImgIdx else '')+'.jpg'
        saveB64(photo1 if img_idx == '1' else photo2, localPath)

        # s3 업로드
        inst.getS3M().upload(localPath, s3path)
        if isMissingFace:
            faceRecords, unrecords = inst.getRekoM().addFace(s3path, inst.getS3M().getBucket(), s3path)
            if len(faceRecords) > 0:
                faceIDs.append(faceRecords[0]['Face']['FaceId'])

        if img_idx == '1' and photo2:
            img_idx = '2'
        else:
            break

    if isMissingFace:
        return faceIDs

def getPostImgAsB64(inst, key, isLong=False):
    post_pic_idx = '1'
    post_s3path = 'posts/' + key + '_' + post_pic_idx + '.jpg'
    post_path = os.path.join(root_path, 'posts/' + key + '_' + post_pic_idx + '.jpg')

    result = {}; maxIdx = 2
    if isLong:
        maxIdx = 3
    for idx in range(1, maxIdx):
        post_pic_idx = str(idx)
        if inst.getS3M().isExist(post_s3path):
            # s3에서 다운로드
            inst.getS3M().download(post_s3path, post_path)
            result['photo' + post_pic_idx] = loadB64(post_path)
        else:
            result['photo' + post_pic_idx] = None

    return result

def downloadImg(inst, key, directory, isImgIdx=True, isLong=False):
    img_idx = '1'


    result = {}; maxIdx = 2
    if isLong:
        maxIdx = 3
    for idx in range(1, maxIdx):
        img_idx = str(idx)
        localPath = os.path.join(root_path, directory + '/' + key + ('_' + img_idx if isImgIdx else '') + '.jpg')
        s3path = directory + '/' + key + ('_' + img_idx if isImgIdx else '') + '.jpg'

        if inst.getS3M().isExist(s3path):
            # s3에서 다운로드
            inst.getS3M().download(s3path, localPath)
            result['photo' + (img_idx if isImgIdx else '')] = loadB64(localPath)
        else:
            result['photo' + (img_idx if isImgIdx else '')] = None

    return result
