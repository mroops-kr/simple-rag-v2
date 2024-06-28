'''
pip install python-multipart

'''
from fastapi import APIRouter, UploadFile
from fastapi.responses import FileResponse
from typing import List
from datetime import datetime
from utils.mysql_util import MysqlClient
from threading import Thread
from utils.cm_util import random_text
from utils.rag_v2_common import process_embedding, search_v2_embeddings
import shutil
import os
import time

from enum import Enum
class YnEnum(str, Enum):
    Y = "Y"
    N = "N"

router = APIRouter()
prefix = '/api/v2/commom'

# 파일 업로드 >> 청크화 >> 임베딩
def cm_upload(
    userId: str = None,
    asyncYn: YnEnum = None,
    files: List[UploadFile] = None
):
    
    # 현재 날짜로 폴더 경로 생성
    now = datetime.now()
    year = now.strftime("%Y")
    month = now.strftime("%m")
    
    # 파일 저장 경로 설정
    upload_dir = os.environ.get('upload_dir')

    if userId is not None:
        # 사용자 파일 경로
        upload_dir = os.path.join(upload_dir, f'users/{userId}')
    else:
        # 공용 파일 경로
        upload_dir = os.path.join(upload_dir, 'share')
    
    # 년 + 월 파일 경로
    year_path = os.path.join(upload_dir, year)
    month_path = os.path.join(year_path, month)

    # 디렉토리가 존재하지 않으면 생성
    os.makedirs(month_path, exist_ok=True)
    month_path = month_path.replace('\\','/')

    fileIds = []
    file_metas = []
    for file in files:
        file_id     = random_text(16)
        file_name   = file.filename

        # 마지막 '.'의 인덱스를 찾기 - 확장자 추출용
        dot_index = file_name.rfind('.')
        file_ext  = file_name[dot_index + 1:].lower()
        file_path = f"{month_path}/{file_id}.{file_ext}"

        print(f'file_path: {file_path}')

        # 파일을 저장할 경로
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 파일 메타 정보
        file_metas.append({
            'userId': userId,
            'fileId': file_id,
            'filePath': file_path,
            'fileName': file_name,
            'fileExt': file_ext,
            'createdAt': now
        })

        # 리턴값
        fileIds.append({ 'fileId': file_id })
    
    file_table = 'rg_share2_file'
    if userId is not None:
        file_table = 'rg_user2_file'

    # 테이블에 저장
    with MysqlClient() as client:
        for file_meta in file_metas:
            # print(file_meta)
            client.auto.insert(file_table, file_meta)
        client.commit()

    # async 방식의 경우
    if asyncYn == 'Y':
        Thread(target=process_embedding, args=(userId, file_metas,)).start()
    else:
        process_embedding(userId, file_metas)

    return fileIds

# 재 임베딩 진행
def cm_reEmbedding(
    userId: str = None,
    asyncYn: YnEnum = None,
    fileIds: List[str] = None
):
    # 리턴용 파일 ID 목록
    fileIds = []
    # 파일 정보
    file_metas = []

    # 파일 테이블
    file_table = 'rg_share2_file'
    if userId is not None:
        file_table = 'rg_user2_file'

    with MysqlClient() as client:

        # 파일 테이블 변경
        client.auto.update(file_table, {
            'userId': userId,
            'fileId': fileIds,
            'char_size': 0,
            'char_chunk_count': 0,
            'summary_size': 0,
            'summary_chunk_count': 0,
        })
        client.commit()

        # 파일 테이블 조회
        list = client.auto.selectList(file_table, {
            'userId': userId,
            'fileId': fileIds
        })
        for item in list:
            file_metas.append({
                'userId': userId,
                'reindex':  'Y',
                'fileId': item['fileId'],
                'filePath': item['filePath'],
                'fileName': item['fileName'],
            })
            # 리턴값
            fileIds.append({ 'fileId': item['fileId'] })
    
    # async 방식의 경우
    if asyncYn == 'Y':
        Thread(target=process_embedding, args=(userId, file_metas,)).start()
    else:
        process_embedding(userId, file_metas)
    
    return fileIds

