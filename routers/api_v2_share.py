'''
pip install python-multipart

'''
from fastapi import APIRouter, File, UploadFile, Form
from typing import List
from routers.api_v2_common import cm_upload, cm_reEmbedding, cm_checkFinish, cm_search, cm_summary, cm_delete, cm_download

from enum import Enum
class YnEnum(str, Enum):
    Y = "Y"
    N = "N"

router = APIRouter()
# 공용 파일
prefix = '/api/v2/share'

@router.post('/upload', description="""
[공유파일] 파일업로드 > 청크화 > 임베딩

- asyncYn : async 여부 > Y 일 경우 - ./checkFinish 로 완료여부 확인
- files: 업로드 파일들

""")
def upload(
    asyncYn: YnEnum = Form(YnEnum.N),
    files: List[UploadFile] = File(...)
):
    return cm_upload(None, asyncYn, files)

@router.post('/reEmbedding', description="""
[공유파일] 업로드된 파일을 다시 임베딩함

- asyncYn : async 여부 > Y 일 경우 - ./checkFinish 로 완료여부 확인
- fileIds: 업로드 파일의 id 들

""")
def reEmbedding(
    asyncYn: YnEnum = Form(YnEnum.N),
    fileIds: List[str] = Form(...)
):
    return cm_reEmbedding(None, asyncYn, fileIds)

@router.post('/checkFinish', description="""
[공유파일] asyncYn: Y 로 호출된 경우, 해당 파일의 완료여부 검사. 2분간 없으면 리턴함, 리턴값 확인 후 재호출 필요

- fileIds : 업로드 파일의 id 들
- finishAnyYn: 끝난 파일이 하나라도 있으면 리턴함

""")
def checkFinish(
    fileIds: List[str] = Form(...),
    finishAnyYn: YnEnum = Form(YnEnum.N),
):
    return cm_checkFinish(None, fileIds, finishAnyYn)

@router.post('/search', description="""
[공유파일] 임베딩된 백터DB에서 question(질문)과 유사도 검사후 결과 리턴함

- question: 질문
- n_results : 리턴할 갯수
- fileIds : 업로드 파일의 id 들

""")
def search(
    question: str = Form(...),
    n_results: int = Form(5),
    fileIds: List[str] = Form(None),
):
    return cm_search(None, question, n_results, fileIds)

@router.post('/summary', description="""
[공유파일] 해당 파일의 요약을 리턴

- fileIds : 업로드 파일의 id 들

""")
def summary(
    fileIds: List[str] = Form(None),
):
    return cm_summary(None, fileIds)

@router.post('/delete', description="""
[공유파일] 임베딩된 데이터 및 파일 삭제

- fileIds : 업로드 파일의 id 들

""")
def delete(
    fileIds: List[str] = Form(None),
):
    return cm_delete(None, fileIds)

@router.get('/download', description="""
[공유파일] 임베딩된 파일 다운로드

- fileId : 업로드 파일의 id

""")
def download(
    fileId: str = Form(None),
):
    return cm_download(None, fileId)


