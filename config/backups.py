from contextlib import closing
import sqlite3
from django.conf import settings
from django.db import connection


def snapshot_database(destination):
    if connection.vendor != 'sqlite':
        raise ValueError('This backup helper requires SQLite.')
    source_name = str(settings.DATABASES['default']['NAME'])
    with closing(sqlite3.connect(source_name, uri=True)) as source:
        with closing(sqlite3.connect(str(destination))) as target:
            source.backup(target)
