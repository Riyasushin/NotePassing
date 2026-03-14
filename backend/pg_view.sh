#!/bin/bash
# PostgreSQL 数据查看工具 - 无需停止应用

DB_CONTAINER="notepassing-db"
DB_USER="notepassing"
DB_NAME="notepassing"

# 检查容器是否运行
if ! docker ps | grep -q "$DB_CONTAINER"; then
    echo "❌ 数据库容器未运行"
    exit 1
fi

# 函数：列出所有表
list_tables() {
    echo "📋 数据库表列表："
    echo "------------------------------"
    docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -t -c "
        SELECT table_name, 
               (SELECT COUNT(*) FROM information_schema.tables t2 
                WHERE t2.table_name = t1.table_name) as cnt
        FROM information_schema.tables t1
        WHERE table_schema = 'public'
        ORDER BY table_name;
    " 2>/dev/null | while read line; do
        table=$(echo "$line" | awk '{print $1}')
        [ -z "$table" ] && continue
        count=$(docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM $table" 2>/dev/null | xargs)
        printf "  • %-30s (%s 行)\n" "$table" "$count"
    done
    echo "------------------------------"
}

# 函数：查看表数据
view_table() {
    local table=$1
    local limit=${2:-20}
    
    echo ""
    echo "📊 表: $table"
    echo ""
    
    # 获取列名
    docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "
        \x off
        SELECT * FROM $table LIMIT $limit;
    " 2>/dev/null
}

# 主逻辑
case "${1:-list}" in
    list|ls|"")
        list_tables
        echo ""
        echo "💡 使用: $0 <表名> [行数]"
        echo "   例如: $0 devices"
        echo "   例如: $0 messages 50"
        ;;
    *)
        view_table "$1" "${2:-20}"
        ;;
esac
