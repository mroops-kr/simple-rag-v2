'''

'''
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import HuggingFaceEmbeddings
from typing import List
# import chromadb
import os

from langchain.chat_models import ChatOpenAI
from langchain_openai import AzureChatOpenAI
from langchain import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from utils.mysql_util import MysqlClient
from utils.file_util import loadFile
from datetime import datetime

import math
import json
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer
from utils.ensemble_retriever import kiwi_tokenize, sentenceModel, EnsembleRetriever

# 임베딩 진행
def process_embedding(userId: str, metas: List[dict]):

    # 파일 테이블
    file_table = 'rg_share2_file'
    if userId is not None:
        file_table = 'rg_user2_file'

    # 파일 내용 테이블
    file_text_table = 'rg_share2_file_cont'
    if userId is not None:
        file_text_table = 'rg_user2_file_cont'

    # 요약을 진행 할 지 여부
    rag_process_summary = os.environ.get('rag_process_summary')

    with MysqlClient() as client:
        
        for meta in metas:
            
            char_size = 0
            summary_size = 0
            summary_chunk_count = 0

            fileId   = meta['fileId']
            fileName = meta['fileName']

            # 문서 로드
            docs = loadFile(meta['filePath'])

            # char_size (총 글자수)
            for doc in docs:
                char_len = len(doc['text'])
                char_size += char_len
                doc['userId']   = userId
                doc['fileId']   = fileId
                doc['fileName'] = fileName

            # 요약용 청크
            summary_chunks = []
            
            # 청크화
            chunks = make_chunks(userId, docs, summary_chunks, chunk_size=800, chunk_overlap=80)
            char_chunk_count = len(chunks)

            # 요약 진행
            if rag_process_summary == 'Y':
                
                process_summarize(userId, meta, chunks, summary_chunks)
                summary_chunk_count = len(chunks)
                for chunk in chunks:
                    if chunk['level'] == 2:
                        summary_size += len(chunk['text'])

            # 임베딩 후 저장
            save_v2_embeddings(userId, chunks, meta)

            # 파일 정보 update
            client.auto.update(file_table, {
                'userId': userId,
                'fileId': fileId,
                'char_size': char_size,
                'char_chunk_count': char_chunk_count,
                'summary_size': summary_size,
                'summary_chunk_count': summary_chunk_count,
            })
            
            # 재인덱싱 - 기존 파일 내용 삭제
            if 'reindex' in meta and meta['reindex'] == 'Y':
                client.auto.delete(file_text_table, {'fileId': fileId,})

            now = datetime.now()

            # 페이지 데이터 insert
            for doc in docs:
                client.auto.insert(file_text_table, {
                    'userId': userId,
                    'fileId': fileId,
                    'level': 1,
                    'page': doc['page'],
                    'p_page': doc['summary_idx'],
                    'file_name': fileName,
                    'created_at': now,
                    'char_size': len(doc['text']),
                    'text': doc['text'],
                })
            client.commit()

            # summary 데이터 insert
            for chunk in chunks:
                if chunk['level'] == 2:
                    client.auto.insert(file_text_table, {
                        'userId': userId,
                        'fileId': fileId,
                        'level': 2,
                        'page': chunk['page'],
                        'file_name': fileName,
                        'sourcePages': chunk['sourcePages'],
                        'created_at': now,
                        'char_size': len(chunk['text']),
                        'text': chunk['text'],
                    })
            client.commit()
            

# 청크화
def make_chunks(userId: str, docs: List[dict], summary_chunks: List[str], chunk_size: int=800, chunk_overlap: int=80):

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunked_docs = []

    rag_chunk_max = int(os.environ.get('rag_chunk_max'))

    # 문서 요약용
    summary_idx = 1
    summary_len = 0
    summary_texts = []
    source_pages = []

    for idx, doc in enumerate(docs):
        page = doc['page']
        text = doc['text']
        fileId   = doc['fileId']
        fileName = doc['fileName']

        text_len = len(text)
        if summary_len + text_len > rag_chunk_max:
            # 요약용 데이터 만들기 - 페이지의 텍스트를 합쳐서 만듬
            summary_chunk = {
                'sourcePages': ', '.join(source_pages),
                'text':         '\n'.join(summary_texts)
            }
            if userId is not None:
                summary_chunk['userId'] = userId
            summary_chunks.append(summary_chunk)

            summary_texts = []
            source_pages  = []
            summary_len = 0
            summary_idx += 1

        summary_texts.append(text)
        source_pages.append(str(idx+1))
        summary_len += text_len

        text_chunks = text_splitter.split_text(text)
        for chunk in text_chunks:
            # 청크 데이터
            chunked_doc = {
                'text': chunk,
                'page': page,
                'level': 1,
                'fileId': fileId,
                'fileName': fileName,
                'summary_idx': summary_idx,
                'sourcePages': '',
            }
            if userId is not None:
                chunked_doc['userId'] = userId

            chunked_docs.append(chunked_doc)
            doc['summary_idx'] = summary_idx
    

    # 요약용 데이터 만들기 - 페이지의 텍스트를 합쳐서 만듬
    summary_chunk = {
        'sourcePages': ', '.join(source_pages),
        'text':         '\n'.join(summary_texts)
    }
    if userId is not None:
        summary_chunk['userId'] = userId
    summary_chunks.append(summary_chunk)

    return chunked_docs

