import streamlit as st
import pandas as pd
import random
import os
import time
import json
import base64

# --- [기능 함수 정의] ---
@st.cache_data
def get_audio_base64(file_path):
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except:
        return None

def play_sound(file_path):
    if not st.session_state.get('sound_on', True):
        return
    b64_string = get_audio_base64(file_path)
    if b64_string:
        timestamp = time.time()
        md = f"""
            <audio autoplay="true" id="audio_{timestamp}">
                <source src="data:audio/mp3;base64,{b64_string}" type="audio/mp3">
            </audio>
            """
        st.markdown(md, unsafe_allow_html=True)

# --- [페이지 설정 및 CSS] ---
st.set_page_config(page_title="2026 민실연 가족법", layout="wide", page_icon="⚖️")

st.markdown("""
    <style>
    .question-box {
        background-color: #f1f3f5;
        color: #000000 !important;
        padding: 20px;
        border-radius: 12px;
        border-left: 8px solid #2e7d32;
        margin-bottom: 10px;
        font-size: 1.1rem;
        font-weight: 500;
        line-height: 1.5;
    }
    .stButton>button {
        width: 100% !important; 
        height: 3em;
        font-size: 16px !important;
        font-weight: bold !important;
        color: #ffffff !important;
        background-color: #262730;
        border-radius: 8px;
    }
    .correct-feedback-text {
        background-color: #e6ffed;
        color: #1a7f37;
        padding: 5px 10px;
        border-radius: 5px;
        font-weight: bold;
    }
    .wrong-feedback-text {
        background-color: #ffebe8;
        color: #b02a37;
        padding: 5px 15px;
        border-radius: 5px;
        font-weight: bold;
    }
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
        gap: 0.3rem !important; 
    }
    </style>
    """, unsafe_allow_html=True)

# --- [데이터 로드 로직: data.xlsx 전용] ---
@st.cache_data
def load_excel_data():
    file_path = "data.xlsx"
    if os.path.exists(file_path):
        try:
            # 엑셀 파일 로드 (연도, 단원, 문제, 정답, 해설 열 포함 가정)
            df = pd.read_excel(file_path)
            # 연도 데이터가 숫자일 경우 대비하여 문자열로 변환 및 소수점 제거
            if '연도' in df.columns:
                df['연도'] = df['연도'].astype(str).str.replace(".0", "", regex=False)
            return df
        except Exception as e:
            st.error(f"엑셀 로드 중 오류 발생: {e}")
            return pd.DataFrame()
    else:
        st.error("폴더 내에 data.xlsx 파일이 없습니다.")
        return pd.DataFrame()

# --- [세션 상태 초기화] ---
if 'full_db' not in st.session_state:
    st.session_state.full_db = load_excel_data()
if 'selected_years' not in st.session_state: 
    st.session_state.selected_years = []
if 'selected_chapters' not in st.session_state:
    st.session_state.selected_chapters = []
if 'wrong_notes' not in st.session_state:
    st.session_state.wrong_notes = pd.DataFrame(columns=['연도', '단원', '문제', '정답', '해설'])
if 'exam_list' not in st.session_state:
    st.session_state.exam_list = []
if 'idx' not in st.session_state:
    st.session_state.idx = 0
if 'answered' not in st.session_state:
    st.session_state.answered = False
if 'wn_idx' not in st.session_state:
    st.session_state.wn_idx = 0
if 'uploader_key' not in st.session_state:
    st.session_state.uploader_key = 0
if 'total_solving_time' not in st.session_state:
    st.session_state.total_solving_time = 0.0
if 'q_start_time' not in st.session_state:
    st.session_state.q_start_time = None
if 'correct_count' not in st.session_state:
    st.session_state.correct_count = 0
if 'sound_on' not in st.session_state:
    st.session_state.sound_on = True

