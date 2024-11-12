# 스터디 플래너 (Study Planner)

## 📚 프로젝트 소개
스터디 그룹을 위한 일정 관리 및 진행 상황 추적 웹 애플리케이션입니다. 
멤버들의 학습 목표를 설정하고 진행 상황을 효과적으로 모니터링할 수 있습니다.

## ✨ 주요 기능
- 📅 스터디 일정 캘린더 관리
- 📊 주간/월간 진행 상황 대시보드
- 🎯 멤버별 학습 목표 설정 및 관리
- 👥 멤버별 진행률 시각화
- 🔔 목표 달성 현황 추적

## 🛠 기술 스택
- **Frontend**: Streamlit
- **Backend**: FastAPI
- **Database**: SQLite
- **Language**: Python

## 🚀 설치 방법

1. 저장소 클론
git clone https://github.com/hanch7274/study_planner.git
cd study_planner

2. 가상환경 생성 및 활성화
```
python -m venv venv
source venv/bin/activate # Windows: venv\Scripts\activate
```

3. 필요한 패키지 설치
```
pip install -r requirements.txt
```

4. 실행
```
uvicorn main:app --host 0.0.0.0 --port 8000
```
