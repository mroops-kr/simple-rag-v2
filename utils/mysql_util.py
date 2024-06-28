'''
pip install mysql-connector-python
pip install sql_metadata
pip install stringcase


'''
from dotenv import load_dotenv
load_dotenv()

import os
import mysql.connector
from stringcase import pascalcase
from sql_metadata import Parser
import datetime
import decimal


# 디버그용 - SQL 출력
debug_sql = True

select_ext_cols = {
}


'''
    Column 데이터
'''
class Col:
    def __init__(self, data):
        self.name = data[0]
        initCap = pascalcase(self.name)
        self.attr = initCap[0].lower() + initCap[1:]
        self.uattr = initCap
        self.pk = data[1] == 'PK'
        self.type = data[2]
    def __str__(self):
        return f'Col(name={self.name}, attr={self.attr}, pk={self.pk}, type={self.type})'

'''
    Table 의 Column 을 로드해서 SQL 자동 생성
'''
class TableLoader:

    table_map = {}
    table_seq_created = False
    
    # 싱글톤 - static 설정
    _singletone = None
    def __new__(cls, *args, **kwargs):
        if cls._singletone is None:
            cls._singletone = super().__new__(cls, *args, **kwargs)
            # 초기화 코드 여기에 추가
        return cls._singletone

    def _getCols(self, client, table):

        if table in self.table_map:
            return self.table_map[table]
        
        sql = """
            SELECT TT.COLUMN_NAME
                , CASE WHEN TT.COLUMN_KEY = 'PRI' 
                    THEN 'PK' ELSE ''
                END PK
                , TT.COLUMN_TYPE
            FROM (
                SELECT T.TABLE_NAME 
                    , C.COLUMN_NAME
                    , C.ORDINAL_POSITION
                    , C.COLUMN_TYPE
                    , C.COLUMN_KEY   
                FROM  INFORMATION_SCHEMA.TABLES  AS T
                    , INFORMATION_SCHEMA.COLUMNS AS C
                WHERE   T.TABLE_SCHEMA = %s
                    AND T.TABLE_SCHEMA   = C.TABLE_SCHEMA
                    AND T.TABLE_NAME   = %s
                    AND T.TABLE_NAME   = C.TABLE_NAME   
            ) TT
            LEFT JOIN INFORMATION_SCHEMA.STATISTICS IDX
                ON  TT.TABLE_NAME    = IDX.TABLE_NAME
                AND TT.COLUMN_NAME   = IDX.COLUMN_NAME
            ORDER BY TT.ORDINAL_POSITION
        """
        cursor = client.conn.cursor()
        cursor.execute(sql, (os.environ.get('mysql_database'), table))
        arr = []
        results = cursor.fetchall()
        for result in results:
            col = Col(result)
            print(col)
            arr.append(col)
        cursor.close()

        self.table_map[table] = arr
        return arr

    def mkSelect(self, client, table, data):
        sql = []
        param = []
        cols = self._getCols(client, table)

        sql.append('SELECT')
        for idx, col in enumerate(cols):
            if idx % 5 == 0:
                if idx != 0:
                    sql.append(',\n  ')
                else:
                    sql.append('\n  ')
            else:
                sql.append(', ')
            sql.append(col.name)

        if table in select_ext_cols:
            for ext_col in select_ext_cols[table]:
                sql.append(',\n  ')
                sql.append(ext_col)

        sql.append(f'\nFROM {table} T')

        hasWhere = False
        for k in data:
            hasWhere = self.setWhereSQL(cols, k, data[k], sql, param, hasWhere)

        if 'order_by' in data:
            sql.append(f"\nORDER BY {data['order_by']}")
        if 'limit' in data and 'offset' in data:
            sql.append(f"\nLIMIT {data['limit']} OFFSET {data['offset']}")

        va = {
            'sql': ''.join(sql),
            'param': tuple(param)
        }
        self.print_log(va)

        return va
    
    def print_log(self, va):
        global debug_sql
        if debug_sql:
            print('[sql]   ======================')
            print(va['sql'])
            print('[param] ======================')
            print(va['param'])
            print('==============================')

    def mkCount(self, client, table, data):
        sql = []
        param = []
        cols = self._getCols(client, table)

        sql.append(f"SELECT COUNT(*) count FROM {table}")

        hasWhere = False
        for k in data:
            hasWhere = self.setWhereSQL(cols, k, data[k], sql, param, hasWhere)

        va = {
            'sql': ''.join(sql),
            'param': tuple(param)
        }
        self.print_log(va)

        return va
    
    def setWhereSQL(self, cols, name, value, sql, param, hasWhere):
        if value == None or value == '':
            return
        
        for col in cols:
            if name == col.attr or name == col.name:
                if isinstance(value, list):
                
                    if len(value) > 0:
                        sqllet = f"{col.name} IN ("
                        for idx, item in enumerate(value):
                            if idx > 0:
                                sqllet = sqllet + ', '
                            
                            param.append(item)
                            sqllet = sqllet + '%s'
                        sqllet = sqllet + ')'

                        self._setWhereAnd(sql, hasWhere)
                        sql.append(sqllet)
                        return True
                    else:
                        return hasWhere
                else:
                    param.append(value)
                    self._setWhereAnd(sql, hasWhere)
                    sql.append(f"{col.name} = %s")
                    return True

            if name == f'min{col.uattr}' or name == f'min_{col.name}':
                param.append(value)
                self._setWhereAnd(sql, hasWhere)
                sql.append(f"{col.name} >= %s")
                return True
            if name == f'max{col.uattr}' or name == f'max_{col.name}':
                param.append(value)
                self._setWhereAnd(sql, hasWhere)
                sql.append(f"{col.name} <= %s")
                return True
        
        return hasWhere

    def _setWhereAnd(self, sql, hasWhere):
        if hasWhere:
            sql.append('\n  AND ')
        else:
            sql.append('\nWHERE ')

    def mkInsert(self, client, table, data):
        sql = []
        param = []
        cols = self._getCols(client, table)

        sql.append(f'INSERT INTO {table} (')
        idx = 0
        for col in cols:
            if col.attr in data or col.name in data:
                if idx % 5 == 0:
                    if idx == 0:
                        sql.append(f'\n  {col.name}')
                    else:
                        sql.append(f',\n  {col.name}')
                else:
                    sql.append(f', {col.name}')
                idx += 1

        sql.append('\n) VALUES (')
        idx = 0
        for col in cols:
            if col.attr in data or col.name in data:
                if idx % 5 == 0:
                    if idx == 0:
                        sql.append(f'\n  %s')
                    else:
                        sql.append(f',\n  %s')
                else:
                    sql.append(f', %s')
                idx += 1
                
                if col.attr in data:
                    param.append(data[col.attr])
                else:
                    param.append(data[col.name])

        sql.append('\n)')
        
        va = {
            'sql': ''.join(sql),
            'param': tuple(param)
        }
        self.print_log(va)

        return va

    def mkUpdate(self, client, table, data, whereData):
        sql = []
        param = []
        cols = self._getCols(client, table)

        sql.append(f'UPDATE {table} SET')
        first = True
        for col in cols:
            if (col.attr in data or col.name in data) and not col.pk:
                if first:
                    first = False
                else:
                    sql.append(',')
                
                sql.append(f'  {col.name} = %s')
                if col.attr in data:
                    param.append(data[col.attr])
                else:
                    param.append(data[col.name])

        if whereData is None:
            whereData = {}
            for col in cols:
                if (col.attr in data or col.name in data) and col.pk:
                    
                    if col.attr in data:
                        whereData[col.attr] = data[col.attr]
                    else:
                        whereData[col.name] = data[col.name]

        hasWhere = False
        for k in whereData:
            hasWhere = self.setWhereSQL(cols, k, whereData[k], sql, param, hasWhere)
        
        va = {
            'sql': ''.join(sql),
            'param': tuple(param)
        }
        self.print_log(va)

        return va
    
    def mkDelete(self, client, table, data):
        sql = []
        param = []
        cols = self._getCols(client, table)

        sql.append(f'DELETE FROM {table}')

        hasWhere = False
        for k in data:
            hasWhere = self.setWhereSQL(cols, k, data[k], sql, param, hasWhere)

        va = {
            'sql': ''.join(sql),
            'param': tuple(param)
        }
        self.print_log(va)
        
        return va

    def nextVal(self, client, table):
        if not self.table_seq_created:
            self.table_seq_created = True
            sql = """
                CREATE TABLE IF NOT EXISTS `table_seq` (
                    `table_id` varchar(45) NOT NULL,
                    `seq_va` int NOT NULL,
                    PRIMARY KEY (`table_id`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
            """
            conn = client.connect()
            cursor = conn.cursor()
            cursor.execute(sql, tuple([]))

            cursor.execute('SELECT seq_va FROM table_seq where table_id = %s FOR UPDATE', (table, ))
            result = cursor.fetchone()

            if result is None:
                cursor.execute('INSERT INTO table_seq(table_id, seq_va) VALUES ( %s, %s )', (table, 1))
                cursor.close()
                conn.commit()
                conn.close()
                return 1
            
            else:
                cursor.execute('UPDATE table_seq SET seq_va = seq_va + 1 WHERE table_id = %s', (table, ))
                cursor.close()
                conn.commit()
                conn.close()
                return result[0] + 1


