import base64

from flask import Flask, jsonify
from flask import request, send_file
from flask_ipban import IpBan
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from service.firebase_manager import FBManager
from service import if_executor as ie
from service.aws_manager import AWSManager as am
import os
from service.lib.tinydb_manager import TinyDBManager

app = Flask(__name__)
ip_ban = IpBan(app)
#ttt
# SPAM 처리
ip_ban_list = ['77.247.110.54', '211.150.70.18', '198.108.67.80', '223.105.4.250', '80.82.70.187', '201.48.117.175',
               '177.11.136.7', '106.12.123.186', '190.58.249.214', '204.11.5.125', '106.13.33.128',
               '58.87.104.102', '113.160.144.113']
ip_ban.block(ip_ban_list, permanent=True)

# access를 위해 아래 json 파일은 인증을 위해 반드시 필요.
# firebase 내 규칙을 수정하더라도 이 프로그램은 영향x
cred = credentials.Certificate('keys/i-find-521d7-firebase-adminsdk-wemsi-4fca9d0fb8.json')
firebase_admin.initialize_app(cred)
fm = FBManager(firestore.client())
inst = am.getInstance()
if inst.checkConnected() is False:
    inst.connect('ifind', 'IFCollection')
db = TinyDBManager(db_file=r'D:\Data\TinyDB\db.json', default_table='ganQueue')


# @app.route('/member/register2', methods=['POST'])
# def register2():
#     a = request.files
#     d = request.args
#     b = request.form
#     c = request.form.get('uploaded_file')
#     # a = request.args.get('uploaded_file')
#     aa = request.files['uploadedfile']
#     aaa = aa.filename.split('/')
#     aa.save(aaa[-1])
#
#     f = open('.\\test.jpg', 'w', -1, "utf-8")
#     f.write(c)
#     f.close()
#     return '200';


@app.route('/download/<string:dataset>')
def download_datasets(dataset):
    # file list
    ''' Dataset List
    연령대_20대1
    20대2_30대1
    30대2
    30대3
    '''
    print(dataset)
    if not os.path.exists("_files/"+dataset+".zip"):
        return '0'
    file_name = f"_files/"+dataset+".zip"
    return send_file(file_name,
                     # mimetype='text/csv',
                     attachment_filename=dataset+'.zip',# 다운받아지는 파일 이름.
                     as_attachment=True)

# 회원가입/탈퇴
# 11월 02일 구현 완료
@app.route('/member/register', methods=['POST'])
@app.route('/member/unregister', methods=['POST'])
def register():
    result_dict = {}

    uid = request.args.get('id')
    pw = request.args.get('pw')

    # profile_photo = request.files['photo']
    if uid and pw:
        if '/member/register' in request.path:
            # 회원가입 -> id, pw, 주소, 이름, 전번, 프로필 사진(None) -> True/False
            addr = request.args.get('addr')
            phone = request.args.get('phone')
            name = request.args.get('name')
            profile_photo = request.args.get('photo')
            if addr and phone and name:
                # 존재여부 체크
                if ie.checkID(fm, uid):
                    result_dict['result'] = False
                    result_dict['err_code'] = 'EXISTING_ID'
                else:
                    if profile_photo:
                        ie.uploadImg(inst, uid, 'profiles', profile_photo, None, False)
                        # image_path = '.\\profiles\\' + uid + '.jpg'
                        # ie.saveB64(profile_photo, image_path)

                        # s3로 업로드
                        # inst.getS3M().upload(image_path, 'profiles/'+uid+'.jpg')

                    res_time, doc_ref = fm.addDocument(fm.getCollection(u'users'), {
                        u'ID': uid,
                        u'PW': pw,
                        u'name': name,
                        u'address': addr,
                        u'phone': phone
                        # u'photo': profile_photo if profile_photo else None
                    }, uid)
                    result_dict['result'] = True

                    if fm.addEmptyCollection(doc_ref, [u'child', u'Missing_post', u'Missing_long_post']) is False:
                        result_dict['err_code'] = 'SUBCOLLECTION_FAIL'

            else:
                result_dict['result'] = False
                result_dict['err_code'] = 'ERROR'
        elif '/member/unregister' in request.path:
            # 회원탈퇴 -> id, pw -> True/False
            idInfo = ie.getIDInfo(fm, uid)
            if idInfo is not None:
                if pw == idInfo['PW']:
                    if fm.deleteCollection(fm.getCollection(u'users/' + uid + u'/child'), 100):
                        if fm.deleteCollection(fm.getCollection(u'users/' + uid + u'/Missing_long_post'), 100, True):
                            if fm.deleteCollection(fm.getCollection(u'users/' + uid + u'/Missing_post'), 100, True):
                                fm.deleteDocument(fm.getDocument(u'users/' + uid))
                                result_dict['result'] = True
                            else:
                                result_dict['result'] = False
                                result_dict['result'] = 'Error'
                        else:
                            result_dict['result'] = False
                            result_dict['result'] = 'Error'
                    else:
                        result_dict['result'] = False
                        result_dict['result'] = 'Error'
                else:
                    result_dict['result'] = False
                    result_dict['err_code'] = 'MISMATCH'
            else:
                result_dict['result'] = False
                result_dict['err_code'] = 'MISMATCH'
        else:
            result_dict['result'] = False
            result_dict['err_code'] = 'ERROR'
    else:
        result_dict['result'] = False
        result_dict['err_code'] = 'ERROR'

    return jsonify(result_dict)


@app.route('/member/login', methods=['POST'])
def login():
    result_dict = {}

    uid = request.args.get('id')
    pw = request.args.get('pw')

    if uid and pw:
        # 존재여부 체크
        idInfo = ie.getIDInfo(fm, uid)
        if idInfo is not None:
            # 아이디가 있다면
            if pw == idInfo['PW']:
                result_dict['result'] = True
            else:
                result_dict['result'] = False
                result_dict['err_code'] = 'MISMATCH'
        else:
            result_dict['result'] = False
            result_dict['err_code'] = 'MISMATCH'
    else:
        result_dict['result'] = False
        result_dict['err_code'] = 'EMPTY'

    # Firebase의 PW와 비교.
    # 기본적으로 안드로이드에서 보낼 때 암호화해서 보내면
    # Firebase에 있는 암호화된 값을 비교하는 방식으로
    # PW 점검. -> PW 변경 시에는 새로 암호화된 값을 저장하는 방식으로 암호화값은 복호화 불가한 방식으로 설정 필요.

    return jsonify(result_dict)


