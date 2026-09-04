#!/bin/bash

BACKUP_DIR=/home/yuri/backups
DATE=$(date +%Y-%m-%d_%H-%M)

# 1. Дамп БД
docker exec pass_db pg_dump -U pomor_admin pass_system_db > $BACKUP_DIR/pass_system_db_$DATE.sql

# 2. Архив всего проекта (с БД)
cd /opt && tar -czf $BACKUP_DIR/pass_system_full_$DATE.tar.gz pass-system/ 2>/dev/null

# 3. Отправка на почту
mutt -s "Ежемесячный полный бэкап pass-system от $(date +%Y-%m-%d)" \
     -a $BACKUP_DIR/pass_system_full_$DATE.tar.gz \
     -a $BACKUP_DIR/pass_system_db_$DATE.sql \
     -- test@zymk.ru < /dev/null

# 4. Удаляем локальные файлы бэкапа (оставляем только отправленный архив)
rm -f $BACKUP_DIR/pass_system_full_$DATE.tar.gz
rm -f $BACKUP_DIR/pass_system_db_$DATE.sql
