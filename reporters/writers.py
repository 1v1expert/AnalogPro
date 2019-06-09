import xlsxwriter
import csv
from django.conf import settings


class BookkeepingWriter(object):
    def __init__(self, name):
        self.filename = name
    
    def dump_csv(self, data):
        with open('{}/{}'.format(settings.FILES_ROOT, self.filename), 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile, dialect='excel')
            for row in data:
                writer.writerow(row)
                
    def dump_xls(self, data):
        pass
    
    def __enter__(self):
        self._wb = xlsxwriter.Workbook(self.filename,
                                       {'default_date_format': 'dd.mm.yyyy'}
        )
        self._default_ws = self._wb.add_worksheet()
        self._row = 0
        self._col = 0
        self.formats = {
            'top_header': self._wb.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'bold': 1}),
            'formula': self._wb.add_format({
                'align': 'left',
                'valign': 'vcenter'}),
            'table_row': self._wb.add_format({
                'align': 'left',
                'valign': 'vcenter',
                'border': 1})
        }
        return self

    def __exit__(self, _type, value, tb):
        self._wb.close()
