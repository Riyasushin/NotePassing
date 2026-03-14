#!/usr/bin/env python3
"""
PostgreSQL 数据查看工具 - 不停止应用
"""

import asyncio
import os
import sys
from pathlib import Path

# 加载 .env
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key, value)

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = os.getenv("DATABASE_URL", "")
engine = create_async_engine(DATABASE_URL)


async def list_tables():
    """列出所有表"""
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' ORDER BY table_name
        """))
        tables = [r[0] for r in result.fetchall()]
        
        print(f"\n📋 数据库表列表 ({len(tables)} 个):\n")
        print("-" * 40)
        for table in tables:
            count_result = await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = count_result.scalar()
            print(f"  • {table:<30} ({count} 行)")
        print("-" * 40)
        return tables


async def view_table(table_name, limit=20):
    """查看表数据"""
    async with engine.connect() as conn:
        # 获取列名
        result = await conn.execute(text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = :table ORDER BY ordinal_position
        """), {"table": table_name})
        columns = [r[0] for r in result.fetchall()]
        
        if not columns:
            print(f"❌ 表 {table_name} 不存在")
            return
        
        # 获取数据
        result = await conn.execute(text(f"SELECT * FROM {table_name} LIMIT {limit}"))
        rows = result.fetchall()
        
        print(f"\n📊 表: {table_name}")
        print(f"   列: {', '.join(columns)}\n")
        
        if not rows:
            print("   (空表)\n")
            return
        
        # 计算列宽
        widths = [min(max(len(str(c)), 12), 25) for c in columns]
        
        # 表头
        header = " | ".join(f"{columns[i]:<{widths[i]}}" for i in range(len(columns)))
        print("   " + header)
        print("   " + "-" * len(header))
        
        # 数据
        for row in rows:
            vals = []
            for i, v in enumerate(row):
                s = str(v) if v is not None else "NULL"
                s = s[:20] + "..." if len(s) > 23 else s
                vals.append(f"{s:<{widths[i]}}")
            print("   " + " | ".join(vals))
        print()


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="查看 PostgreSQL 数据")
    parser.add_argument("table", nargs="?", help="表名")
    parser.add_argument("-n", "--limit", type=int, default=20)
    parser.add_argument("-a", "--all", action="store_true", help="显示所有表")
    args = parser.parse_args()
    
    try:
        if args.all:
            tables = await list_tables()
            print()
            for table in tables:
                await view_table(table, args.limit)
        elif args.table:
            await view_table(args.table, args.limit)
        else:
            await list_tables()
            print("\n💡 使用: python view_pg.py <表名>")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