# 회원조회 / 회원수정
@app.route('/member/info', methods=['POST'])
@app.route('/member/edit', methods=['POST'])
def member_info():
    result_dict = {}
    # return
    uid = request.args.get('id')

    if uid:
        # 존재여부 체크
        idInfo = ie.getIDInfo(fm, uid)
        if idInfo is not None:
            profile_s3path = 'profiles/' + uid + '.jpg'
            profile_path = '.\\profiles\\' + uid + '.jpg'
            if '/member/info' in request.path:
                # 회원조회 -> id, pw -> 주소, 이름, 전번, 프로필 사진(None)
                pw = request.args.get('pw')
                if pw and pw == idInfo['PW']:
                    idInfo.update(ie.downloadImg(inst, uid, 'profiles', False))
                    # # s3에서 파일 존재 여부 확인
                    # if inst.getS3M().isExist(profile_s3path):
                    #     # s3에서 다운로드
                    #     inst.getS3M().download(profile_s3path, profile_path)
                    #     idInfo['photo'] = ie.loadB64(profile_path)
                    # else:
                    #     idInfo['photo'] = None

                    result_dict['result'] = True
                    result_dict['contents'] = {"addr": idInfo['address'], "name": idInfo['name'],
                                               "phone": idInfo['phone'], "photo": idInfo['photo']}
                else:
                    result_dict['result'] = False
                    result_dict['err_code'] = 'MISMATCH'
            elif '/member/edit' in request.path:
                # 회원수정 -> ID, (이후 값들은 선택적 요소) - 주소, PW, 이름, 전번, 사진 -> True/False + ErrorCode

                new_pw = request.args.get('new_pw')
                name = request.args.get('name')
                addr = request.args.get('addr')
                phone = request.args.get('phone')
                profile_photo = request.args.get('photo')

                query = {}
                if new_pw:  # PW 변경
                    query['PW'] = new_pw
                if name:  # 이름 변경
                    query['name'] = name
                if phone:  # 휴대폰번호 변경
                    query['phone'] = phone

                if addr:
                    query['address'] = addr
                fm.updateDocument(fm.getDocument(u'users/' + uid), query)

                if profile_photo:  # 프로필사진 변경 혹은 추가
                    ie.uploadImg(inst, uid, 'profiles', profile_photo, None, False)
                    # image_path = '.\\profiles\\' + uid + '.jpg'
                    # ie.saveB64(profile_photo, image_path)
                    #
                    # s3에 이미지 업로드
                    # inst.getS3M().upload(image_path, 'profiles/' + uid + '.jpg')
                result_dict['result'] = True
            else:
                result_dict['result'] = False
                result_dict['err_code'] = 'ERROR'

        else:
            result_dict['result'] = False
            result_dict['err_code'] = 'MISMATCH'
    else:
        result_dict['result'] = False

    return jsonify(result_dict)


@app.route('/my/posts', methods=['POST'])
@app.route('/my/comments', methods=['POST'])
@app.route('/my/children', methods=['POST'])
def mine():
    result_dict = {}
    uid = request.args.get('id')
    if uid:
        if ie.checkID(fm, uid):
            if '/my/posts' in request.path:
                # 본인 미아신고내역조회 -> ID -> 사진 이름 실종날짜
                missing_long_posts = fm.readCollection(fm.getCollection(u'users/' + uid + u'/Missing_long_post'))
                missing_short_posts = fm.readCollection(fm.getCollection(u'users/' + uid + u'/Missing_post'))
                # empty는 항상 제거
                del missing_short_posts['empty']
                del missing_long_posts['empty']

                # 단기, 장기 순
                result_dict['result'] = True
                result_dict['contents'] = []
                for key, missing in missing_short_posts.items():
                    mresult = {'type': '0', 'name': missing['name'], 'missing_date': missing['date']}

                    mresult.update(ie.downloadImg(inst, key, 'posts'))
                    mresult['picture'] = mresult.pop('photo1')
                    # short_post_s3path = 'posts/' + key + '_1.jpg'
                    # short_post_path = '.\\posts\\' + key + '_1.jpg'
                    # if inst.getS3M().isExist(short_post_s3path):
                    #     s3에서 다운로드
                    # inst.getS3M().download(short_post_s3path, short_post_path)
                    # mresult['picture'] = ie.loadB64(short_post_path)
                    # else:
                    #     mresult['picture'] = None

                    result_dict['contents'].append(mresult)
                for key, missing in missing_long_posts.items():
                    mresult = {'type': '1', 'name': missing['name'], 'missing_date': missing['date']}

                    if inst.getS3M().isExist('posts/' + key + '_1.jpg'):
                        mresult.update(ie.downloadImg(inst, key, 'posts'))
                        mresult['picture'] = mresult.pop('photo1')
                        # long_post_s3path = 'posts/' + key + '_1.jpg'
                        # long_post_path = '.\\posts\\' + key + '_1.jpg'
                        #
                        # inst.getS3M().download(long_post_s3path, long_post_path)
                        # mresult['picture'] = ie.loadB64(long_post_path)
                    elif inst.getS3M().isExist('posts/' + key + '_2.jpg'):
                        mresult.update(ie.downloadImg(inst, key, 'posts', True, True))
                        if mresult['photo1']:
                            mresult.pop('photo2')
                            mresult['picture'] = mresult.pop('photo1')
                        elif mresult['photo2']:
                            mresult.pop('photo1')
                            mresult['picture'] = mresult.pop('photo2')
                        else:
                            mresult['picture'] = None
                        # long_post_s3path = 'posts/' + key + '_2.jpg'
                        # long_post_path = '.\\posts\\' + key + '_2.jpg'
                        #
                        # inst.getS3M().download(long_post_s3path, long_post_path)
                        # mresult['picture'] = ie.loadB64(long_post_path)
                    else:
                        mresult['picture'] = None

                    result_dict['contents'].append(mresult)
            elif '/my/comments' in request.path:
                # 본인 제보내역조회 -> id -> type, 게시자ID, 아이이름, 내용, 게시날짜의 배열
                a = fm.collectionGroup(u'Report').where(u'id', u'==', uid)
                docs = a.stream()
                res = []

                for i in docs:
                    a = i.to_dict()
                    a['post_user_id'] = i._reference._path[1]
                    a['type'] = '0' if i._reference._path[2] == 'Missing_post' else '1'
                    a['comment'] = a.pop('contents')
                    a['written_date'] = a.pop('date')

                    postInfo = fm.getDocument(
                        u'users/' + a['post_user_id'] + u'/' + i._reference._path[2] + u'/' + i._reference._path[
                            3]).get().to_dict()
                    a['missing_name'] = postInfo['name']
                    res.append(a)
                    print(a)
                if len(res) > 0:
                    result_dict['result'] = True
                    result_dict['contents'] = res

            elif '/my/children' in request.path:
                # 본인 아이정보조회
                # id -> 이름들
                res = fm.readCollection(fm.getCollection(u'users/' + uid + u'/child'))
                # empty는 항상 제거
                del res['empty']

                result_dict['contents'] = []
                result_dict['result'] = True
                for k, v in res.items():
                    result_dict['contents'].append({'name': v['name']})
            else:
                result_dict['result'] = False
                result_dict['err_code'] = 'ERROR'
        else:
            result_dict['result'] = False
            result_dict['err_code'] = 'MISMATCH'
    else:
        result_dict['result'] = False
    return jsonify(result_dict)


