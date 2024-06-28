# simple-rag

## English

### Overview
* A simple RAG is built using Python.
* The final answer is obtained through file categorization and communication with LLM in a Java-based WAS.
* The purpose of this system is to extract and provide text based on similarity inspection from the uploaded file contents.

### Configuration
* Implemented using MySQL - connection settings need to be changed (.env file).
* Required tables are in the tables_v1.sql file, so they need to be executed to be created.
* The embedding model used is 'jhgan/ko-sbert-nli' from HuggingFaceEmbeddings - a model that supports Korean well.
* Chroma is used for the Vector DB.
* Document summarization is performed simultaneously with file upload; if summarization is not desired, set rag_process_summary='N' in the .env file.
* For summarization, the OPENAI_API_KEY needs to be set in the .env file.

``` C
/api/v2/share/~~ : Shared file API
/api/v2/user/~~ : Personal file API
```

### Changes
* To improve the accuracy of text extraction, we now use a combination of 'jhgan/ko-sbert-nli' and BM25 (EnsembleRetriever).
* While using EnsembleRetriever, instead of using a Vector DB, we save the already embedded values to a file (using numpy).

### Previous version
* https://github.com/mroops-kr/simple-rag

### Author
* Author: mroops@naver.com

------------
## Korean

### 개요
* Python 으로 만든 간단한 RAG 시스템.
* Java기반 WAS에서 파일에 대한 카테고리 구성 및 LLM과의 통신을 통해 최종 답을 받아옴.
* 본 시스템은 업로드한 파일 내용 중 유사도 검사에 의한 텍스트를 추출하여 제공하는 것을 목적으로 함.

### 설정
* MySql 을 사용함 - 연결 설정 정보 변경 필요 (.env 파일)
* 필요 테이블은 tables_v1.sql 파일에 있으며 실행하여 만들어야 함
* 임베딩 모델은 HuggingFaceEmbeddings의 'jhgan/ko-sbert-nli' 사용 - 한글 지원이 잘되는 모델
* Vector DB 는 크로마 사용
* 파일 업로드와 동시에 문서 요약 진행함, 요약 진행을 원하지 않으면 rag_process_summary='N' 로 설정 필요 (.env 파일)
* 요약 진행시 OPENAI_API_KEY 설정 필요 (.env 파일)

``` C
/api/v2/share/~~ : 공유 파일 api
/api/v2/user/~~ : 개인 파일 api
```

### 변경 사항
* 텍스트 추출의 정확도를 높이기 위해서 'jhgan/ko-sbert-nli' 과 BM25 결합하여 사용 (EnsembleRetriever)
* EnsembleRetriever 를 사용하면서 이미 Embedding 된 값을 저장하기 위해 Vector DB 사용하지 않고 파일에 저장 (numpy 사용)
* offline 사용을 고려해서 다운로드 받은 모델을 사용함. 아래 코드 실행하여 다운 받음
``` C
python utils/model_download.py
```

### 이전 버전
* https://github.com/mroops-kr/simple-rag

### 작성자
* 작성자: mroops@naver.com
