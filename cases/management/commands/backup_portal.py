from pathlib import Path
import tempfile
from zipfile import ZipFile, ZIP_DEFLATED
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from config.backups import snapshot_database


class Command(BaseCommand):
    help = 'Create a consistent SQLite snapshot and evidence archive for scheduled backups.'

    def add_arguments(self, parser):
        parser.add_argument('--directory', default=str(settings.BASE_DIR / 'backups'))

    def handle(self, *args, **options):
        directory = Path(options['directory']).resolve()
        directory.mkdir(parents=True, exist_ok=True)
        destination = directory / ('fmsc-' + timezone.now().strftime('%Y%m%d-%H%M%S-%f') + '.zip')
        with tempfile.TemporaryDirectory() as temporary:
            database = Path(temporary) / 'db.sqlite3'
            snapshot_database(database)
            with ZipFile(destination, 'x', ZIP_DEFLATED) as archive:
                archive.write(database, 'db.sqlite3')
                media = Path(settings.MEDIA_ROOT)
                if media.exists():
                    for file in media.rglob('*'):
                        if file.is_file() and file.name != '.gitkeep':
                            archive.write(file, 'media/' + file.relative_to(media).as_posix())
        self.stdout.write(self.style.SUCCESS(f'Backup saved: {destination}'))