@app.route('/child/register', methods=['POST'])
@app.route('/child/info', methods=['POST'])
@app.route('/child/edit', methods=['POST'])
@app.route('/child/delete', methods=['POST'])
def add_child():
    result_dict = {}
    uid = request.args.get('id')
    name = request.args.get('name')
    age = request.args.get('age')
    feature = request.args.get('feature')
    photo = request.args.get('photo')
    if uid and name:
        if ie.checkID(fm, uid):
            if '/child/register' in request.path:
                # 아이정보등록 -> ID, 이름, 나이, 특징, 사진 -> True/False
                if ie.checkChildName(fm, uid, name):
                    result_dict['result'] = False
                    result_dict['err_code'] = 'EXISTING_NAME'
                else:
                    if age and feature and photo:
                        res_time, doc_ref = fm.addDocument(fm.getCollection(u'users/' + uid + u'/child'), {
                            u'name': name,
                            u'age': age,
                            u'point': feature
                        })
                        ie.uploadImg(inst, doc_ref.id, 'children', photo)
                        # children_path = '.\\children\\' + doc_ref.id + '_1.jpg'
                        # children_s3path = '/children/' + doc_ref.id + '_1.jpg'
                        # ie.saveB64(photo, children_path)
                        # s3 업로드
                        # inst.getS3M().upload(children_path, children_s3path)

                        result_dict['result'] = True
                    else:
                        result_dict['result'] = False
                        result_dict['err_code'] = 'ERROR'
            elif '/child/info' in request.path:
                # 아이정보상세조회 -> ID, 이름 -> 나이, 이름, 사진, 특징
                key, childInfo = ie.checkChildName(fm, uid, name, True)
                if childInfo:
                    result_dict['result'] = True
                    # children_s3path = 'children/' + key + '_1.jpg'
                    # children_path = '.\\children\\' + key + '_1.jpg'
                    childInfo.update(ie.downloadImg(inst, key, 'children'))
                    # 임시용
                    childInfo['photo'] = childInfo.pop('photo1')

                    # if inst.getS3M().isExist(children_s3path):
                    #     # s3에서 다운로드
                    #     inst.getS3M().download(children_s3path, children_path)
                    #     childInfo['photo'] = ie.loadB64(children_path)
                    # else:
                    #     childInfo['photo'] = None

                    childInfo['feature'] = childInfo.pop('point')
                    result_dict['contents'] = childInfo
                else:
                    result_dict['result'] = False
                    result_dict['err_code'] = 'NONAME'
            elif '/child/edit' in request.path:
                # 아이정보수정
                # ID, 이름 (이후 파라메타는 선택)(이름 변경시, 바뀐 이름까지 같이.), 나이, 특징, 사진 -> True, False
                key, childInfo = ie.checkChildName(fm, uid, name, True)
                if key is None:
                    result_dict['result'] = False
                    result_dict['err_code'] = 'NONAME'
                else:
                    new_name = request.args.get('new_name')
                    query = {}

                    if new_name:  # 이름 변경
                        # 새로운 이름을 가진 아이가 있는지 중복체크
                        query['name'] = new_name
                    if age:  # 나이 변경
                        query['age'] = age
                    if feature:  # 특징 정보 수정
                        query['point'] = feature

                    if 'err_code' in result_dict.keys():
                        result_dict['result'] = False
                    else:
                        if len(query.keys()) is not 0:
                            fm.updateDocument(fm.getDocument(u'users/' + uid + u'/child/' + key), query)
                        if photo:  # 사진 수정 혹은 등록
                            ie.uploadImg(inst, key, 'children', photo)
                            # children_path = '.\\children\\' + key + '_1.jpg'
                            # children_s3path = '/children/' + key + '_1.jpg'
                            # ie.saveB64(photo, children_path)
                            # # s3 업로드
                            # inst.getS3M().upload(children_path, children_s3path)

                        result_dict['result'] = True
            elif '/child/delete' in request.path:
                # 아이정보삭제 -> id, name -> True/False
                key, childInfo = ie.checkChildName(fm, uid, name, True)
                if key is None:
                    result_dict['result'] = False
                    result_dict['err_code'] = 'NONAME'
                else:
                    fm.deleteDocument(fm.getDocument('users/' + uid + u'/child/' + key))
                    # %%% 여기에서 S3에 있는 사진도 삭제해야함. %%% #
                    result_dict['result'] = True
            else:
                result_dict['result'] = False
        else:
            result_dict['result'] = False
            result_dict['err_code'] = 'MISMATCH'
    else:
        result_dict['result'] = False
        result_dict['err_code'] = 'MISMATCH'
    return jsonify(result_dict)