'''
    TABLE - COLUMN 기반 SQL 자동 생성
'''
class Auto:
    def __init__(self, client):
        self.client = client
    
    def selectOne(self, table, param):
        va = TableLoader().mkSelect(self.client, table, param)
        return self.client.selectOne(va['sql'], va['param'], get_attr(param, '_column_type'))
    
    def selectList(self, table, param):
        va = TableLoader().mkSelect(self.client, table, param)
        return self.client.selectList(va['sql'], va['param'], get_attr(param, '_column_type'))
    
    def count(self, table, param):
        va = TableLoader().mkCount(self.client, table, param)
        return self.client.count(va['sql'], va['param'])
    
    def insert(self, table, param):
        va = TableLoader().mkInsert(self.client, table, param)
        return self.client.insert(va['sql'], va['param'])
    
    def update(self, table, param, whereParam = None):
        va = TableLoader().mkUpdate(self.client, table, param, whereParam)
        return self.client.update(va['sql'], va['param'])
    
    def delete(self, table, param):
        va = TableLoader().mkDelete(self.client, table, param)
        return self.client.delete(va['sql'], va['param'])
    
    def nextVal(self, table):
        return TableLoader().nextVal(self.client, table)

# 파라미터 리턴
def get_attr(param, key, defalt_va = None):
    if key in param:
        return param[key]
    return defalt_va

