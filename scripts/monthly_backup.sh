#!/bin/bash

BACKUP_DIR=/home/yuri/backups
DATE=$(date +%Y-%m-%d_%H-%M)

# 1. Дамп БД
docker exec pass_db pg_dump -U pomor_admin pass_system_db > $BACKUP_DIR/pass_system_db_$DATE.sql

# 2. Архив всего проекта (без db_data)
cd /opt && tar -czf $BACKUP_DIR/pass_system_full_$DATE.tar.gz --exclude=pass-system/db_data pass-system/

# 3. Отправка на почту через mpack
mpack -s "Ежемесячный полный бэкап pass-system от $(date +%Y-%m-%d)" -c application/gzip $BACKUP_DIR/pass_system_full_$DATE.tar.gz test@zymk.ru

# 4. Удаляем локальные файлы бэкапа
rm -f $BACKUP_DIR/pass_system_full_$DATE.tar.gz
rm -f $BACKUP_DIR/pass_system_db_$DATE.sql