@app.route('/post/write', methods=['POST'])
@app.route('/post/edit', methods=['POST'])
@app.route('/post/delete', methods=['POST'])
@app.route('/post/list', methods=['POST'])
@app.route('/post/info', methods=['POST'])
def post_page():
    result_dict = {}
    uid = request.args.get('id')
    name = request.args.get('name')
    # if request.path in ['/post/write', '/post/edit']:

    if '/post/info' in request.path:
        # 미아상세조회
        # 게시자ID, 아이이름
        # return 그에 대한 모든 정보 + 보호자번호(=게시자의 번호)
        pid = request.args.get('pid')
        if pid and name:
            key, missingInfo = ie.checkMissingName(fm, pid, name, True)
            temp = fm.getDocument(u'users', pid)
            t = temp.get().to_dict()
            phone = t['phone']
            group = fm.getDocument(u'users/' + pid + u'/Missing_' + (
                u'long_' if missingInfo['type'] is 1 else u'') + u'post/' + key)
            a = group.get().to_dict()
            res = []
            a['pid'] = group.get()._reference._path[1]
            a['missing_place'] = a.pop('place')
            a['missing_date'] = a.pop('date')
            a['feature'] = a.pop('point')
            a['phone'] = phone

            if missingInfo['type'] is 0:
                # 결과 딕셔너리 병합
                a.update(ie.downloadImg(inst, key, 'posts'))
                # a.update(ie.getPostImgAsB64(inst, key))
            elif missingInfo['type'] is 1:
                a.update(ie.downloadImg(inst, key, 'posts', True, True))
                # a.update(ie.getPostImgAsB64(inst, key, True))
            else:
                result_dict['result'] = False
                result_dict['err_code'] = 'ERROR'
            res.append(a)
            if len(res) > 0:
                result_dict['result'] = True
                result_dict['contents'] = res[0]
        elif pid is None:
            result_dict['result'] = False
            result_dict['err_code'] = 'NOPID'
        elif name is None:
            result_dict['result'] = False
            result_dict['err_code'] = 'NONAME'

    elif '/post/list' in request.path:
        # 미아리스트전체조회
        # Type 장/단 , 단기일 경우 도시이름, 장기일 경우 Type2 -> 0나 1 (0:찾고있어요, 1:찾아주세요)
        # return 단기일 경우, 게시자ID, 사진, 이름, 나이, 실종날짜, 실종장소 의 배열
        # return 장기일 경우, 게시자ID, 사진1, 사진2, 이름, 나이, 실종날짜, 실종장소 의 배열
        if request.args.get('type'):
            mtype = request.args.get('type')
            colGroupRef = fm.collectionGroup('Missing_long_post')
            group = colGroupRef.where("type2", "==", int(mtype))
            docs = group.stream()
            res = []
            for i in docs:
                a = i.to_dict()
                a['pid'] = i._reference._path[1]
                a['type'] = a.pop('type2')
                a['missing_place'] = a.pop('place')
                a['missing_date'] = a.pop('date')
                a.update(ie.downloadImg(inst, i._reference._path[3], 'posts', True, True))
                res.append(a)
            if len(res) > 0:
                result_dict['result'] = True
                result_dict['contents'] = res
            else:
                result_dict['result'] = True
                result_dict['contents'] = res
        elif request.args.get('city_name'):
            # result_dict['result'] = False
            # result_dict['err_code'] = 'ERROR'
            major = request.args.get('city_name')
            colGroupRef = fm.collectionGroup('Missing_post')
            group = colGroupRef.where("major", "==", major)
            docs = group.stream()
            res = []
            for i in docs:
                a = i.to_dict()
                a['pid'] = i._reference._path[1]
                a['missing_place'] = a.pop('place')
                a['missing_date'] = a.pop('date')
                a.update(ie.downloadImg(inst, i._reference._path[3], 'posts'))
                res.append(a)
            if len(res) > 0:
                result_dict['result'] = True
                result_dict['contents'] = res
            else:
                result_dict['result'] = True
                result_dict['contents'] = res

        else:
            result_dict['result'] = False
            result_dict['err_code'] = 'ERROR'

    else:
        if uid and ie.checkID(fm, uid):
            try:
                new_name = request.args.get('new_name')
                tmp = request.args.get('type')
                if tmp is not None:
                    type1 = int(tmp)
                age = request.args.get('age')
                # pre_age = request.args.get('pre_age') # 찾아주세요의 경우, 자신의 실종 당시 나이. 단기의 경우 실종 당시 나이?
                now_photo = request.args.get('photo2')
                pre_photo = request.args.get('photo1')
                missing_date = request.args.get('missing_date')
                missing_place = request.args.get('missing_place')
                feature = request.args.get('feature')

                if name:
                    if '/post/write' in request.path:
                        # 미아신고등록
                        # - 단기, 장기 여부 / ID, 나이, 현재모습사진, 옛날모습사진, 실종날짜, 이름, 장소, 특징
                        # return True/False
                        if ie.checkMissingName(fm, uid, name):
                            result_dict['result'] = False
                            result_dict['err_code'] = 'EXISTING_NAME'
                        elif age and missing_date and missing_place and feature:
                            major = missing_place.split()
                            city = major[1]
                            major = major[0]
                            if type1 is 0 and pre_photo:
                                # 단기미아
                                # postID = uid + str(
                                #     fm.readCollection(fm.getCollection(u'users/' + uid + u'/Missing_post'), True))
                                res_time, doc_ref = fm.addDocument(fm.getCollection(u'users/' + uid + u'/Missing_post'),
                                                                   {
                                                                       u'name': name,
                                                                       u'age': age,
                                                                       u'point': feature,
                                                                       u'place': missing_place,
                                                                       u'major': major,
                                                                       u'city': city,
                                                                       u'date': missing_date
                                                                   })
                                result_dict['result'] = True

                                # s3 업로드
                                faceIds = ie.uploadImg(inst, doc_ref.id, 'posts', pre_photo, None, True, True)
                                if len(faceIds) > 0:
                                    fm.updateDocument(fm.getDocument(u'users/' + uid + u'/Missing_post' + u'/' + doc_ref.id), {u'face':faceIds[0]})
                                if fm.addEmptyCollection(doc_ref,
                                                         [u'Report']) is False:
                                    result_dict['err_code'] = 'SUBCOLLECTION_FAIL'
                            elif type1 is 1:
                                type2 = int(request.args.get('type2'))
                                if type2 is 0 and pre_photo:
                                    # 찾고있어요
                                    # postID = uid + str(
                                    #     fm.readCollection(fm.getCollection(u'users/' + uid + u'/Missing_long_post'), True))
                                    res_time, doc_ref = fm.addDocument(
                                        fm.getCollection(u'users/' + uid + u'/Missing_long_post'),
                                        {
                                            u'name': name,
                                            u'age': age,
                                            u'point': feature,
                                            u'place': missing_place,
                                            u'date': missing_date,
                                            u'type2': type2
                                        })
                                    result_dict['result'] = True

                                    # s3 업로드
                                    faceIds = ie.uploadImg(inst, doc_ref.id, 'posts', pre_photo, None, True, True)
                                    if len(faceIds) > 0:
                                        fm.updateDocument(
                                            fm.getDocument(u'users/' + uid + u'/Missing_long_post' + u'/' + doc_ref.id),
                                            {u'face': faceIds[0]})

                                        # GAN 요청 리스트에 등록
                                        db.getTable().insert({
                                                u'id': uid,
                                                u'key': doc_ref._path[3],
                                                u'age': age,
                                                u'date': missing_date,
                                                u'type2': type2,
                                                u'grabbed': False  # True면 GAN이 가져갔다는 소리. 이 document가 삭제되면 처리완료 시그널
                                            })
                                        # res_time, ref = fm.addDocument(
                                        #     fm.getCollection(u'ganStack'),
                                        #     {
                                        #         u'id': uid,
                                        #         u'key': doc_ref._path[3],
                                        #         u'age': age,
                                        #         u'date': missing_date,
                                        #         u'type2': type2,
                                        #         u'grabbed': False  # True면 GAN이 가져갔다는 소리. 이 document가 삭제되면 처리완료 시그널
                                        #     })
                                    if fm.addEmptyCollection(doc_ref,
                                                             [u'Report']) is False:
                                        result_dict['err_code'] = 'SUBCOLLECTION_FAIL'

                                    a = doc_ref._path[3]


                                elif type2 is 1 and pre_photo:
                                    # 찾아주세요
                                    # postID = uid + str(
                                    #     fm.readCollection(fm.getCollection(u'users/' + uid + u'/Missing_long_post'), True))
                                    res_time, doc_ref = fm.addDocument(
                                        fm.getCollection(u'users/' + uid + u'/Missing_long_post'),
                                        {
                                            u'name': name,
                                            u'age': age,
                                            u'point': feature,
                                            u'place': missing_place,
                                            u'date': missing_date,
                                            u'type2': type2
                                        })
                                    result_dict['result'] = True

                                    # s3 업로드
                                    faceIds = ie.uploadImg(inst, doc_ref.id, 'posts', now_photo, pre_photo, True, True)
                                    if len(faceIds) > 0:
                                        fm.updateDocument(
                                            fm.getDocument(u'users/' + uid + u'/Missing_long_post' + u'/' + doc_ref.id),
                                            {u'face': faceIds[0]})

                                        # GAN 요청 리스트에 등록
                                        db.getTable().insert({
                                                u'id': uid,
                                                u'key': doc_ref._path[3],
                                                u'age': age,
                                                u'date': missing_date,
                                                u'type2': type2,
                                                u'grabbed': False  # True면 GAN이 가져갔다는 소리. 이 document가 삭제되면 처리완료 시그널
                                            })
                                        # res_time, ref = fm.addDocument(
                                        #     fm.getCollection(u'ganStack'),
                                        #     {
                                        #         u'id': uid,
                                        #         u'key': doc_ref._path[3],
                                        #         u'age': age,
                                        #         u'date': missing_date,
                                        #         u'type2': type2,
                                        #         u'grabbed': False  # True면 GAN이 가져갔다는 소리. 이 document가 삭제되면 처리완료 시그널
                                        #     })
                                    if fm.addEmptyCollection(doc_ref,
                                                             [u'Report']) is False:
                                        result_dict['err_code'] = 'SUBCOLLECTION_FAIL'


                                else:
                                    result_dict['result'] = False
                                    result_dict['err_code'] = 'ERROR1'
                            else:
                                result_dict['result'] = False
                                result_dict['err_code'] = 'ERROR2'
                        else:
                            result_dict['result'] = False
                            result_dict['err_code'] = 'ERROR3'

                    elif '/post/edit' in request.path:
                        # 미아신고수정
                        # ID, 아이이름, 정보들
                        # return True/False
                        key, missingInfo = ie.checkMissingName(fm, uid, name, True)
                        if key is None:
                            result_dict['result'] = False
                            result_dict['err_code'] = 'NONAME'
                        else:
                            query = {}
                            if new_name:  # 이름 변경
                                if ie.checkMissingName(fm, uid, new_name):
                                    result_dict['err_code'] = 'EXISTING_NEWNAME'
                                else:
                                    query['name'] = new_name
                            if age:  # 나이 변경
                                query['age'] = age
                            if feature:  # 특징 정보 수정
                                query['point'] = feature
                            # if now_photo:  # 현재 사진 수정 혹은 등록
                            #     query['cur_photo'] = now_photo
                            # if pre_photo:  # 과거 사진 수정 혹은 등록
                            #     if missingInfo['type'] is 1:
                            #         query['old_photo'] = pre_photo
                            #     else:
                            #         query['photo'] = pre_photo
                            if missing_date:  # 실종일자 수정 혹은 등록
                                query['date'] = missing_date
                            if missing_place:  # 실종장소 수정 혹은 등록
                                query['place'] = missing_place
                            query['modified_date'] = firestore.SERVER_TIMESTAMP

                            if 'err_code' in result_dict.keys():
                                result_dict['result'] = False
                            else:
                                fm.updateDocument(fm.getDocument(u'users/' + uid + u'/Missing_' + (
                                    u'long_' if missingInfo['type'] is 1 else u'') + u'post/' + key), query)

                                if pre_photo:
                                    # 기존 face 정보 얻어오기
                                    faces = inst.getRekoM().getFaces(100)

                                    targetFace = None
                                    for f in faces:
                                        if key in f['ExternalImageId']:
                                            targetFace = f['FaceId']

                                    targetFace = missingInfo['face']
                                    # face 정보 삭제
                                    inst.deleteFaces(targetFace, [])

                                    faceIds = ie.uploadImg(inst, key, 'posts', pre_photo, None, True, True)
                                    if len(faceIds) > 0:
                                        if missingInfo['type'] is 1:
                                            fm.updateDocument(
                                                fm.getDocument(u'users/' + uid + u'/Missing_long_post' + u'/' + key),
                                                {u'face': faceIds[0]})

                                            # GAN 요청 리스트에 등록
                                            db.getTable().insert({
                                                    u'id':uid,
                                                    u'key': key,
                                                    u'age': age if age else missingInfo['age'],
                                                    u'date': missing_date if missing_date else missingInfo['date'],
                                                    u'type2': 0,
                                                    u'grabbed': False  # True면 GAN이 가져갔다는 소리. 이 document가 삭제되면 처리완료 시그널
                                                }) # [FIX!]나중에 age와 date만 수정해도 gan 요청하도록 수정 필요!
                                            # res_time, ref = fm.addDocument(
                                            #     fm.getCollection(u'ganStack'),
                                            #     {
                                            #         u'id':uid,
                                            #         u'key': key,
                                            #         u'age': age,
                                            #         u'date': missing_date if missing_date else missingInfo['date'],
                                            #         u'type2': 0,
                                            #         u'grabbed': False  # True면 GAN이 가져갔다는 소리. 이 document가 삭제되면 처리완료 시그널
                                            #     })
                                        else:  # 단기
                                            fm.updateDocument(
                                                fm.getDocument(
                                                    u'users/' + uid + u'/Missing_post' + u'/' + key),
                                                {u'face': faceIds[0]})


                                if now_photo:
                                    faceIds = ie.uploadImg(inst, key, 'posts', None, now_photo, True, True)
                                    if len(faceIds) > 0:
                                        fm.updateDocument(
                                            fm.getDocument(
                                                u'users/' + uid + u'/Missing_long_post' + u'/' + key),
                                            {u'face': faceIds[0]})

                                        # GAN 요청 리스트에 등록
                                        db.getTable().insert({
                                                u'id': uid,
                                                u'key': key,
                                                u'age': age if age else missingInfo['age'],
                                                u'date': missing_date if missing_date else missingInfo['date'],
                                                u'type2': 1,
                                                u'grabbed': False  # True면 GAN이 가져갔다는 소리. 이 document가 삭제되면 처리완료 시그널
                                            })
                                        # res_time, ref = fm.addDocument(
                                        #     fm.getCollection(u'ganStack'),
                                        #     {
                                        #         u'id': uid,
                                        #         u'key': key,
                                        #         u'age': age,
                                        #         u'date': missing_date if missing_date else missingInfo['date'],
                                        #         u'type2': 1,
                                        #         u'grabbed': False  # True면 GAN이 가져갔다는 소리. 이 document가 삭제되면 처리완료 시그널
                                        #     })
                                result_dict['result'] = True
                    elif '/post/delete' in request.path:
                        # 미아신고삭제
                        # ID, 아이이름
                        # return True/False
                        key, missingInfo = ie.checkMissingName(fm, uid, name, True)
                        if key is None:
                            result_dict['result'] = False
                            result_dict['err_code'] = 'NONAME'
                        else:
                            fm.deleteCollection(fm.getCollection('users/' + uid + u'/Missing_' + (
                                u'long_' if missingInfo['type'] is 1 else u'') + u'post/' + key + u'/Report'))

                            fm.deleteDocument(fm.getDocument('users/' + uid + u'/Missing_' + (
                                u'long_' if missingInfo['type'] is 1 else u'') + u'post/' + key))

                            result_dict['result'] = True

                    else:
                        result_dict['result'] = False
                        result_dict['err_code'] = 'ERROR'
                else:
                    result_dict['result'] = False
                    result_dict['err_code'] = 'ERROR'
            except ValueError as ve:
                print('Value Error - Invalid Type')
                print('error -> ', ve)
                result_dict['result'] = False
                result_dict['err_code'] = 'INVALID_TYPE'
                return jsonify(result_dict)

            except Exception as ex:
                print('Error - ', ex)
                result_dict['result'] = False
                result_dict['err_code'] = 'ERROR_EXCEPTION'


        else:
            result_dict['result'] = False
            result_dict['err_code'] = 'NOID'
    return jsonify(result_dict)


