#!/bin/bash

BACKUP_DIR=/home/yuri/backups
DATE=$(date +%Y-%m-%d)
WEEKDAY=$(date +%u)  # 1 = понедельник, 7 = воскресенье

# Создаём дамп БД
docker exec pass_db pg_dump -U pomor_admin pass_system_db > $BACKUP_DIR/pass_system_$DATE.sql

# Если сегодня воскресенье (7) — архивируем все бэкапы за неделю и отправляем
if [ "$WEEKDAY" -eq 7 ]; then
    ARCHIVE_NAME="pass_system_backup_$DATE.tar.gz"
    tar -czf $BACKUP_DIR/$ARCHIVE_NAME -C $BACKUP_DIR pass_system_*.sql
    mutt -s "Еженедельный архив бэкапов БД pass_system от $DATE" -a $BACKUP_DIR/$ARCHIVE_NAME -- test@zymk.ru < /dev/null
    # Удаляем все SQL-бэкапы, кроме последнего (сегодняшнего)
    find $BACKUP_DIR -name "pass_system_*.sql" ! -name "pass_system_$DATE.sql" -delete
fi