# 파일 임베딩이 완료 되었는지 검사
def cm_checkFinish(
    userId: str = None,
    fileIds: List[str] = None,
    finishAnyYn: YnEnum = None,
):
    
    # 완료 목록
    finished = []
    # 비완료 목록
    not_finished = []

    # 파일 테이블
    file_table = 'rg_share2_file'
    if userId is not None:
        file_table = 'rg_user2_file'

    # 2분간 완료 여부 검사 후 리턴함
    for i in range(24):

        with MysqlClient() as client:
            
            # 파일 테이블 조회
            list = client.auto.selectList(file_table, {
                'userId': userId,
                'fileId': fileIds
            })

            finished = []
            not_finished = []

            # 루프 돌면서 완료된것, 안된것 목록에 모음
            for item in list:
                print(item)
                if item['charChunkCount'] is None or item['charChunkCount'] == 0:
                    not_finished.append(item['fileId'])
                else:
                    finished.append(item['fileId'])
            
            # finishAnyYn: Y 이고, 끝난 것이 있으면
            if finishAnyYn == YnEnum.Y and len(finished) > 0:
                return {
                    'finished': finished,
                    'not_finished': not_finished,
                }
            
            # 모두 완료 되었으면
            if len(not_finished) == 0:
                break

            time.sleep(5)  # 5초 동안 대기
    
    return {
        'finished': finished,
        'not_finished': not_finished,
    }


# @app.get("/search")
# async def search(
#     question: str,
#     n_results: int = 5,
#     fileIds: Optional[List[str]] = Query(None),
#     option: Optional[str] = None,
# ):

# 임베딩 검색
def cm_search(
    userId: str = None,
    question: str = None,
    n_results: int = None,
    fileIds: List[str] = None,
):

    file_table = 'rg_share2_file'
    if userId is not None:
        file_table = 'rg_user2_file'

    with MysqlClient() as client:
        list = client.auto.selectList(file_table, {
            'userId': userId,
            'fileId': fileIds,
        })

        filePaths = []
        for item in list:
            filePaths.append(item['filePath'])

        if len(filePaths) == 0:
            return []
        
        results = search_v2_embeddings(userId, [question], filePaths = filePaths, n_results = n_results)

        return results

# 요약 조회
def cm_summary(
    userId: str = None,
    fileIds: List[str] = None,
):
    # 파일 내용 테이블
    file_text_table = 'rg_share2_file_cont'
    order_by = 'file_id, level, page'
    if userId is not None:
        file_text_table = 'rg_user2_file_cont'
        order_by = 'user_id, file_id, level, page'
    
    with MysqlClient() as client:
        # 파일 내용 목록 조회
        list = client.auto.selectList(file_text_table, {
            'userId': userId,
            'file_id': fileIds,
            'level': 2,
            'order_by': order_by
        })

        returnList = []
        for item in list:
            returnList.append({
                'fileId':     item['fileId'],
                'fileName':   item['fileName'],
                'page':       item['page'],
                'sourcePages': item['sourcePages'],
                'text':       item['text'],
            })
        return returnList

# 임베딩, 파일 삭제
def cm_delete(
    userId: str = None,
    fileIds: List[str] = None,
):

    # 파일 테이블
    file_table = 'rg_share2_file'
    if userId is not None:
        file_table = 'rg_user2_file'

    # 파일 내용 테이블
    file_text_table = 'rg_share2_file_cont'
    if userId is not None:
        file_text_table = 'rg_user2_file_cont'
    
    deletedIds = []
    with MysqlClient() as client:
        # 파일 테이블 조회
        list = client.auto.selectList(file_table, {
            'userId': userId,
            'fileId': fileIds
        })
        for item in list:

            # 파일 내용 테이블 - 데이터 삭제
            client.auto.delete(file_text_table, {
                'userId': userId,
                'fileId': item['fileId']
            })

            # 파일 테이블 - 데이터 삭제
            client.auto.delete(file_table, {
                'userId': userId,
                'fileId': item['fileId']
            })

            # 물리 파일 삭제
            filePath = item['filePath']
            if os.path.exists(filePath):
                os.remove(filePath)
            if os.path.exists(f'{filePath}.npz'):
                os.remove(f'{filePath}.npz')

            # 삭제목록 - 리턴 목록
            deletedIds.append(item['fileId'])

            client.commit()

    return deletedIds

# 임베딩된 파일 다운로드
def cm_download(
    userId: str = None,
    fileId: str = None,
):
    # 파일 테이블
    file_table = 'rg_share2_file'
    if userId is not None:
        file_table = 'rg_user2_file'
        
    with MysqlClient() as client:
        # 파일 테이블 조회
        item = client.auto.selectOne(file_table, {
            'userId': userId,
            'fileId': fileId
        })

        # 데이터 있으면
        if item is not None:
            # 물리적 파일 있으면
            if os.path.exists(item['filePath']):
                return FileResponse(item['filePath'], media_type='application/octet-stream', filename=item['fileName'])
            else:
                return {"error": "File not found"}
    
    return {"error": "Data not found"}