@app.route('/comment/write', methods=['POST'])
@app.route('/comment/edit', methods=['POST'])
@app.route('/comment/delete', methods=['POST'])
@app.route('/comment/list', methods=['POST'])
def comment_page():
    result_dict = {}
    uid = request.args.get('id')
    pid = request.args.get('pid')
    cid = request.args.get('cid')
    name = request.args.get('name')
    contents = request.args.get('contents')
    date = request.args.get('date')
    tmp = request.args.get('type')
    if tmp is not None:
        type = int(tmp)

    if uid and pid and name:
        if '/comment/write' in request.path:
            # 미아제보등록
            # ID, 게시자ID, 아이이름, 제보내용, 제보날짜
            # True, False
            if contents and date:
                cc = u'users/' + pid + u'/Missing_' + (
                    u'long_' if type is 1 else u'') + u'post'
                post_path = fm.getCollection(u'users/' + pid + u'/Missing_' + (
                    u'long_' if type is 1 else u'') + u'post').where(u'name', u'==', name).stream()
                for d in post_path:
                    post = d.reference
                res_time, doc_ref = fm.addDocument(post.collection(u'Report'),
                                                   {
                                                       u'id': uid,
                                                       u'contents': contents,
                                                       u'date': date
                                                   })
                result_dict['result'] = True
            else:
                result_dict['result'] = False
        elif cid:
            if '/comment/edit' in request.path:
                # 미아제보수정
                # ID, 게시자ID, 제보식별자, 아이이름, 제보내용, 제보날짜
                # True, False
                key = ie.checkComment(fm, pid, cid, name, True)
                query = {}
                if key is False:
                    result_dict['result'] = False
                    result_dict['err_code'] = 'NOCONTENT'
                elif contents:  # 제보내용 변경
                    query['contents'] = contents
                    query['date'] = date
                    fm.updateDocument(fm.getDocument(key), query)
                    result_dict['result'] = True
            elif '/comment/delete' in request.path:
                # 미아제보삭제
                # ID, 게시자ID, 제보식별자, 아이이름
                key = ie.checkComment(fm, pid, cid, name, True)
                if key is False:
                    result_dict['result'] = False
                    result_dict['err_code'] = 'NOCONTENT'
                else:
                    fm.deleteDocument(fm.getDocument(key))
                    result_dict['result'] = True
            else:
                result_dict['result'] = False
                result_dict['err_code'] = 'ERROR'
        elif '/comment/list' in request.path:
            # 미아제보 전체조회
            # 게시자ID, 아이이름
            post_path = fm.getCollection(u'users/' + pid + u'/Missing_' + (
                u'long_' if type is 1 else u'') + u'post').where(u'name', u'==', name).stream()
            for d in post_path:
                post = d.reference
            group = post.collection(u'Report')
            docs = group.stream()
            res = []
            for i in docs:
                a = i.to_dict()
                if i.id == 'empty':
                    continue
                aRef = ie.getIDInfo(fm, a['id'], True)
                aInfo = aRef.to_dict()
                a['name'] = aInfo['name']
                a['cid'] = i._reference._path[5]
                a.update(ie.downloadImg(inst, a['id'], 'profiles', False))
                res.append(a)
            if len(res) > 0:
                result_dict['result'] = True
                result_dict['contents'] = res
            else:
                result_dict['result'] = True
                result_dict['contents'] = res
        else:
            result_dict['result'] = False
            result_dict['err_code'] = 'ERROR'
    else:
        result_dict['result'] = False
        result_dict['err_code'] = 'ERROR'
    return jsonify(result_dict)


