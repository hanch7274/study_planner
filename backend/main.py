from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import date
import uvicorn
from database import (
    init_db,
    get_all_members,
    get_member_goals,
    add_new_goal,
    add_new_member,
    delete_member,
    mark_goal_complete,
    toggle_goal_complete,
    delete_goal,
)
from database import (
    get_study_note, save_study_note, get_weekly_notes,
    delete_study_note, get_user_notes_count
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.staticfiles import StaticFiles
import subprocess

# 새로운 Pydantic 모델 추가
class StudyNoteCreate(BaseModel):
    goal_id: int
    user_id: int
    note_date: date
    content: str

class DateRange(BaseModel):
    start_date: date
    end_date: date

app = FastAPI()
# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Streamlit 앱 실행을 위한 함수
def run_streamlit():
    streamlit_cmd = [
        "streamlit", "run", 
        "../frontend/app.py",
        "--server.port", "8501",
        "--server.address", "localhost"
    ]
    return subprocess.Popen(streamlit_cmd)

# 서버 시작 시 Streamlit 실행
streamlit_process = None


@app.on_event("startup")
async def startup_event():
    global streamlit_process
    streamlit_process = run_streamlit()

@app.on_event("shutdown")
async def shutdown_event():
    if streamlit_process:
        streamlit_process.terminate()


class Goal(BaseModel):
    title: str
    target_date: date
    user_id: int

class Member(BaseModel):
    name: str
    email: str

@app.get("/members")
async def read_members():
    return await get_all_members()

@app.get("/goals/{member_id}")
async def read_goals(member_id: int):
    return await get_member_goals(member_id)

@app.post("/goals")
async def create_goal(goal: Goal):
    return await add_new_goal(goal.user_id, goal.title, goal.target_date)

@app.put("/goals/{goal_id}")
async def complete_goal(goal_id: int):
    return await mark_goal_complete(goal_id)

@app.post("/members")
async def create_member(member: Member):
    return await add_new_member(member.name, member.email)

@app.delete("/members/{member_id}")
async def remove_member(member_id: int):
    return await delete_member(member_id)

@app.put("/goals/{goal_id}/toggle")
async def toggle_goal(goal_id: int):
    return await toggle_goal_complete(goal_id)

@app.delete("/goals/{goal_id}")
async def delete_goal_endpoint(goal_id: int):
    result = await delete_goal(goal_id)
    if result["status"] == "error":
        raise HTTPException(status_code=404, detail=result["message"])
    return result

# 노트 관련 엔드포인트 수정
@app.get("/goals/{goal_id}/notes")
async def get_note(goal_id: int):
    """특정 목표의 학습 노트 조회"""
    note = await get_study_note(goal_id)
    if note is None:
        return {"status": "success", "data": None}
    return {"status": "success", "data": note}

@app.post("/goals/{goal_id}/notes")
async def create_note(goal_id: int, note: StudyNoteCreate):
    """학습 노트 생성 또는 업데이트"""
    try:
        result = await save_study_note(
            goal_id,
            note.user_id,
            note.note_date,
            note.content
        )
        return {"status": "success", "message": "Note saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users/{user_id}/notes/weekly")
async def get_notes_by_week(
    user_id: int,
    start_date: date,
    end_date: date
):
    """주간 학습 노트 목록 조회"""
    try:
        notes = await get_weekly_notes(user_id, start_date, end_date)
        return {"status": "success", "data": notes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/goals/{goal_id}/notes")
async def delete_note(goal_id: int, user_id: int):
    """학습 노트 삭제"""
    try:
        result = await delete_study_note(goal_id, user_id)
        return {"status": "success", "message": "Note deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users/{user_id}/notes/stats")
async def get_notes_stats(
    user_id: int,
    start_date: date,
    end_date: date
):
    """사용자의 노트 통계 조회"""
    try:
        stats = await get_user_notes_count(user_id, start_date, end_date)
        return {"status": "success", "data": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    # 백엔드 서버 실행
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )