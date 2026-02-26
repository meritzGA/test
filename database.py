"""
데이터베이스 관리 모듈
- 현재: SQLite (로컬 파일)
- 전환 가능: PostgreSQL, MySQL 등 외부 DB로 전환 시 get_connection()과 쿼리만 수정
"""

import sqlite3
import pandas as pd
from datetime import datetime
import os
import json


# ──────────────────────────────────────────────
# DB 연결 (외부 DB 전환 시 이 부분만 수정)
# ──────────────────────────────────────────────
DB_PATH = os.environ.get("DB_PATH", "data/manager_system.db")


def get_connection():
    """
    SQLite 연결 반환
    [외부 DB 전환 예시 - PostgreSQL]
    import psycopg2
    return psycopg2.connect(
        host=os.environ.get("DB_HOST"),
        port=os.environ.get("DB_PORT", 5432),
        dbname=os.environ.get("DB_NAME"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD")
    )
    """
    os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """DB 초기화 - 테이블 생성"""
    conn = get_connection()
    cursor = conn.cursor()

    # 업로드 파일 추적
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS uploaded_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT NOT NULL,
            file_type TEXT NOT NULL,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            row_count INTEGER DEFAULT 0,
            col_count INTEGER DEFAULT 0,
            join_column TEXT
        )
    """)

    # 조인 설정 저장
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS join_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_a_join_col TEXT,
            file_b_join_col TEXT,
            manager_code_cols TEXT,
            customer_name_col TEXT,
            customer_number_col TEXT,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 메시지 발송 로그
    # [외부 DB 전환 시] TIMESTAMP → TIMESTAMPTZ, TEXT → VARCHAR 등으로 변경
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS message_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            manager_code TEXT NOT NULL,
            manager_name TEXT,
            customer_number TEXT NOT NULL,
            customer_name TEXT,
            message_type INTEGER NOT NULL,
            sent_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            month_key TEXT NOT NULL
        )
    """)

    # 로그인 로그
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS login_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            manager_code TEXT NOT NULL,
            manager_name TEXT,
            login_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 시상 JSON 데이터
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prize_json_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_json TEXT NOT NULL,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 인덱스 생성
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_msg_manager ON message_logs(manager_code)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_msg_month ON message_logs(month_key)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_msg_customer ON message_logs(customer_number)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_login_manager ON login_logs(manager_code)")

    conn.commit()
    conn.close()


# ──────────────────────────────────────────────
# 파일 업로드 관리
# ──────────────────────────────────────────────

def save_uploaded_file(df: pd.DataFrame, file_name: str, file_type: str, join_column: str = None):
    """업로드된 파일을 DB에 저장"""
    conn = get_connection()

    # 매니저코드 등 숫자형 코드 컬럼을 문자열로 변환 (float → int → str)
    code_keywords = ["코드", "번호", "ID", "id"]
    for col in df.columns:
        if any(kw in col for kw in code_keywords):
            if df[col].dtype in ["float64", "float32"]:
                df[col] = df[col].apply(lambda x: str(int(x)) if pd.notna(x) else "")
            elif df[col].dtype in ["int64", "int32"]:
                df[col] = df[col].astype(str)

    # 파일 메타데이터 저장
    conn.execute(
        "INSERT INTO uploaded_files (file_name, file_type, row_count, col_count, join_column) VALUES (?, ?, ?, ?, ?)",
        (file_name, file_type, len(df), len(df.columns), join_column)
    )

    # 데이터를 테이블로 저장 (기존 테이블 덮어쓰기)
    table_name = f"raw_{file_type.lower()}"
    df.to_sql(table_name, conn, if_exists="replace", index=False)

    conn.commit()
    conn.close()


def delete_uploaded_file(file_type: str):
    """업로드된 파일 삭제"""
    conn = get_connection()
    conn.execute("DELETE FROM uploaded_files WHERE file_type = ?", (file_type,))
    table_name = f"raw_{file_type.lower()}"
    try:
        conn.execute(f"DROP TABLE IF EXISTS {table_name}")
    except Exception:
        pass
    conn.commit()
    conn.close()


