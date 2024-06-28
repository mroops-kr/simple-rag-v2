
'''
pip install PyPDF2
pip install PyMuPDF
pip install TextLoader
pip install docx
pip install python-docx
pip install pypandoc


pandoc
https://github.com/jgm/pandoc/releases/

sudo apt-get install pandoc
sudo apt-get install texlive-latex-base
'''
from PyPDF2 import PdfReader
from langchain.schema import Document
from langchain.document_loaders import TextLoader
import docx
import os

def loadFile(filePath: str):

    rag_chunk_max = int(os.environ.get('rag_chunk_max'))
    dot_index = filePath.rfind('.')
    file_ext  = filePath[dot_index + 1:].lower()

    # pdf 로드
    if file_ext == 'pdf':
        reader = PdfReader(filePath)
        documents = []
        for index, page in enumerate(reader.pages):
            text = page.extract_text()
            if text and text != '':
                documents.append({'text': text, 'page': index+1})
        return documents
    
    # txt 로드
    elif file_ext == 'txt':
        with open(file = filePath, mode = "r", encoding = "utf-8") as f:
            
            documents = []
            new_lines = []
            count = 0
            page = 1
            all_lines = f.readlines()

            # 5000 자가 넘지 않게 페이지 분할
            for line in all_lines:
                if line and line != '':
                    if len(line) + count > rag_chunk_max:
                        text = "\n".join(new_lines)
                        documents.append({'text': text, 'page': page})
                        page += 1
                        new_lines = []
                        count = 0
                    new_lines.append(line)
                    count += len(line)
            
            documents.append({'text': "".join(new_lines), 'page': page})
            return documents

    elif file_ext == 'doc' or file_ext == 'docx':
        doc = docx.Document(filePath)

        count = 0
        page = 1
        new_lines = []
        documents = []

        for paragraph in doc.paragraphs:
            line = paragraph.text

            # 5000 자가 넘지 않게 페이지 분할
            if line and line != '':
                if len(line) + count > rag_chunk_max:
                    text = "\n".join(new_lines)
                    documents.append({'text': text, 'page': page})
                    page += 1
                    new_lines = []
                    count = 0
                new_lines.append(line)
                count += len(line)

        documents.append({'text': "".join(new_lines), 'page': page})
        return documents

    return None

# # doc >> pdf 변환
# import pypandoc
# def convert_docx_to_pdf(docx_path, pdf_path):
#     pypandoc.convert_file(docx_path, 'pdf', outputfile=pdf_path)
