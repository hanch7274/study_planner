import sqlite3
import asyncio
import aiosqlite

async def migrate_data():
    # 먼저 backup.db에서 데이터 읽기
    with sqlite3.connect('backup.db') as backup_db:
        # users 테이블 데이터 가져오기
        users = backup_db.execute("SELECT * FROM users").fetchall()
        # goals 테이블 데이터 가져오기
        goals = backup_db.execute("SELECT * FROM goals").fetchall()

    # planner.db에 데이터 쓰기
    async with aiosqlite.connect('planner.db') as planner_db:
        # 기존 데이터 삭제
        await planner_db.execute("DELETE FROM goals")
        await planner_db.execute("DELETE FROM users")
        
        # users 테이블 데이터 복사
        for user in users:
            await planner_db.execute(
                "INSERT INTO users (id, name, email) VALUES (?, ?, ?)",
                user
            )
        
        # goals 테이블 데이터 복사
        for goal in goals:
            await planner_db.execute(
                "INSERT INTO goals (id, user_id, title, target_date, is_completed) VALUES (?, ?, ?, ?, ?)",
                goal
            )
        
        await planner_db.commit()
    
    print("데이터 마이그레이션이 완료되었습니다!")

if __name__ == "__main__":
    asyncio.run(migrate_data())