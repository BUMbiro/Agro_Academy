"""check_db.py — быстрая диагностика подключения к PostgreSQL."""
import psycopg

from config.settings import DATABASES

cfg = DATABASES['default']
base = {
    'host': cfg['HOST'],
    'port': cfg['PORT'],
    'user': cfg['USER'],
    'password': cfg['PASSWORD'],
    'connect_timeout': 5,
}


def try_connect(dbname):
    try:
        with psycopg.connect(dbname=dbname, **base) as conn:
            version, encoding = conn.execute(
                'SELECT version(), current_setting(\'server_encoding\')'
            ).fetchone()
        print(f'  [OK]   {dbname}: подключение есть')
        print(f'         {version.split(",")[0]} | server_encoding={encoding}')
        return True
    except psycopg.Error as exc:
        print(f'  [FAIL] {dbname}: {exc}')
        return False


print(f'host={base["host"]} port={base["port"]} user={base["user"]} '
      f'password={"*" * len(base["password"] or "")}')
print('1) Служебная база postgres (проверяет сервер, логин и пароль):')
server_ok = try_connect('postgres')

if server_ok:
    print(f'2) Рабочая база {cfg["NAME"]} (проверяет, создана ли она):')
    try_connect(cfg["NAME"])
else:
    print('   Рабочую базу не проверяю: сначала нужно оживить сервер/логин.')
