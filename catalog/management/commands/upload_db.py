from django.core.management.base import BaseCommand

from catalog.file_utils import SubclassesReader, ProcessingUploadData, XLSDocumentReader
from django.contrib.auth import models as auth_md
import logging
from catalog.models import Category

# from time import time, strftime, gmtime
import time
# Get an instance of a logger
import traceback
logger = logging.getLogger('analog')


class Command(BaseCommand):
    """ Upload DataBase"""
    
    def add_arguments(self, parser):
        parser.add_argument(
            "--filename", action="store_true",
        )
    
    def handle(self, *args, **options):
        filename = options["filename"]
        if not filename:
            filename = 'files/Subclasses.xlsx'

        filename = 'files/Betterman_test.xlsx'
        created, error = ProcessingUploadData(
            XLSDocumentReader(path=filename).parse_file(), start_time=time.time()
        ).get_structured_data()

        if not created:
            self.stdout.write(f'{error}')