class MysqlClient:
    
    conn = None
    auto = None

    def __init__(self):
        from dotenv import load_dotenv
        load_dotenv()
        self.conn = self.connect()
        self.auto = Auto(self)
    
    def __del__(self):
        if self.conn != None:
            self.conn.close()

    def selectOne(self, sql, param, column_type = None):

        # SQL 실행
        cursor = self.conn.cursor()
        cursor.execute(sql, param)
        result = cursor.fetchone()
        
        if column_type is None:
            column_type = os.environ.get('mysql_column_case')

        # 컬럼 메타데이터
        attrs = []
        for metadata in cursor.description:
            if column_type == 'none':
                attrs.append(metadata[0])
            elif column_type == 'lower':
                attrs.append(metadata[0].lower())
            elif column_type == 'upper':
                attrs.append(metadata[0].upper())
            else:
                initCap = pascalcase(metadata[0])
                attrs.append(initCap[0].lower() + initCap[1:])

        # dict 변환
        va = {}
        for idx, item in enumerate(attrs):
            self._appendResult(va, item, result[idx])
        
        cursor.close()
        return va
    
    def count(self, sql, param):

        # SQL 실행
        cursor = self.conn.cursor()
        cursor.execute(sql, param)
        result = cursor.fetchone()

        return result[0]

    def selectList(self, sql, param, column_type = None):

        # SQL 실행
        cursor = self.conn.cursor()
        cursor.execute(sql, param)
        returnArr = []
        results = cursor.fetchall()

        if column_type is None:
            column_type = os.environ.get('mysql_column_case')

        # 컬럼 메타데이터
        attrs = []
        for metadata in cursor.description:
            if column_type == 'none':
                attrs.append(metadata[0])
            elif column_type == 'lower':
                attrs.append(metadata[0].lower())
            elif column_type == 'upper':
                attrs.append(metadata[0].upper())
            else:
                initCap = pascalcase(metadata[0])
                attrs.append(initCap[0].lower() + initCap[1:])

        # dict 변환
        for result in results:
            va = {}
            for idx, item in enumerate(attrs):
                self._appendResult(va, item, result[idx])
            returnArr.append(va)
        
        cursor.close()
        return returnArr
    
    def _appendResult(self, va, name, result):
        if isinstance(result, datetime.datetime):
            va[name] = str(result)
        elif isinstance(result, decimal.Decimal):
            va[name] = float(result)
        else:
            va[name] = result

    def insert(self, sql, param):
        cursor = self.conn.cursor()
        cursor.execute(sql, param)
        cursor.close()
        return True
    
    def update(self, sql, param):
        cursor = self.conn.cursor()
        cursor.execute(sql, param)
        cursor.close()
        return True
    
    def delete(self, sql, param):
        cursor = self.conn.cursor()
        cursor.execute(sql, param)
        cursor.close()
        return True
    
    def commit(self):
        self.conn.commit()

    def __enter__(self):
        return self # 반환값이 있어야 VARIABLE를 블록내에서 사용할 수 있다

    def connect(self):

        # print(f'mysql_host: {os.environ.get('mysql_host')}')
        # print(f'mysql_port: {os.environ.get('mysql_port')}')
        # print(f'mysql_user: {os.environ.get('mysql_user')}')
        # print(f'mysql_password: {os.environ.get('mysql_password')}')
        # print(f'mysql_database: {os.environ.get('mysql_database')}')

        conn = mysql.connector.connect(
            host = os.environ.get('mysql_host'),
            port = int(os.environ.get('mysql_port')),
            user = os.environ.get('mysql_user'),
            password = os.environ.get('mysql_password'),
            database = os.environ.get('mysql_database'),
        )
        return conn

    def __exit__(self, exc_type, exc_value, traceback):
        ""
        # 마지막 처리를 한다(자원반납 등)
        # print('__exit__')

