'''

이 모듈은 테스트용 메소드 모음 모듈입니다.

'''




from flask import Flask
app = Flask(__name__)

@app.route('/hello')
def hello_world():
    # make a collection , make a document
    # it also has updating function
    # start = time.time()
    # doc_ref = db.collection(u'users').document(u'u2')
    # doc_ref.set({
    #     u'first': u'Eva',
    #     u'last': u'Lovelace2',
    #     u'born': 1999
    # })
    # print('Create1 Time : ' + str(time.time() - start))
    # db.collection(u'users').document(u'u2').collection(u'children').add({})
    # db.collection(u'users').document(u'u2').collection(u'fpost').add({})
    # db.collection(u'users').document(u'u2').collection(u'lpost').add({})
    # print('Create2 Time : ' + str(time.time() - start))
    pass

# @app.route('/dump', methods=['GET'])
# def dump_data():
#     colName = request.args.get('colname')
#     dumpCount = request.args.get('dcount')
#     start = time.time()
#     fm.make_dump(db, colName, int(dumpCount))
#
#     return 'Dump Time : ' + str(time.time() - start)


@app.route('/read/<string:col_name>')
def read_data_page(col_name):
    start = time.time()
    users_ref = db.collection(col_name)
    docs = users_ref.stream()
    result_dict = {}
    for doc in docs:
        print(u'{} => {}'.format(doc.id, doc.to_dict()))
        result_dict[doc.id] = doc.to_dict()
    print('Read Time : ' + str(time.time() - start))
    return jsonify(result_dict)


@app.route('/delete/<string:col_name>')
def delete_data_page(col_name):
    start = time.time()
    users_ref = db.collection(col_name)
    fm.deleteCollection(users_ref, 100)
    return 'Delete Time : ' + str(time.time() - start)


@app.route('/join', methods=['GET'])
def join_user():
    start = time.time()
    userName = request.args.get('username')
    firstName = request.args.get('fname')
    lastName = request.args.get('lname')
    born = request.args.get('born')
    uCount = len(fm.readCollection(fm.getCollection(db, u'users')).keys())
    uID = u'user'+str(uCount)

    doc_ref = db.collection(u'users').document(userName)
    doc_ref.set({
        u'uid':uID,
        u'first': firstName,
        u'last': lastName,
        u'born': born
    })
    print('Create1 Time : ' + str(time.time() - start))
    db.collection(u'users').document(userName).collection(u'children').add({})
    db.collection(u'users').document(userName).collection(u'fpost').add({})
    db.collection(u'users').document(userName).collection(u'lpost').add({})
    print('Create2 Time : ' + str(time.time() - start))
    return '404 Error'



@app.route('/base64t')
def base64test():
    from service.aws_manager import AWSManager
    am = AWSManager.getInstance()
    am.connect("ifind", "IFCollection")
    result = am.getFacesAsBinary('leeminu.jpg')
    print(result)
    return 'C'


@app.route('/update_police')
def update_police():
    ie.call_police_api()
    return 'test'