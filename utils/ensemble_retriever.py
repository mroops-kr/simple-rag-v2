from sentence_transformers import SentenceTransformer
# from rank_bm25 import BM25Okapi
# from typing import Union, List
import numpy as np
import os
from sentence_transformers import util
from kiwipiepy import Kiwi

# 한글 형태소 토크나이저
kiwi = Kiwi()
def kiwi_tokenize(text):
    return [token.form for token in kiwi.tokenize(text)]

# 로컬 모델 - offline 사용 가능
local_dir = os.environ.get('local_model_dir')
model_path = f'{local_dir}/jhgan/ko-sbert-nli'
sentenceModel = SentenceTransformer(model_path)

class EnsembleRetriever:
    def __init__(self, bm25, model, embeddings, documents, metadatas):
        self.bm25 = bm25
        self.model = model
        self.embeddings = embeddings
        self.documents = documents
        self.metadatas = metadatas

    def retrieve(self, query, top_k=10):
        # BM25 검색
        tokenized_query = kiwi_tokenize(query)
        bm25_scores = self.bm25.get_scores(tokenized_query)

        # 임베딩 기반 검색
        query_embedding = self.model.encode(query, convert_to_tensor=True)
        cosine_scores = util.pytorch_cos_sim(query_embedding, self.embeddings)[0]

        # 점수 결합
        combined_scores = bm25_scores * 0.3 + cosine_scores.numpy() * 0.7

        # 상위 문서 추출
        top_indices = np.argsort(combined_scores)[::-1][:top_k]

        # 결과 만들기
        results = []
        for i in top_indices:
            result = self.metadatas[i]
            result['text'] = self.documents[i]
            results.append(result)

        # return [self.documents[i] for i in top_indices]
        return results