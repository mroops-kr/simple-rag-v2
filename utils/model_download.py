
from sentence_transformers import SentenceTransformer
import os

# 모델 다운로드 및 로컬 저장 경로 설정
model = SentenceTransformer('jhgan/ko-sbert-nli')

# 경로 만들기
local_dir = os.environ.get('local_model_dir')
model_path = f'{local_dir}/jhgan/ko-sbert-nli'
os.makedirs(model_path, exist_ok=True)

# 저장
model.save(model_path)

#
#       실행
#       python utils/model_download.py