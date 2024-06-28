import random
import string

characters = string.ascii_letters + string.digits

# 랜덤 텍스트 리턴
def random_text(length):
    global characters
    random_text = ''.join(random.choice(characters) for _ in range(length))
    return random_text

# 파라미터 리턴
def get_attr(param, key, defalt_va = None):
    if key in param:
        return param[key]
    return defalt_va

# value 값 없으면 random 생성 리턴
def get_random(param, key, size):
    value = get_attr(param, key)
    if value is None:
        return random_text(size)
    return value