@app.route('/search_face', methods=['POST'])
def search_face():
    # 미아사진비교1 (1대다)
    # 사진
    # return [사진, 이름, 일치도, 게시자ID] 배열
    if '/search_face' in request.path:
        result_dict = {}

        uid = request.args.get('uid')
        imgB64 = request.args.get('img')

        if uid and imgB64:
            if ie.checkID(fm, uid):
                img_64_decode = base64.urlsafe_b64decode(imgB64)
                img = 'compare\\' + uid + '_search_1.jpg'
                img_result = open(img, 'wb')
                img_result.write(img_64_decode)

                # usrImg, kidImg 이게 파라미터.
                # 결과는 result true, similarity : 90
                # err_code 는 미정
                if inst.checkConnected() is False:
                    inst.connect('ifind', 'IFCollection')
                result, value = inst.searchFaces([img])

                if result is False and value is None:
                    result_dict['result'] = False
                    result_dict['err_code'] = 'ERROR'
                else:
                    if len(value) is 0:
                        result_dict['result'] = True
                        result_dict['contents'] = []
                    else:
                        result_dict['result'] = True
                        result_dict['contents'] = []

                        #pid, name, photo, similarity, type

                        for i in value[0]:
                            a = {}
                            mInfo = ie.getMissingByFace(fm, i['Face']['FaceId'])
                            a['pid'] = mInfo.reference._path[1]
                            a.update(mInfo._data)
                            # 나머지 정보 주기
                            a['similarity'] = i['Similarity']
                            a.update(ie.downloadImg(inst, mInfo.reference._path[3], 'posts'))
                            a['photo'] = a.pop('photo1')
                            result_dict['contents'].append(a)
            else:
                result_dict['result'] = False
                result_dict['err_code'] = 'MISMATCH'
        return jsonify(result_dict)


