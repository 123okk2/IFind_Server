import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import firebase_manager as fm
import if_executor as ie


#
# def make_dump(db, colName, dumpCount):
#     colRef = getCollection(db, colName)
#
#     for i in range(dumpCount):
#         addDocument(colRef, {
#             u'first': u'Eva',
#             u'last': u'Lovelace2',
#             u'born': 1817
#         })
#     print("Dump Complete - Collection " + colName + " with " + str(dumpCount) + " times. ")

class FBManager:
    def __init__(self, db=None):
        if db:
            self.__db = db
            self.__isConnected = True
        else:
            self.__db = None
            self.__isConnected = False

    def connect(self, db):
        self.__db = db
        self.__isConnected = True

    def disconnect(self):
        self.__db = None
        self.__isConnected = False


    def addEmptyCollection(self, docRef, colList):
        if type(colList) is list:
            for i in colList:
                docRef.collection(i).add({}, u'empty')
            return True
        elif type(colList) is str:
            docRef.collection(colList).add({}, u'empty')
            return True
        else:
            return False

    def getCollection(self, path, colName=None):
        # path : collection의 위치. (collection 자체를 포함해도 되고 그렇지 않다면 반드시 colName으로 collection 이름을 넘겨줘야함.
        # 예시1 - getCollection('users/user1') : 불가능 ( return None )
        # 예시2 - getCollection('users/user1', 'child') : 가능
        # 예시3 - getCollection('users/user1/child') : 가능
        # 예시4 - getCollection('users') : 가능
        # 추후 예외처리 여부 확인필요
        args = path.split('/')
        if len(args) % 2 is 1:
            prev = self.__db.collection(path)
        elif colName and len(args) is not 0:
            prev = self.__db.collection(path+u'/'+colName)
        else:
            return None

        return prev

    def readCollection(self, colRef, isCountValue=False):
        # 이 함수에서는 collection을 가지고 와서 dict[dict]] 구조로 반환해줍니다.
        # 마치 2차원 배열과 비슷한 느낌으로 doc.id가 첫번째 dict의 key이며 그 key 값의 value는 doc.to_dict()입니다.
        docs = colRef.stream()
        resultDict = {}

        for doc in docs:
            resultDict[doc.id] = doc.to_dict()
            # print(u'{} => {}'.format(doc.id, doc.to_dict()))
        if isCountValue:
            return len(resultDict)
        return resultDict

    def deleteCollection(self, colRef, batch_size=None, isPost = False):  # Delete Collection
        if batch_size:
            docs = colRef.limit(batch_size).get()
            deleted = 0

            for doc in docs:
                # print(u'Deleting doc {} => {}'.format(doc.id, doc.to_dict()))
                if isPost:
                    self.deleteCollection(doc.reference.collection(u'Report'), 1000)
                doc.reference.delete()
                deleted = deleted + 1

            if deleted >= batch_size:
                return self.deleteCollection(self, colRef, batch_size)
            return True
        else:
            return False

    def getDocument(self, path, docName=None):
        # path : document의 위치. (document 자체를 포함해도 되고 그렇지 않다면 반드시 docName으로 document 이름을 넘겨줘야함.
        # 예시1 - getDocument('users/user1') : 가능
        # 예시2 - getDocument('users', 'user1') : 가능
        # 예시3 - getDocument('users') : 불가능 ( return None )
        # 추후 예외처리 여부 확인필요
        args = path.split('/')
        if len(args) % 2 is 0 and len(args) is not 0:
            prev = self.__db.document(path)
        elif docName:
            prev = self.__db.document(path+u'/'+docName)
        else:
            return None

        return prev

    def getDocumentDirectly(self, colName, docName):
        # 추후 예외처리 여부 확인필요
        docRef = self.__db.collection(colName).document(docName)
        return docRef

    def addDocument(self, colRef, query, docName=None):
        # 추후 예외처리 여부 확인필요
        # add : id는 자동으로 부여받고 싶으면 사용
        return colRef.add(query, docName)

    def setDocument(self, docRef, query, merged):
        # set : 전체를 변경할 경우 사용
        # merged : 기존 데이터와의 합병 여부
        # 추후 예외처리 여부 확인필요
        if merged:
            self.__db.collection(docRef).set(query, merge=True)
        else:
            self.__db.collection(docRef).set(query)

    def updateDocument(self, docRef, query):
        # update : 일부만 변경할 경우 사용
        # 추후 예외처리 여부 확인필요
        docRef.update(query)

    def deleteDocument(self, docRef):
        # 예외처리가 필요하다면 사용하고 필요없다면 이 메소드는 존재무의미
        docRef.delete()

    def readDocument(self, docRef):
        # 예외처리가 필요하다면 사용하고 필요없다면 이 메소드는 존재무의미
        return self.__db.collection(docRef).get()

    '''
    < 사용법 >
    museums = db.collection_group(u'landmarks')\
    .where(u'type', u'==', u'museum')
    docs = museums.stream()
    for doc in docs:
        print(u'{} => {}'.format(doc.id, doc.to_dict()))
    '''
    def collectionGroup(self, colName):
        # 동일한 이름의 모든 컬렉션에 대한 질의
        group = self.__db.collection_group(colName)
        return group

