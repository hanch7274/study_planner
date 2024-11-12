import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import calendar
import httpx
import asyncio
from typing import List, Dict, Any
import time


class APIClient:
    def __init__(self, base_url: str = None):
        self.base_url = base_url or st.secrets["API_URL"] if "API_URL" in st.secrets else "http://localhost:8000"
        self._client = None
    
    async def get_client(self):
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=10.0
            )
        return self._client
    
    async def close(self):
        if self._client is not None:
            await self._client.aclose()
            self._client = None
    
    async def fetch_members(self):
        try:
            client = await self.get_client()
            response = await client.get("/members")
            return response.json()
        except Exception as e:
            st.error(f"멤버 정보 조회 중 오류 발생: {str(e)}")
            return []

    async def add_member(self, name: str, email: str):
        try:
            if not name or not email:
                raise ValueError("이름과 이메일을 모두 입력해주세요")
            
            client = await self.get_client()    
            response = await client.post(
                "/members",
                json={"name": name, "email": email}
            )
            
            if response.status_code != 200:
                raise Exception("서버 오류가 발생했습니다")
                
            return response.json()
            
        except ValueError as e:
            st.error(str(e))
            return {"status": "error", "message": str(e)}
        except Exception as e:
            st.error(f"멤버 추가 중 오류 발생: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def delete_member(self, member_id: int):
        try:
            client = await self.get_client()
            response = await client.delete(f"/members/{member_id}")
            return response.json()
        except Exception as e:
            st.error(f"멤버 삭제 중 오류 발생: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def fetch_goals(self, member_id: int):
        try:
            client = await self.get_client()
            response = await client.get(f"/goals/{member_id}")
            return response.json()
        except Exception as e:
            st.error(f"목표 정보 조회 중 오류 발생: {str(e)}")
            return []

    async def add_goal(self, user_id: int, title: str, target_date: datetime):
        try:
            client = await self.get_client()
            response = await client.post(
                "/goals",
                json={
                    "user_id": user_id,
                    "title": title,
                    "target_date": target_date.strftime("%Y-%m-%d")
                }
            )
            return response.json()
        except Exception as e:
            st.error(f"목표 추가 중 오류 발생: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def toggle_goal_complete(self, goal_id: int):
        try:
            client = await self.get_client()
            response = await client.put(f"/goals/{goal_id}/toggle")
            return response.json()
        except Exception as e:
            st.error(f"목표 상태 변경 중 오류 발생: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def delete_goal(self, goal_id: int):
        try:
            client = await self.get_client()
            response = await client.delete(f"/goals/{goal_id}")
            return response.json()
        except Exception as e:
            st.error(f"목표 삭제 중 오류 발생: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def get_study_note(self, goal_id: int):
        """학습 노트 조회"""
        try:
            client = await self.get_client()
            response = await client.get(f"/goals/{goal_id}/notes")  # 엔드포인트 수정
            return response.json()
        except Exception as e:
            st.error(f"노트 조회 중 오류 발생: {str(e)}")
            return None

    async def save_study_note(self, goal_id: int, user_id: int, note_date: str, content: str):
        """학습 노트 저장"""
        try:
            client = await self.get_client()
            response = await client.post(
                f"/goals/{goal_id}/notes",
                json={
                    "goal_id": goal_id,
                    "user_id": user_id,
                    "note_date": note_date,
                    "content": content
                }
            )
            return response.json()
        except Exception as e:
            st.error(f"노트 저장 중 오류 발생: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def get_weekly_notes(self, user_id: int, start_date: str, end_date: str):
        """주간 노트 조회"""
        try:
            client = await self.get_client()
            response = await client.get(
                f"/users/{user_id}/notes/weekly",  # 엔드포인트 수정
                params={"start_date": start_date, "end_date": end_date}
            )
            return response.json()
        except Exception as e:
            st.error(f"주간 노트 조회 중 오류 발생: {str(e)}")
            return []


class AsyncCache:
    def __init__(self, ttl: int = 60):
        self.cache = {}
        self.timestamps = {}
        self.ttl = ttl
    
    def get(self, key: str) -> Any:
        if key in self.cache:
            if time.time() - self.timestamps[key] < self.ttl:
                return self.cache[key]
            else:
                del self.cache[key]
                del self.timestamps[key]
        return None
    
    def set(self, key: str, value: Any):
        self.cache[key] = value
        self.timestamps[key] = time.time()
    
    def clear(self):
        self.cache.clear()
        self.timestamps.clear()
    
    async def get_or_set(self, key: str, fetch_func):
        cached_value = self.get(key)
        if cached_value is not None:
            return cached_value
        
        value = await fetch_func()
        self.set(key, value)
        return value


class StateManager:
    def __init__(self):
        self.goals_cache = AsyncCache(ttl=5)
        self.members_cache = AsyncCache(ttl=5)
        self.api_client = APIClient("http://localhost:8000")
    
    async def cleanup(self):
        await self.api_client.close()

async def safe_api_call(func, error_message="API 호출 중 오류가 발생했습니다"):
    try:
        return await func()
    except Exception as e:
        st.error(f"{error_message}: {str(e)}")
        return None

# 세션 상태 초기화
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    st.session_state.state_manager = StateManager()
    st.session_state.member_colors = {}
    st.session_state.selected_dates = []
    st.session_state.selected_week_offset = 0
    st.session_state.needs_rerun = False
    st.session_state.current_user_id = None


# get_member_color 함수를 전역 함수로 수정
def get_member_color(member_id: int) -> str:
    """멤버별 고유 색상을 반환하는 함수"""
    if member_id not in st.session_state.member_colors:
        # 미리 정의된 색상 목록
        colors = [
            '#FF6B6B',  # 빨간색
            '#4ECDC4',  # 청록색
            '#45B7D1',  # 하늘색
            '#96CEB4',  # 민트색
            '#FFEEAD',  # 노란색
            '#D4A5A5',  # 분홍색
            '#9FA8DA',  # 보라색
            '#88D8B0',  # 연두색
            '#FFB6B9',  # 연한 빨간색
            '#B5EAD7',  # 연한 초록색
        ]
        # 멤버 ID에 따라 색상 할당 (순환)
        st.session_state.member_colors[member_id] = colors[len(st.session_state.member_colors) % len(colors)]
    
    return st.session_state.member_colors[member_id]

# 페이지 설정
st.set_page_config(
    page_title="스터디 플래너",
    page_icon="📚",
    layout="wide"
)

# 통합된 CSS 스타일
st.markdown("""
    <style>
    /* 기본 스타일 */
    .week-info {
        text-align: center;
        padding: 10px;
        background-color: #f0f2f6;
        border-radius: 5px;
        margin: 10px 0;
    }
    .note-card {
        border: 1px solid #ddd;
        border-radius: 5px;
        padding: 15px;
        margin: 10px 0;
    }
    .note-content {
        white-space: pre-wrap;
        background-color: #f8f9fa;
        padding: 10px;
        border-radius: 5px;
    }
    
    /* 달력 스타일 */
    .calendar {
        width: 100%;
        border-collapse: collapse;
    }
    .calendar th, .calendar td {
        border: 1px solid #ddd;
        padding: 8px;
        text-align: center;
        height: 80px;
        vertical-align: top;
    }
    .calendar th {
        background-color: #f8f9fa;
        height: auto;
    }
    .date {
        font-size: 0.9em;
        margin-bottom: 5px;
    }
    .goal-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        display: inline-block;
        margin: 1px;
    }
    
    /* 네비게이션 버튼 */
    .week-nav-button {
        border: none;
        background: white;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        color: #444;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .week-nav-button:hover {
        background: #e7f3ff;
        color: #0066cc;
    }
    
    /* 목표 테이블 */
    .goals-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0 0.5rem;
        margin-top: 1rem;
    }
    .goals-header {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        color: #666;
        font-weight: 600;
        font-size: 0.9rem;
    }
    .goal-row {
        background: white;
        border-radius: 8px;
        margin-bottom: 0.5rem;
        transition: all 0.2s;
    }
    .goal-row:hover {
        background: #f8f9fa;
        transform: translateX(2px);
    }
    
    /* 버튼 스타일 */
    .stButton>button {
        margin: 5px 0;
        width: 100%;
        padding: 0.5rem;
        border-radius: 8px;
        background-color: #f0f2f6;
        color: #444;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .stButton>button:hover {
        background-color: #e7f3ff;
        color: #0066cc;
    }
    </style>
""", unsafe_allow_html=True)

# 전역 함수로 이동
def update_week_offset(new_offset):
    st.session_state.selected_week_offset = new_offset
    st.session_state.needs_rerun = True

# show_planner 함수 수정
async def show_planner():
    # 멤버 목록 로드
    members = await safe_api_call(
        lambda: load_members(),
        "멤버 정보 로드 중 오류가 발생했습니다"
    )
    
    if not members:
        st.warning("등록된 멤버가 없습니다. 멤버 관리 메뉴에서 멤버를 추가해주세요.")
        return
    
    # 멤버 선택 - 고유 key 추가
    selected_member = st.sidebar.selectbox(
        "멤버 선택",
        options=[(m['id'], m['name']) for m in members],
        format_func=lambda x: x[1],
        key="planner_member_select"  # 고유 key 추가
    )

    # 현재 사용자 ID 저장
    st.session_state.current_user_id = selected_member[0]
    
    tab1, tab2, tab3 = st.tabs(["📅 공유 달력", "🎯 목표 설정", "📝 학습 일지"])
    
    with tab1:
        await show_shared_calendar(members)  # members 인자 전달
    with tab2:
        await show_goal_setting(selected_member)
    with tab3:
        await show_study_notes(selected_member)


# 캐시된 데이터 로딩 함수
async def load_members():
    return await st.session_state.state_manager.members_cache.get_or_set(
        'members',
        st.session_state.state_manager.api_client.fetch_members
    )

async def load_goals(member_id: int):
    return await st.session_state.state_manager.goals_cache.get_or_set(
        f'goals_{member_id}',
        lambda: st.session_state.state_manager.api_client.fetch_goals(member_id)
    )

async def show_member_management():
    st.subheader("멤버 관리")
    
    # 멤버 추가 폼
    with st.form("add_member_form"):
        st.write("새 멤버 추가")
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("이름")
        with col2:
            email = st.text_input("이메일")
        
        if st.form_submit_button("멤버 추가"):
            if name and email:
                try:
                    result = await st.session_state.state_manager.api_client.add_member(name, email)
                    if result.get("status") == "success":
                        st.success(f"멤버 {name}님이 추가되었습니다!")
                        st.session_state.state_manager.members_cache.cache.clear()
                        time.sleep(0.1)  # 짧은 지연 추가
                        st.rerun()
                    else:
                        st.error("멤버 추가 실패: " + result.get("message", "알 수 없는 오류"))
                except Exception as e:
                    st.error(f"멤버 추가 중 오류가 발생했습니다: {str(e)}")
    
    # 현재 멤버 목록 표시
    st.subheader("현재 멤버 목록")
    try:
        members = await st.session_state.state_manager.api_client.fetch_members()
        
        if members:
            for member in members:
                col1, col2, col3 = st.columns([3,2,1])
                with col1:
                    st.write(f"👤 {member['name']}")
                with col2:
                    st.write(member['email'])
                with col3:
                    if st.button("삭제", key=f"del_{member['id']}"):
                        try:
                            result = await st.session_state.state_manager.api_client.delete_member(member['id'])
                            if result.get("status") == "success":
                                st.success(f"멤버가 삭제되었습니다.")
                                st.session_state.state_manager.members_cache.cache.clear()
                                time.sleep(0.1)  # 짧은 지연 추가
                                st.rerun()
                            else:
                                st.error("멤버 삭제 실패: " + result.get("message", "알 수 없는 오류"))
                        except Exception as e:
                            st.error(f"멤버 삭제 중 오류가 발생했습니다: {str(e)}")
        else:
            st.info("등록된 멤버가 없습니다.")
    except Exception as e:
        st.error(f"멤버 목록 조회 중 오류가 발생했습니다: {str(e)}")

async def show_shared_calendar(members: List[dict]):
    st.markdown("<h3>📅 공유 달력</h3>", unsafe_allow_html=True)
    
    # 현재 날짜 정보
    today = datetime.now()
    
    # 달력 네비게이션
    col1, col2, col3 = st.columns([1,3,1])
    
    with col1:
        if st.button("◀", key="prev_month"):
            if 'selected_month' in st.session_state:
                year = st.session_state.selected_year
                month = st.session_state.selected_month - 1
                if month < 1:
                    month = 12
                    year -= 1
                st.session_state.selected_month = month
                st.session_state.selected_year = year
    
    with col2:
        if 'selected_month' not in st.session_state:
            st.session_state.selected_month = today.month
        if 'selected_year' not in st.session_state:
            st.session_state.selected_year = today.year
            
        selected_date = f"{st.session_state.selected_year}년 {st.session_state.selected_month}월"
        st.markdown(f"<h4 style='text-align: center;'>{selected_date}</h4>", unsafe_allow_html=True)
    
    with col3:
        if st.button("▶", key="next_month"):
            if 'selected_month' in st.session_state:
                year = st.session_state.selected_year
                month = st.session_state.selected_month + 1
                if month > 12:
                    month = 1
                    year += 1
                st.session_state.selected_month = month
                st.session_state.selected_year = year
    
    # 모든 멤버의 목표 로드
    all_goals = {}
    for member in members:
        goals = await load_goals(member['id'])
        all_goals[member['id']] = goals
    
    # 달력 생성 부분 수정
    month_calendar = calendar.monthcalendar(st.session_state.selected_year, st.session_state.selected_month)

    
    # 달력 스타일 추가
    st.markdown("""
        <style>
            /* 달력 테이블 스타일 */
            .calendar-table {
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 20px;
            }
            
            /* 달력 헤더 스타일 */
            .calendar-table th {
                background-color: #f8f9fa;
                padding: 10px;
                text-align: center;
                border: 1px solid #dee2e6;
            }
            
            /* 달력 셀 스타일 */
            .calendar-table td {
                height: 100px;
                width: 14.28%;
                vertical-align: top;
                padding: 5px;
                border: 1px solid #dee2e6;
            }
            
            /* 날짜 스타일 */
            .date-number {
                font-size: 14px;
                margin-bottom: 5px;
            }
            
            /* 토요일 스타일 */
            .saturday {
                color: blue;
            }
            
            /* 일요일 스타일 */
            .sunday {
                color: red;
            }
            
            /* 오늘 날짜 스타일 */
            .today {
                background-color: #fff3cd;
            }
            
            /* 목표가 있는 날짜 스타일 */
            .has-goals {
                background-color: #e8f4f8;
            }
            
            /* 목표 표시 점 스타일 */
            .goal-dot {
                width: 8px;
                height: 8px;
                border-radius: 50%;
                display: inline-block;
                margin: 2px;
            }
        /* 다른 월의 날짜 스타일 */
        .other-month {
            color: #ccc;
            background-color: #f8f9fa;
        }
        
        /* 목표 컨테이너 스타일 */
        .goals-container {
            margin-top: 5px;
            font-size: 12px;
        }
        
        /* 목표 항목 스타일 */
        .goal-item {
            margin: 2px 0;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
    </style>
""", unsafe_allow_html=True)

    # 달력 테이블 생성 부분 수정
    calendar_html = """
        <table class='calendar-table'>
            <tr>
                <th>월</th>
                <th>화</th>
                <th>수</th>
                <th>목</th>
                <th>금</th>
                <th class='saturday'>토</th>
                <th class='sunday'>일</th>
            </tr>
    """
    
    # 각 주차별 처리
    for week in month_calendar:
        calendar_html += "<tr>"
        for i, day in enumerate(week):
            if day == 0:
                # 이전/다음 달의 날짜
                calendar_html += "<td class='other-month'></td>"
            else:
                # 현재 날짜 생성
                current_date = datetime(st.session_state.selected_year, 
                                     st.session_state.selected_month, 
                                     day)
                date_str = current_date.strftime('%Y-%m-%d')
                
                # 클래스 설정
                classes = []
                if current_date.date() == datetime.now().date():
                    classes.append('today')
                if i == 5:  # 토요일
                    classes.append('saturday')
                if i == 6:  # 일요일
                    classes.append('sunday')
                
                # 해당 날짜의 목표 수집
                date_goals = []
                for member_id, goals in all_goals.items():
                    member_goals = [g for g in goals if g['target_date'] == date_str]
                    if member_goals:
                        member_name = next(m['name'] for m in members if m['id'] == member_id)
                        date_goals.extend([(member_name, g) for g in member_goals])
                
                if date_goals:
                    classes.append('has-goals')
                
                class_str = ' '.join(classes)
                
                # 셀 내용 생성
                cell_content = f"<div class='date-number'>{day}</div>"
                if date_goals:
                    cell_content += "<div class='goals-container'>"
                    for member_name, goal in date_goals[:3]:
                        status = "✅" if goal['is_completed'] else "⬜"
                        cell_content += f"<div class='goal-item' style='font-size: 14px;'>{status} <strong>{member_name}</strong></div>"  # 크기 및 스타일 수정
                    if len(date_goals) > 3:
                        cell_content += f"<div class='goal-item'>+{len(date_goals)-3}개 더보기</div>"
                    cell_content += "</div>"
                
                calendar_html += f"<td class='{class_str}'>{cell_content}</td>"
        
        calendar_html += "</tr>"
    
    calendar_html += "</table>"
    
    # 달력 렌더링
    st.markdown(calendar_html, unsafe_allow_html=True)

    # 주간 스터디 진행 상황
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    
    # 탭 생성
    progress_tab1, progress_tab2 = st.tabs(["📊 주간 진행 상황", "📈 월간 진행 상황"])
    with progress_tab1:
        st.subheader("📊 이번 주 스터디 진행 상황")

        # 이번주의 시작일과 종료일 계산
        today = datetime.now().date()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        for member in members:
            if member['id'] in all_goals:
                # 이번주 목표들 필터링
                week_goals = [
                    goal for goal in all_goals[member['id']]
                    if week_start <= datetime.strptime(goal['target_date'], '%Y-%m-%d').date() <= week_end
                ]
                await display_progress(member, week_goals, get_member_color(member['id']))
    with progress_tab2:
        st.subheader("📈 이번 달 스터디 진행 상황")

        # 이번달의 시작일과 종료일 계산
        month_start = datetime(st.session_state.selected_year, st.session_state.selected_month, 1).date()
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        for member in members:
            if member['id'] in all_goals:
                # 이번달 목표들 필터링
                month_goals = [
                    goal for goal in all_goals[member['id']]
                    if month_start <= datetime.strptime(goal['target_date'], '%Y-%m-%d').date() <= month_end
                ]
                
                await display_progress(member, month_goals, get_member_color(member['id']))

async def display_progress(member: dict, goals: List[dict], color: str):
    """진행 상황을 표시하는 헬퍼 함수"""
    if goals:
        completed_goals = len([g for g in goals if g['is_completed']])
        total_goals = len(goals)
        progress = completed_goals / total_goals
        percentage = round(progress * 100)  # 퍼센트 계산
        
        # 멤버별 진행 상황 표시
        st.markdown(f"""
            <div style="padding: 10px; margin: 5px 0; border-left: 3px solid {color};">
                <div style="margin-bottom: 5px;">
                    <span style="font-weight: bold; font-size: 1.2em;">{member['name']}</span>
                    <span style="color: #666; font-size: 1.1em;"> 
                        ({completed_goals}/{total_goals} 완료 - {percentage}%)
                    </span>
                </div>
                <div style="max-height: 150px; overflow-y: auto;">
                    <ul style="font-size: 1.1em;">
                        {''.join(f"<li>{goal['target_date']} ({['월', '화', '수', '목', '금', '토', '일'][datetime.strptime(goal['target_date'], '%Y-%m-%d').weekday()]}) - {goal['title']} - {'✅' if goal['is_completed'] else '⬜'}</li>" for goal in goals)}
                    </ul>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # 프로그레스 바
        st.progress(progress)
    else:
        # 목표가 없는 경우
        st.markdown(f"""
            <div style="padding: 10px; margin: 5px 0; border-left: 3px solid {color};">
                <div style="margin-bottom: 5px;">
                    <span style="font-weight: bold; font-size: 1.2em;">{member['name']}</span>
                    <span style="color: #666; font-size: 1.1em;"> 
                        (목표 없음 - 0%)
                    </span>
                </div>
            </div>
        """, unsafe_allow_html=True)
        st.progress(0.0)

async def show_goal_setting(selected_member):
    st.markdown("<h3>🎯 목표 설정</h3>", unsafe_allow_html=True)
    # CSS 스타일 추가
    st.markdown("""
        <style>
            .goals-table {
                width: 100%;
                border-collapse: collapse;
            }
            .goal-row {
                border-bottom: 1px solid #ddd;
            }
            .goal-row td {
                padding: 8px;
                font-size: 14px;  /* 목표 내용과 날짜의 폰트 크기 조정 */
            }
            .goal-button {
                padding: 5px 8px;  /* 버튼의 패딩 조정 */
                font-size: 12px;  /* 버튼의 폰트 크기 조정 */
                cursor: pointer;
                border: none;  /* 버튼 테두리 제거 */
                background-color: #f0f0f0;  /* 버튼 배경색 */
                border-radius: 4px;  /* 버튼 모서리 둥글게 */
            }
            .goal-button:hover {
                background-color: #e0e0e0;  /* 버튼 호버 시 배경색 변경 */
            }
        </style>
    """, unsafe_allow_html=True)

    # 목표 추가 폼
    st.write("새 목표 추가")
    goal_title = st.text_input("목표 내용")
    
    # 달력에서 날짜 선택
    selected_date_range = st.date_input("목표를 설정할 날짜 선택", [], help="목표를 설정할 날짜를 선택하세요", key="goal_date_range")

    # 선택된 날짜 범위에서 요일 선택
    if selected_date_range:
        start_date, end_date = selected_date_range[0], selected_date_range[-1]
        date_list = [start_date + timedelta(days=x) for x in range((end_date - start_date).days + 1)]
        selected_dates = [date for date in date_list if st.checkbox(f"{date.strftime('%Y-%m-%d')} ({['월', '화', '수', '목', '금', '토', '일'][date.weekday()]})", key=f"checkbox_{date}")]
    else:
        selected_dates = []

    # 선택된 날짜 표시
    if selected_dates:
        st.write(f"선택된 날짜: {', '.join([date.strftime('%Y-%m-%d') for date in selected_dates])}")
    else:
        st.write("선택된 날짜가 없습니다.")

    # 목표 추가 폼
    with st.form("add_goal_form"):
        # 제출 버튼 추가
        submitted = st.form_submit_button("목표 추가", on_click=lambda: st.session_state.update({"goal_dates": selected_dates}))

    if submitted:
        if goal_title and selected_dates:
            success_count = 0
            for date in selected_dates:
                result = await safe_api_call(
                    lambda: st.session_state.state_manager.api_client.add_goal(
                        selected_member[0],
                        goal_title,
                        date
                    ),
                    "목표 추가 중 오류가 발생했습니다"
                )
                if result and result.get("status") == "success":
                    success_count += 1
            
            if success_count > 0:
                st.success(f"새로운 목표 {success_count}개가 추가되었습니다!")
                st.session_state.state_manager.goals_cache.clear()
                time.sleep(0.1)
                st.rerun()
            else:
                st.warning("선택된 날짜에 해당하는 목표가 없습니다.")
        else:
            st.error("목표 내용과 날짜를 모두 입력해주세요.")

    # 현재 목표 목록 표시
    st.markdown("<div class='section-divider'>", unsafe_allow_html=True)
    st.markdown("<h3>📋 현재 목표 목록</h3>", unsafe_allow_html=True)

    goals = await safe_api_call(
        lambda: load_goals(selected_member[0]),
        "목표 목록 로드 중 오류가 발생했습니다"
    )
    if goals:
        today = datetime.now()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)

        weekly_goals = [
            goal for goal in goals 
            if start_of_week.date() <= datetime.strptime(goal['target_date'], '%Y-%m-%d').date() <= end_of_week.date()
        ]
        if weekly_goals:
            for goal in weekly_goals:
                goal_date = datetime.strptime(goal['target_date'], '%Y-%m-%d')
                weekday = ['월', '화', '수', '목', '금', '토', '일'][goal_date.weekday()]
                
                st.markdown(f"""
                    <div class='goal-card {"completed" if goal["is_completed"] else ""}'>
                        <h4>{"✅" if goal["is_completed"] else "⬜"} {goal["target_date"]} ({weekday})</h4>
                        <p>{goal["title"]}</p>
                    </div>
                """, unsafe_allow_html=True)

                # 목표 상태 변경 버튼
                if st.button(f"상태 변경", key=f"toggle_{goal['id']}"):
                    new_status = not goal["is_completed"]
                    result = await safe_api_call(
                        lambda: st.session_state.state_manager.api_client.toggle_goal_complete(goal['id']),
                        "목표 상태 변경 중 오류가 발생했습니다"
                    )
                    if result and result.get("status") == "success":
                        st.success("목표 상태가 변경되었습니다.")
                        st.session_state.state_manager.goals_cache.clear()
                        time.sleep(0.1)
                        st.rerun()
                    else:
                        st.error("목표 상태 변경 실패: " + result.get("message", "알 수 없는 오류"))

                # 목표 삭제 버튼
                if st.button(f"삭제", key=f"delete_{goal['id']}"):
                    result = await safe_api_call(
                        lambda: st.session_state.state_manager.api_client.delete_goal(goal['id']),
                        "목표 삭제 중 오류가 발생했습니다"
                    )
                    if result and result.get("status") == "success":
                        st.success("목표가 삭제되었습니다.")
                        st.session_state.state_manager.goals_cache.clear()
                        time.sleep(0.1)
                        st.rerun()
                    else:
                        st.error("목표 삭제 실패: " + result.get("message", "알 수 없는 오류"))
        else:
            st.info("이번 주에 등록된 목표가 없습니다.")
    else:
        st.info("등록된 목표가 없습니다.")
    


async def show_study_notes(selected_member):
    st.markdown("<h3>📝 학습 일지</h3>", unsafe_allow_html=True)
    

    goals = await safe_api_call(
        lambda: load_goals(selected_member[0]),
        "목표 목록 로드 중 오류가 발생했습니다"
    )
    
    if goals:
        for goal in goals:
            goal_date = datetime.strptime(goal['target_date'], '%Y-%m-%d')
            weekday = ['월', '화', '수', '목', '금', '토', '일'][goal_date.weekday()]
            
            st.markdown(f"""
                <div class='goal-card {"completed" if goal["is_completed"] else ""}'>
                    <h4>{"✅" if goal["is_completed"] else "⬜"} {goal["target_date"]} ({weekday})</h4>
                    <p>{goal["title"]}</p>
                </div>
            """, unsafe_allow_html=True)

            # 노트 조회 및 처리 부분 수정
            note_result = await safe_api_call(
            lambda: st.session_state.state_manager.api_client.get_study_note(goal['id']),
            "노트 조회 중 오류가 발생했습니다"
        )

            note_content = ""
            if note_result and note_result.get("status") == "success":
                note_data = note_result.get("data").get("data")
                if note_data:
                        note_content = note_data.get("content", "")

            # 본인의 노트인 경우 편집 가능
            if selected_member[0] == st.session_state.current_user_id:
                with st.expander("학습 노트 작성", expanded=not note_content):
                    new_content = st.text_area(
                        "학습 내용",
                        value=note_content,
                        height=150,
                        key=f"note_{goal['id']}"
                    )

                    if st.button("저장", key=f"save_note_{goal['id']}"):
                        result = await safe_api_call(
                            lambda: st.session_state.state_manager.api_client.save_study_note(
                                goal['id'],
                                selected_member[0],
                                goal['target_date'],
                                new_content
                            ),
                            "노트 저장 중 오류가 발생했습니다"
                        )
                        if result and result.get("status") == "success":
                            st.success("학습 내용이 저장되었습니다.")
                            time.sleep(0.1)
                            st.rerun()
            else:
                # 다른 사람의 노트는 읽기 전용
                if note_content:
                    with st.expander("학습 노트 보기", expanded=False):
                        st.markdown(note_content)
                else:
                    st.info("작성된 학습 내용이 없습니다.")
    else:
        st.info("등록된 목표가 없습니다.")


async def main():
    st.title("스터디 플래너 📚")
    
    menu = st.sidebar.selectbox(
        "메뉴 선택",
        ["플래너", "멤버 관리"]
    )
    
    try:
        if menu == "플래너":
            await show_planner()
        else:
            await show_member_management()
    except Exception as e:
        st.error(f"오류가 발생했습니다: {str(e)}")
    finally:
        await st.session_state.state_manager.cleanup()

if __name__ == "__main__":
    # 기존의 asyncio.run() 대신 이벤트 루프를 직접 생성
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    finally:
        loop.close()