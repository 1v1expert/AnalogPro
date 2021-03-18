from django.core.management.base import BaseCommand

from catalog.file_utils import ProcessingUploadData, XLSDocumentReader

import logging

from time import time, strftime, gmtime

# Get an instance of a logger
logger = logging.getLogger('analog')


class Command(BaseCommand):
    """ Update DataBase"""
    
    def add_arguments(self, parser):
        parser.add_argument(
            "--filename", action="store_true",
        )
    
    def handle(self, *args, **options):
        filename = options["filename"]
        if not filename:
            filename = 'files/North_Aurora(fason).xlsx'

        created, error = ProcessingUploadData(
            XLSDocumentReader(path=filename).parse_file()).get_structured_data(only_check=False)
        
        if created:
            self.stdout.write(f'File {filename} is upload success')
        else:
            self.stdout.write(f'Error after process file')