def get_uploaded_files():
    """업로드된 파일 목록 조회"""
    conn = get_connection()
    # [외부 DB 전환 시] SELECT 쿼리는 동일
    rows = conn.execute(
        "SELECT file_type, file_name, upload_date, row_count, col_count, join_column FROM uploaded_files ORDER BY upload_date DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_raw_data(file_type: str) -> pd.DataFrame:
    """원본 데이터 조회"""
    conn = get_connection()
    table_name = f"raw_{file_type.lower()}"
    try:
        df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df


def get_raw_columns(file_type: str) -> list:
    """원본 데이터 컬럼 목록"""
    conn = get_connection()
    table_name = f"raw_{file_type.lower()}"
    try:
        cursor = conn.execute(f"PRAGMA table_info({table_name})")
        cols = [row[1] for row in cursor.fetchall()]
    except Exception:
        cols = []
    conn.close()
    return cols


# ──────────────────────────────────────────────
# 데이터 병합 (조인)
# ──────────────────────────────────────────────

def merge_data(file_a_type: str, file_b_type: str, col_a: str, col_b: str):
    """두 파일을 outer join으로 병합"""
    df_a = get_raw_data(file_a_type)
    df_b = get_raw_data(file_b_type)

    if df_a.empty and df_b.empty:
        return pd.DataFrame()

    if df_a.empty:
        merged = df_b.copy()
    elif df_b.empty:
        merged = df_a.copy()
    else:
        # 중복 컬럼명 처리: 접미사 추가
        merged = pd.merge(
            df_a, df_b,
            left_on=col_a, right_on=col_b,
            how="outer",
            suffixes=("_A", "_B")
        )

    # 병합 결과 저장
    conn = get_connection()
    merged.to_sql("merged_data", conn, if_exists="replace", index=False)

    # 조인 설정 저장
    conn.execute("DELETE FROM join_config")
    conn.execute(
        "INSERT INTO join_config (file_a_join_col, file_b_join_col) VALUES (?, ?)",
        (col_a, col_b)
    )
    conn.commit()
    conn.close()

    return merged


def get_merged_data() -> pd.DataFrame:
    """병합된 데이터 조회"""
    conn = get_connection()
    try:
        df = pd.read_sql("SELECT * FROM merged_data", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df


def get_merged_columns() -> list:
    """병합된 데이터 컬럼 목록"""
    conn = get_connection()
    try:
        cursor = conn.execute("PRAGMA table_info(merged_data)")
        cols = [row[1] for row in cursor.fetchall()]
    except Exception:
        cols = []
    conn.close()
    return cols


def delete_merged_data():
    """병합 데이터 삭제"""
    conn = get_connection()
    try:
        conn.execute("DROP TABLE IF EXISTS merged_data")
        conn.execute("DELETE FROM join_config")
    except Exception:
        pass
    conn.commit()
    conn.close()


# ──────────────────────────────────────────────
# 매니저별 사용인 조회
# ──────────────────────────────────────────────

def get_users_by_manager(manager_code: str, manager_col_list: list) -> pd.DataFrame:
    """
    매니저 코드로 매칭된 사용인 목록 조회
    manager_col_list: 매니저코드가 들어있는 컬럼명 리스트
    """
    conn = get_connection()
    try:
        # 입력값 정규화: 소수점 제거
        clean_code = str(manager_code).replace(".0", "").strip()

        # OR 조건으로 여러 매니저코드 컬럼 검색 (문자열, float 양쪽 매칭)
        conditions = []
        params = []
        for col in manager_col_list:
            conditions.append(f'(CAST("{col}" AS TEXT) = ? OR CAST("{col}" AS TEXT) = ?)')
            params.extend([clean_code, clean_code + ".0"])

        where_clause = " OR ".join(conditions)
        query = f"SELECT * FROM merged_data WHERE {where_clause}"
        df = pd.read_sql(query, conn, params=params)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df


# ──────────────────────────────────────────────
# 메시지 로그
# ──────────────────────────────────────────────

def log_message(manager_code: str, manager_name: str,
                customer_number: str, customer_name: str,
                message_type: int):
    """메시지 발송 로그 기록"""
    month_key = datetime.now().strftime("%Y%m")
    conn = get_connection()
    # [외부 DB 전환 시] INSERT 쿼리 동일, CURRENT_TIMESTAMP → NOW() 등
    conn.execute(
        """INSERT INTO message_logs
           (manager_code, manager_name, customer_number, customer_name, message_type, month_key)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (str(manager_code), manager_name, str(customer_number), customer_name, message_type, month_key)
    )
    conn.commit()
    conn.close()


def get_message_logs_for_customer(manager_code: str, customer_number: str) -> list:
    """특정 매니저-고객 조합의 당월 메시지 로그 조회"""
    month_key = datetime.now().strftime("%Y%m")
    conn = get_connection()
    rows = conn.execute(
        """SELECT message_type, sent_date FROM message_logs
           WHERE manager_code = ? AND customer_number = ? AND month_key = ?
           ORDER BY sent_date DESC""",
        (str(manager_code), str(customer_number), month_key)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_message_summary_for_manager(manager_code: str) -> dict:
    """매니저별 당월 메시지 발송 요약"""
    month_key = datetime.now().strftime("%Y%m")
    conn = get_connection()
    rows = conn.execute(
        """SELECT message_type,
                  COUNT(DISTINCT customer_number) as unique_customers,
                  COUNT(*) as total_count
           FROM message_logs
           WHERE manager_code = ? AND month_key = ?
           GROUP BY message_type""",
        (str(manager_code), month_key)
    ).fetchall()
    conn.close()
    return {row["message_type"]: {"customers": row["unique_customers"], "count": row["total_count"]} for row in rows}


def get_all_message_summary() -> pd.DataFrame:
    """전체 매니저 메시지 발송 요약 (관리자용)"""
    month_key = datetime.now().strftime("%Y%m")
    conn = get_connection()
    # [외부 DB 전환 시] 쿼리 동일
    df = pd.read_sql(
        """SELECT
               manager_code as 매니저코드,
               manager_name as 매니저명,
               message_type as 메시지유형,
               COUNT(DISTINCT customer_number) as 발송인원,
               COUNT(*) as 발송횟수
           FROM message_logs
           WHERE month_key = ?
           GROUP BY manager_code, manager_name, message_type
           ORDER BY manager_code, message_type""",
        conn, params=[month_key]
    )
    conn.close()
    return df


# ──────────────────────────────────────────────
# 로그인 로그
# ──────────────────────────────────────────────

def log_login(manager_code: str, manager_name: str = ""):
    """로그인 로그 기록"""
    conn = get_connection()
    conn.execute(
        "INSERT INTO login_logs (manager_code, manager_name) VALUES (?, ?)",
        (str(manager_code), manager_name)
    )
    conn.commit()
    conn.close()


def get_login_logs() -> pd.DataFrame:
    """로그인 로그 조회 (관리자용)"""
    conn = get_connection()
    df = pd.read_sql(
        """SELECT
               manager_code as 매니저코드,
               manager_name as 매니저명,
               login_date as 로그인시간,
               COUNT(*) OVER (PARTITION BY manager_code) as 총로그인횟수
           FROM login_logs
           ORDER BY login_date DESC
           LIMIT 500""",
        conn
    )
    conn.close()
    return df


def get_login_summary() -> pd.DataFrame:
    """로그인 요약 (관리자용)"""
    month_key = datetime.now().strftime("%Y%m")
    conn = get_connection()
    df = pd.read_sql(
        """SELECT
               manager_code as 매니저코드,
               manager_name as 매니저명,
               COUNT(*) as 로그인횟수,
               MAX(login_date) as 최근로그인
           FROM login_logs
           WHERE strftime('%%Y%%m', login_date) = ?
           GROUP BY manager_code, manager_name
           ORDER BY 로그인횟수 DESC""",
        conn, params=[month_key]
    )
    conn.close()
    return df


# ──────────────────────────────────────────────
# 시상 JSON
# ──────────────────────────────────────────────

def save_prize_json(data: dict):
    """시상 JSON 데이터 저장"""
    conn = get_connection()
    conn.execute("DELETE FROM prize_json_data")  # 기존 데이터 삭제
    conn.execute(
        "INSERT INTO prize_json_data (data_json) VALUES (?)",
        (json.dumps(data, ensure_ascii=False),)
    )
    conn.commit()
    conn.close()


def get_prize_json() -> dict:
    """시상 JSON 데이터 조회"""
    conn = get_connection()
    row = conn.execute("SELECT data_json FROM prize_json_data ORDER BY upload_date DESC LIMIT 1").fetchone()
    conn.close()
    if row:
        return json.loads(row["data_json"])
    return {}


def delete_prize_json():
    """시상 JSON 삭제"""
    conn = get_connection()
    conn.execute("DELETE FROM prize_json_data")
    conn.commit()
    conn.close()


# ──────────────────────────────────────────────
# 월간 초기화
# ──────────────────────────────────────────────

def cleanup_old_month_logs():
    """이전 달 메시지 로그 정리 (당월만 유지)
    [외부 DB 전환 시] 크론잡이나 스케줄러로 매월 1일 실행
    """
    month_key = datetime.now().strftime("%Y%m")
    conn = get_connection()
    conn.execute("DELETE FROM message_logs WHERE month_key != ?", (month_key,))
    conn.commit()
    conn.close()