# 임베딩 후 데이터 저장
def save_v2_embeddings(userId: str, chunks: List[dict], meta: dict):

    documents  = []
    metadatas  = []
    file_meta = { 'userId': userId, 'fileId': meta['fileId'], 'fileName': meta['fileName'] }

    for chunk in chunks:

        documents.append(chunk['text'])
        metadatas.append({
            'level': chunk['level'],
            'page':  chunk['page'],
            'sourcePages': chunk['sourcePages'],
        })

    # 임베딩
    embeddings = sentenceModel.encode(documents, convert_to_tensor=False)

    # 토크나이즈
    tokenizeds = [kiwi_tokenize(doc) for doc in documents]
    
    # 데이터를 파일에 저장
    filePath = meta['filePath']

    np.savez(f'{filePath}.npz',
        documents  = documents,
        metadatas  = metadatas,
        embeddings = embeddings,
        tokenizeds = { 'json': json.dumps(tokenizeds) },
        file_meta=file_meta)
    
# 컬랙션 검색
def search_v2_embeddings(userId: str, questions: List[str], filePaths: List[str], n_results: int=5):

    documents  = []
    metadatas  = []
    embeddings = []
    tokenizeds = []
    # file_meta  = []
    for filePath in filePaths:
        # 저장된 데이터 로드
        data = np.load(f'{filePath}.npz', allow_pickle=True)

        docs   = data['documents'].tolist()
        metas  = data['metadatas'].tolist()
        embds  = data['embeddings'].tolist()
        toks   = data['tokenizeds'].item()
        file_meta = data['file_meta'].item()

        toks = json.loads(toks['json'])

        fileId   = file_meta['fileId']
        fileName = file_meta['fileName']
        # 메타에 파일 정보 더함
        for meta in metas:
            meta['fileId']   = fileId
            meta['fileName'] = fileName
        
        for i in range(len(docs)):
            documents.append(docs[i])
            metadatas.append(metas[i])
            embeddings.append(embds[i])
            tokenizeds.append(toks[i])

    # BM25 모델
    bm25 = BM25Okapi(tokenizeds)

    # EnsembleRetriever 생성
    retriever = EnsembleRetriever(bm25, sentenceModel, embeddings, documents, metadatas)

    # 쿼리 수행
    results = []
    top_k = math.ceil(n_results / len(questions))
    # Multi-Query-Retriever 의 경우 대비
    for question in questions:
        # 쿼리 수행
        retrieved = retriever.retrieve(question, top_k=top_k)
        for item in retrieved:
            if n_results > len(results):
                results.append(item)

    return results

# 요약 진행
def process_summarize(userId: str, meta: List[dict], chunks: List[dict], summary_chunks: List[dict]):

    # 프롬프트
    prompt=PromptTemplate(
        input_variables=['content', 'language'],
        template="""
        Please summarize the content below in about 800 characters, no more than 1200 characters, without omitting important words.
        Please provide a summary in {language}.

        content: {content}
        """
    )

    # LLM (Large Language Model)
    model = None
    openai_api_key = os.environ.get('OPENAI_API_KEY')
    if openai_api_key is not None and openai_api_key != '':
        model = ChatOpenAI(temperature=0,)
    else:
        model = AzureChatOpenAI(
            temperature=0,
            deployment_name='gpt-35-turbo-16k',     # 변경 필요
            api_version='2023-08-01-preview',       # 변경 필요
        )
    
    # OutputParser
    output_parser = StrOutputParser()

    chain = prompt | model | output_parser

    for i, summary_chunk in enumerate(summary_chunks):
        
        # chain 호출로 LLM을 통한 요약 실행
        input = {"content": summary_chunk['text'], 'language': 'Korean'}
        result = chain.invoke(input)

        print('summarize')
        print(result)

        # 요약 정보 청크목록에 더함 - 같이 embedding 진행을 위한 것
        newChunk = {
            'text': result,
            'page': i+1,
            'level': 2,
            'fileId': meta['fileId'],
            'fileName': meta['fileName'],
            'sourcePages': summary_chunk['sourcePages'],
            'char_size': len(result)
        }
        if userId is not None:
            newChunk['userId'] = userId
        chunks.append(newChunk)