# --- [사이드바 필터 설정] ---
with st.sidebar:
    st.title("⚖️ 학습 설정")
    st.toggle("🔊 효과음", key="sound_on")
    st.divider()

    if st.button("📖 사용방법 보기", use_container_width=True):
        show_manual()
    st.divider()

    if not st.session_state.full_db.empty:
        st.subheader("📅 범위 선택")
        
        # 1. 연도 선택
        all_years = sorted(st.session_state.full_db['연도'].unique().tolist(), reverse=True)
        sel_years = st.multiselect("연도 선택", all_years, key="selected_years")
        
        # 2. 단원 선택 (선택된 연도에 해당하는 단원만 표시)
        if sel_years:
            filtered_by_year = st.session_state.full_db[st.session_state.full_db['연도'].isin(sel_years)]
        else:
            filtered_by_year = st.session_state.full_db
            
        all_chapters = sorted(filtered_by_year['단원'].unique().tolist())
        sel_chapters = st.multiselect("단원 선택 (미선택 시 전체)", all_chapters, key="selected_chapters")

        # 최종 필터링된 DB 생성
        if sel_years:
            current_db = filtered_by_year
            if sel_chapters:
                current_db = current_db[current_db['단원'].isin(sel_chapters)]
        else:
            current_db = pd.DataFrame() # 연도 선택 전에는 빈 값
    else:
        current_db = pd.DataFrame()

    st.divider()
    st.subheader("💾 데이터 관리")
    # 오답노트 저장/복구 (기존 기능 유지)
    csv_dn = st.session_state.wrong_notes.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 내 오답노트 저장", csv_dn, "my_wrong_notes.csv", "text/csv", use_container_width=True)
    
    up_csv = st.file_uploader("📤 오답노트 복구", type="csv", key=f"csv_up_{st.session_state.uploader_key}")
    if up_csv:
        try:
            st.session_state.wrong_notes = pd.read_csv(up_csv)
            st.session_state.uploader_key += 1
            st.toast("오답노트 복구 완료! ✅")
            time.sleep(0.5)
            st.rerun()
        except: st.error("CSV 복구 실패")

# --- [메인 화면] ---
st.title("⚖️ 2026 민실연 중간고사 가족법")

tab1, tab2, tab3 = st.tabs(["📝 문제 풀이", "❌ 오답 집중 복습", "📚 전체 조회"])

# --- Tab 1: 문제 풀이 ---
with tab1:
    if current_db.empty:
        if st.session_state.full_db.empty:
            st.warning("data.xlsx 파일을 찾을 수 없습니다.")
        else:
            st.info("왼쪽 사이드바에서 **연도**를 먼저 선택해주세요.")
    else:
        st.success(f"현재 선택 범위: 총 {len(current_db)}문항이 준비되었습니다.")
        
        col_setup1, col_setup2 = st.columns([1, 2])
        with col_setup1:
            num = st.number_input("출제 문항 수", 1, len(current_db), min(10, len(current_db)))
        with col_setup2:
            st.write("") # 간격 맞춤
            if st.button("🚀 새 시험 시작", use_container_width=True):
                st.session_state.exam_list = current_db.sample(n=num).to_dict('records')
                st.session_state.idx = 0
                st.session_state.answered = False
                st.session_state.correct_count = 0
                st.session_state.total_solving_time = 0.0
                st.session_state.q_start_time = time.time()
                st.rerun()

        if st.session_state.get('exam_list'):
            exam = st.session_state.exam_list
            curr_idx = st.session_state.idx
            
            if curr_idx < len(exam):
                q = exam[curr_idx]
                st.write(f"### 📝 문제 {curr_idx + 1} / {len(exam)}")
                st.progress((curr_idx + 1) / len(exam))
                
                if not st.session_state.answered and st.session_state.q_start_time is None:
                    st.session_state.q_start_time = time.time()

                st.markdown(f'<div class="question-box"><b>[{q["연도"]} | {q["단원"]}]</b><br><br>{str(q["문제"])}</div>', unsafe_allow_html=True)
                
                user_input = None
                b_cols = st.columns(3)
                with b_cols[0]: 
                    if st.button("O", key=f"o_{curr_idx}"): user_input = "O"
                with b_cols[1]: 
                    if st.button("X", key=f"x_{curr_idx}"): user_input = "X"
                with b_cols[2]: 
                    if st.button("?", key=f"q_{curr_idx}"): user_input = "?"

                if user_input and not st.session_state.answered:
                    solve_duration = time.time() - st.session_state.q_start_time
                    st.session_state.total_solving_time += solve_duration
                    st.session_state.q_start_time = None 
                    st.session_state.answered = True
                    
                    correct_ans = str(q['정답']).strip().upper()
                    is_correct = (user_input == correct_ans)
                    st.session_state.last_is_correct = is_correct
                    
                    if is_correct: 
                        st.session_state.correct_count += 1
                    else:
                        if q['문제'] not in st.session_state.wrong_notes['문제'].values:
                            st.session_state.wrong_notes = pd.concat([st.session_state.wrong_notes, pd.DataFrame([q])], ignore_index=True)
                    
                    st.session_state.last_exp = q['해설']
                    st.session_state.last_ans = correct_ans

                if st.session_state.answered:
                    if st.session_state.last_is_correct:
                        play_sound("correct.mp3") 
                        st.markdown("<span class='correct-feedback-text'>정답입니다!</span>", unsafe_allow_html=True)
                    else:
                        play_sound("wrong.mp3") 
                        st.markdown("<span class='wrong-feedback-text'>틀렸습니다!</span>", unsafe_allow_html=True)

                    with st.expander("📖 해설 보기", expanded=True):
                        st.markdown(f"### 정답: {st.session_state.last_ans}") 
                        st.write(st.session_state.last_exp)
                    
                    if st.button("다음 문제 ➡️", use_container_width=True):
                        st.session_state.idx += 1
                        st.session_state.answered = False
                        st.rerun()

            else:
                st.balloons()
                st.header("📊 결과 리포트")
                c1, c2, c3 = st.columns(3)
                c1.metric("정답 수", f"{st.session_state.correct_count} / {len(exam)}")
                c2.metric("정답률", f"{(st.session_state.correct_count/len(exam))*100:.1f}%")
                c3.metric("평균 속도", f"{st.session_state.total_solving_time/len(exam):.1f}초")
                if st.button("🔄 다시 하기", use_container_width=True):
                    st.session_state.exam_list = []
                    st.rerun()