@app.route('/compare_face', methods=['POST'])
def compare_face():
    # 미아사진비교2 (1대1)
    # 사진, 게시자ID, 아이이름
    # return 일치도
    if '/compare_face' in request.path:
        result_dict = {}
        pid = request.args.get('pid')

        # usrImg = '.\\source.jpg'
        # usrImg_result = open(usrImg, 'rb').read()
        # usrImgB64 = base64.urlsafe_b64encode(usrImg_result)
        # trgImg = '.\\target.jpg'
        # trgImg_result = open(trgImg, 'rb').read()
        # kidImgB64 = base64.urlsafe_b64encode(trgImg_result)

        usrImgB64 = request.args.get('usrImg')
        kidImgB64 = request.args.get('kidImg')

        if pid and usrImgB64 and kidImgB64:
            if ie.checkID(fm, pid):
                usrImg_64_decode = base64.urlsafe_b64decode(usrImgB64)
                usrImg = '.\\compare\\' + pid + '_1.jpg'
                usrImg_result = open(usrImg, 'wb')
                usrImg_result.write(usrImg_64_decode)

                kidImg_64_decode = base64.urlsafe_b64decode(kidImgB64)
                kidImg = '.\\compare\\' + pid + '_2.jpg'
                kidImg_result = open(kidImg, 'wb')
                kidImg_result.write(kidImg_64_decode)

                # usrImg, kidImg 이게 파라미터.
                # 결과는 result true, similarity : 90
                # err_code 는 미정
                if inst.checkConnected() is False:
                    inst.connect('ifind', 'IFCollection')
                res = inst.compareFaces(usrImg, kidImg)

                result_dict['result'] = True
                result_dict['contents'] = res

                return jsonify(result_dict)
        result_dict['result'] = False
        result_dict['err_code'] = 'ERROR'

    return jsonify(result_dict)


