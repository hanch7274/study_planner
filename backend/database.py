import aiosqlite
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, String, Boolean, Date, ForeignKey
from datetime import date


async def init_db():
    async with aiosqlite.connect('planner.db') as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users
            (id INTEGER PRIMARY KEY, name TEXT, email TEXT UNIQUE)
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS goals
            (id INTEGER PRIMARY KEY,
             user_id INTEGER,
             title TEXT,
             target_date DATE,
             is_completed BOOLEAN,
             FOREIGN KEY (user_id) REFERENCES users (id))
        ''')
        # study_notes 테이블 추가
        await db.execute('''
            CREATE TABLE IF NOT EXISTS study_notes
            (id INTEGER PRIMARY KEY,
             user_id INTEGER,
             goal_id INTEGER,
             note_date DATE,
             content TEXT,
             created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
             updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
             FOREIGN KEY (user_id) REFERENCES users (id),
             FOREIGN KEY (goal_id) REFERENCES goals (id))
        ''')
        await db.commit()

async def get_all_members():
    async with aiosqlite.connect('planner.db') as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users") as cursor:
            return await cursor.fetchall()

async def get_member_goals(member_id: int):
    async with aiosqlite.connect('planner.db') as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM goals WHERE user_id = ?", 
            (member_id,)
        ) as cursor:
            return await cursor.fetchall()

async def add_new_goal(user_id: int, title: str, target_date: date):
    async with aiosqlite.connect('planner.db') as db:
        await db.execute(
            """INSERT INTO goals (user_id, title, target_date, is_completed)
               VALUES (?, ?, ?, ?)""",
            (user_id, title, target_date, False)
        )
        await db.commit()
        return {"status": "success"}

async def add_new_member(name: str, email: str):
    async with aiosqlite.connect('planner.db') as db:
        try:
            await db.execute(
                "INSERT INTO users (name, email) VALUES (?, ?)",
                (name, email)
            )
            await db.commit()
            return {"status": "success"}
        except aiosqlite.IntegrityError:
            return {"status": "error", "message": "Email already exists"}

async def delete_member(member_id: int):
    async with aiosqlite.connect('planner.db') as db:
        await db.execute("DELETE FROM goals WHERE user_id = ?", (member_id,))
        await db.execute("DELETE FROM users WHERE id = ?", (member_id,))
        await db.commit()
        return {"status": "success"}

async def mark_goal_complete(goal_id: int):
    async with aiosqlite.connect('planner.db') as db:
        await db.execute(
            "UPDATE goals SET is_completed = TRUE WHERE id = ?",
            (goal_id,)
        )
        await db.commit()
        return {"status": "success"}
    
async def toggle_goal_complete(goal_id: int):
    async with aiosqlite.connect('planner.db') as db:
        # 현재 상태 확인
        async with db.execute(
            "SELECT is_completed FROM goals WHERE id = ?",
            (goal_id,)
        ) as cursor:
            result = await cursor.fetchone()
            if result is None:
                return {"status": "error", "message": "Goal not found"}
            current_state = result[0]
        
        # 상태 토글
        await db.execute(
            "UPDATE goals SET is_completed = ? WHERE id = ?",
            (not current_state, goal_id)
        )
        await db.commit()
        return {"status": "success", "is_completed": not current_state}
    
async def delete_goal(goal_id: int):
    async with aiosqlite.connect('planner.db') as db:
        # 목표 존재 여부 확인
        async with db.execute(
            "SELECT id FROM goals WHERE id = ?",
            (goal_id,)
        ) as cursor:
            if not await cursor.fetchone():
                return {"status": "error", "message": "Goal not found"}
        
        # 목표 삭제
        await db.execute(
            "DELETE FROM goals WHERE id = ?",
            (goal_id,)
        )
        await db.commit()
        return {"status": "success", "message": "Goal deleted successfully"}

# 학습 노트 관련 함수들 추가
async def get_study_note(goal_id: int):
    """특정 목표에 대한 학습 노트 조회"""
    async with aiosqlite.connect('planner.db') as db:
        db.row_factory = aiosqlite.Row
        try:
            async with db.execute(
                """SELECT * FROM study_notes 
                   WHERE goal_id = ? 
                   ORDER BY updated_at DESC 
                   LIMIT 1""",
                (goal_id,)
            ) as cursor:
                note = await cursor.fetchone()
                
                if note:
                    return {
                        "status": "success",
                        "data": dict(note)
                    }
                return {
                    "status": "success",
                    "data": None
                }
        except Exception as e:
            print(f"Error in get_study_note: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "data": None
            }

async def save_study_note(goal_id: int, user_id: int, note_date: date, content: str):
    """학습 노트 저장 또는 업데이트"""
    async with aiosqlite.connect('planner.db') as db:
        try:
            # 기존 노트 확인
            async with db.execute(
                "SELECT id FROM study_notes WHERE goal_id = ?",
                (goal_id,)
            ) as cursor:
                existing_note = await cursor.fetchone()
            
            if existing_note:
                # 기존 노트 업데이트
                await db.execute("""
                    UPDATE study_notes 
                    SET content = ?, updated_at = CURRENT_TIMESTAMP 
                    WHERE goal_id = ?
                """, (content, goal_id))
            else:
                # 새 노트 생성
                await db.execute("""
                    INSERT INTO study_notes 
                    (goal_id, user_id, note_date, content) 
                    VALUES (?, ?, ?, ?)
                """, (goal_id, user_id, note_date, content))
            
            await db.commit()
            return {"status": "success", "message": "Note saved successfully"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

async def get_weekly_notes(user_id: int, start_date: date, end_date: date):
    """특정 기간의 학습 노트 목록 조회"""
    async with aiosqlite.connect('planner.db') as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT n.*, g.title as goal_title 
               FROM study_notes n 
               JOIN goals g ON n.goal_id = g.id 
               WHERE n.user_id = ? AND n.note_date BETWEEN ? AND ?
               ORDER BY n.note_date DESC""",
            (user_id, start_date, end_date)
        ) as cursor:
            notes = await cursor.fetchall()
            return {
                "status": "success",
                "data": [dict(row) for row in notes]
            }

async def delete_study_note(goal_id: int, user_id: int):
    """학습 노트 삭제 (본인 것만 삭제 가능)"""
    async with aiosqlite.connect('planner.db') as db:
        try:
            await db.execute(
                "DELETE FROM study_notes WHERE goal_id = ? AND user_id = ?",
                (goal_id, user_id)
            )
            await db.commit()
            return {"status": "success", "message": "Note deleted successfully"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

async def get_user_notes_count(user_id: int, start_date: date, end_date: date):
    """특정 기간 동안의 사용자 노트 통계"""
    async with aiosqlite.connect('planner.db') as db:
        try:
            async with db.execute(
                """SELECT COUNT(*) as total_notes,
                   SUM(CASE WHEN content != '' AND content IS NOT NULL THEN 1 ELSE 0 END) as completed_notes
                   FROM study_notes
                   WHERE user_id = ? AND note_date BETWEEN ? AND ?""",
                (user_id, start_date, end_date)
            ) as cursor:
                result = await cursor.fetchone()
                return {
                    "status": "success",
                    "data": {
                        "total_notes": result[0],
                        "completed_notes": result[1] or 0
                    }
                }
        except Exception as e:
            return {"status": "error", "message": str(e)}