# --- Tab 2: 오답 집중 복습 ---
with tab2:
    wn = st.session_state.wrong_notes
    if wn.empty:
        st.info("오답 노트가 비어 있습니다.")
    else:
        st.subheader(f"현재 오답: {len(wn)}개")
        if st.button("🔀 순서 섞기", use_container_width=True):
            st.session_state.wrong_notes = wn.sample(frac=1).reset_index(drop=True)
            st.session_state.wn_idx = 0
            st.rerun()
        
        st.divider()
        if st.session_state.wn_idx >= len(wn): st.session_state.wn_idx = 0

        n1, n2, n3 = st.columns([1, 2, 1])
        with n1:
            if st.button("⬅️ 이전", key="prev_w"):
                st.session_state.wn_idx = (st.session_state.wn_idx - 1) % len(wn); st.rerun()
        with n2:
            st.markdown(f"<p style='text-align: center;'>{st.session_state.wn_idx + 1} / {len(wn)}</p>", unsafe_allow_html=True)
        with n3:
            if st.button("다음 ➡️", key="next_w"):
                st.session_state.wn_idx = (st.session_state.wn_idx + 1) % len(wn); st.rerun()
        
        q_wn = wn.iloc[st.session_state.wn_idx]
        st.markdown(f'<div class="question-box"><b>[{q_wn["연도"]} | {q_wn["단원"]}]</b><br><br>{q_wn["문제"]}</div>', unsafe_allow_html=True)
        
        with st.expander("📖 정답 및 해설 확인"):
            st.info(f"정답: {q_wn['정답']}")
            st.write(q_wn['해설'])

        if st.button("✅ 오답노트에서 삭제", use_container_width=True):
            st.session_state.wrong_notes = wn.drop(wn.index[st.session_state.wn_idx]).reset_index(drop=True)
            st.rerun()

# --- Tab 3: 전체 조회 ---
with tab3:
    st.header("📚 전체 데이터베이스 조회")
    st.dataframe(st.session_state.full_db, use_container_width=True)

# 하단 정보
st.sidebar.markdown("""
<div style="font-size: 0.8rem; color: gray; margin-top: 20px;">
16기 유각준<br>
</div>
""", unsafe_allow_html=True)