@app.route('/96ca1fca/admin.php')
@app.route('/')
@app.route('/phpinfo.php')
@app.route('/test.php')
@app.route('/index.php')
@app.route('/bbs.php')
@app.route('/forum.php')
@app.route('/forums.php')
@app.route('/bbs/index.php')
@app.route('/forum/index.php')
@app.route('/forums/index.php')
@app.route('/webdav/')
@app.route('/java.php')
@app.route('/_query.php')
@app.route('/db_cts.php')
@app.route('/db_pma.php')
@app.route('/logon.php')
@app.route('/license.php')
@app.route('/log.php')
@app.route('/hell.php')
@app.route('/x.php')
@app.route('/shell.php')
@app.route('/htdocs.php')
@app.route('/b.php')
@app.route('/sane.php')
@app.route('/lala.php')
@app.route('/lala-dpr.php')
@app.route('/wpc.php')
@app.route('/t6nv.php')
@app.route('/muhstik.php')
@app.route('/text.php')
@app.route('/wp-config.php')
@app.route('/muhstik2.php')
@app.route('/muhstiks.php')
@app.route('/muhstik-dpr.php')
@app.route('/lol.php')
@app.route('/uploader.php')
@app.route('/cmd.php')
@app.route('/cmv.php')
@app.route('/cmdd.php')
@app.route('/knal.php')
@app.route('/appserv.php')
@app.route('/scripts/setup.php')
@app.route('/phpMyAdmin/scripts/setup.php')
@app.route('/scripts/db___.init.php')
@app.route('/phpmyadmin/scripts/db___.init.php')
@app.route('/pma/scripts/setup.php')
@app.route('/myadmin/scripts/setup.php')
@app.route('/pma/scripts/db___.init.php')
@app.route('/myadmin/scripts/db___.init.php')
@app.route('/plugins/weathermap/editor.php')
@app.route('/cacti/plugins/weathermap/editor.php')
@app.route('/weathermap/editor.php')
@app.route('/elrekt.php')
@app.route('/App/?content=die(md5(HelloThinkPHP))')
@app.route('/index.php')
@app.route('/joomla/')
@app.route('/install/lib/ajaxHandlers/ajaxServerSettingsChk.php')
@app.route('/d7.php')
@app.route('/rxr.php')
@app.route('/1x.php')
@app.route('/home.php')
@app.route('/undx.php')
@app.route('/spider.php')
@app.route('/payload.php')
@app.route('/composers.php')
@app.route('/izom.php')
@app.route('/composer.php')
@app.route('/hue2.php')
@app.route('/lang.php')
@app.route('/new_license.php')
@app.route('/images/!.php')
@app.route('/images/vuln.php')
@app.route('/hd.php')
@app.route('/images/up.php')
@app.route('/images/attari.php')
@app.route('/images/jsspwneed.php')
@app.route('/images/stories/cmd.php')
@app.route('/images/stories/filemga.php')
@app.route('/up.php')
@app.route('/laravel.php')
@app.route('/huoshan.php')
@app.route('/yu.php')
@app.route('/floaw.php')
@app.route('/ftmabc.php')
@app.route('/mjx.php')
@app.route('/xiaoxia.php')
@app.route('/yuyang.php')
@app.route('/coonig.php')
@app.route('/ak.php')
@app.route('/baidoubi.php')
@app.route('/meijianxue.php')
@app.route('/no1.php')
@app.route('/python.php')
@app.route('/woshimengmei.php')
@app.route('/indea.php')
@app.route('/taisui.php')
@app.route('/xiaxia.php')
@app.route('/kk.php')
@app.route('/xsser.php')
@app.route('/zzz.php')
@app.route('/99.php')
@app.route('/hs.php')
@app.route('/1ts.php')
@app.route('/root.php')
@app.route('/5678.php')
@app.route('/root11.php')
@app.route('/xiu.php')
@app.route('/wuwu11.php')
@app.route('/xw.php')
@app.route('/xw1.php')
@app.route('/9678.php')
@app.route('/wc.php')
@app.route('/xx.php')
@app.route('/s.php')
@app.route('/w.php')
@app.route('/sheep.php')
@app.route('/qaq.php')
@app.route('/my.php')
@app.route('/qq.php')
@app.route('/aaa.php')
@app.route('/hhh.php')
@app.route('/jjj.php')
@app.route('/www.php')
@app.route('/411.php')
@app.route('/415.php')
@app.route('/421.php')
@app.route('/a411.php')
@app.route('/whoami.php')
@app.route('/whoami.php.php')
@app.route('/9.php')
@app.route('/98k.php')
@app.route('/981.php')
@app.route('/887.php')
@app.route('/888.php')
@app.route('/aa.php')
@app.route('/bb.php')
@app.route('/pp.php')
@app.route('/bbq.php')
@app.route('/jj1.php')
@app.route('/7o.php')
@app.route('/qwq.php')
@app.route('/nb.php')
@app.route('/hgx.php')
@app.route('/ppl.php')
@app.route('/tty.php')
@app.route('/aap.php')
@app.route('/app.php')
@app.route('/bbr.php')
@app.route('/ioi.php')
@app.route('/uuu.php')
@app.route('/yyy.php')
@app.route('/ack.php')
@app.route('/shh.php')
@app.route('/ddd.php')
@app.route('/nnn.php')
@app.route('/rrr.php')
@app.route('/bbqq.php')
@app.route('/tyrant.php')
@app.route('/qiqi1.php')
@app.route('/zhk.php')
@app.route('/bbv.php')
@app.route('/seeyon/htmlofficeservlet')
@app.route('/secure/ContactAdministrators!default.jspa')
@app.route('/weaver/bsh.servlet.BshServlet')
@app.route('/user/register')
@app.route('/user.php')
@app.route('/phpmyadmin/index.php')
@app.route('/pmd/index.php')
@app.route('/PMA/index.php')
@app.route('/PMA2/index.php')
@app.route('/pmamy/index.php')
@app.route('/pmamy2/index.php')
@app.route('/admin/index.php')
@app.route('/db/index.php')
@app.route('/dbadmin/index.php')
@app.route('/web/phpMyAdmin/index.php')
@app.route('/admin/pma/index.php')
@app.route('/admin/mysql/index.php')
@app.route('/admin/mysql2/index.php')
@app.route('/admin/phpmyadmin/index.php')
@app.route('/admin/phpmyadmin2/index.php')
@app.route('/mysqladmin/index.php')
@app.route('/mysql-admin/index.php')
@app.route('/mysql_admin/index.php')
@app.route('/phpadmin/index.php')
@app.route('/phpmyadmin0/index.php')
@app.route('/phpmyadmin1/index.php')
@app.route('/phpMyAdmin-4.4.0/index.php')
@app.route('/phpMyAdmin4.8.0/index.php')
@app.route('/phpMyAdmin4.8.1/index.php')
@app.route('/phpMyAdmin4.8.2/index.php')
@app.route('/phpMyAdmin4.8.3/index.php')
@app.route('/phpMyAdmin4.8.4/index.php')
@app.route('/phpMyAdmin4.8.5/index.php')
@app.route('/myadmin/index.php')
@app.route('/myadmin2/index.php')
@app.route('/xampp/phpmyadmin/index.php')
@app.route('/phpMyadmin_bak/index.php')
@app.route('/www/phpMyAdmin/index.php')
@app.route('/tools/phpMyAdmin/index.php')
@app.route('/phpmyadmin-old/index.php')
@app.route('/phpMyAdminold/index.php')
@app.route('/pma-old/index.php')
@app.route('/claroline/phpMyAdmin/index.php')
@app.route('/typo3/phpmyadmin/index.php')
@app.route('/phpmyadmin/phpmyadmin/index.php')
@app.route('/phpMyAbmin/index.php')
@app.route('/phpMyAdmin+++---/index.php')
@app.route('/v/index.php')
@app.route('/phpmyadm1n/index.php')
@app.route('/shaAdmin/index.php')
@app.route('/phpMyadmi/index.php')
@app.route('/phpMyAdmion/index.php')
@app.route('/s/index.php')
@app.route('/pwd/index.php')
@app.route('/phpMyAdmina/index.php')
@app.route('/phpMyAdmins/index.php')
@app.route('/phpMyAdmin._/index.php')
@app.route('/phpMyAdmin._2/index.php')
@app.route('/phpMyAdmin333/index.php')
@app.route('/phpmyadmin3333/index.php')
@app.route('/php2MyAdmin/index.php')
@app.route('/phpiMyAdmin/index.php')
@app.route('/phpNyAdmin/index.php')
@app.route('/1/index.php')
@app.route('/download/index.php')
@app.route('/phpMyAdmin_111/index.php')
@app.route('/phpmadmin/index.php')
@app.route('/321/index.php')
@app.route('/123131/index.php')
@app.route('/phpMyAdminn/index.php')
@app.route('/sbb/index.php')
@app.route('/phpMyAdmin_ai/index.php')
@app.route('/__phpMyAdmin/index.php')
@app.route('/program/index.php')
@app.route('/shopdb/index.php')
@app.route('/phppma/index.php')
@app.route('/phpmy/index.php')
@app.route('/mysql/admin/index.php')
@app.route('/mysql/dbadmin/index.php')
@app.route('/mysql/sqlmanager/index.php')
@app.route('/mysql/mysqlmanager/index.php')
@app.route('/wp-content/plugins/portable-phpmyadmin/wp-pma-mod/index.php')
@app.route('/sqladmin/index.php')
@app.route('/sql/index.php')
@app.route('/websql/index.php')
@app.route('/manager/html')
def fake():
    return '操你十八代祖宗'  # 중국에서 가장 심한 욕
