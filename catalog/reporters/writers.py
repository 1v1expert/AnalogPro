import csv
from collections import OrderedDict
from datetime import datetime

import xlsxwriter
from django.conf import settings
from django.utils.functional import LazyObject, SimpleLazyObject

from catalog import choices
from catalog.models import DataFile
from catalog.utils import get_or_create_tech_user


class BookkeepingWriter(object):
    def __init__(self, name, user=None):
        self.filename = 'files/{}.xlsx'.format(name)
        # self.filename = name
        self._default_ws = None
        self.user = user or get_or_create_tech_user()
        self._row = 0
        self._col = 0
    
    def create_page(self, name):
        self._row = 0
        self._col = 0
        self._default_ws = self._wb.add_worksheet(name)
    
    def dump(self, books):
        # self.write_top_header(**data['top_header'])
        # for data in book:
        for data in books:
            self.create_page(data['top_header']['name'])
            self.write_table_header(data['table_header'].values())
            # FIXME: make use of `for k in data['table_header']`
            for row in data['table_data']:
                try:
                    if isinstance(row, OrderedDict):
                        self.write_table_row(row.values())
                    elif isinstance(row, tuple):
                        self.write_table_row(row)
                except Exception as e:
                    print(e, row)
    
    def write_top_header(self):
        pass
    
    def write_table_header(self, row):
        base_opts = {'text_wrap': 1, 'align': 'left', 'valign': 'vcenter', 'left': 1, 'right': 1, 'top': 2,
            'bottom': 2, }
        default_format = self._wb.add_format(base_opts)
    
        for col, cell in enumerate(row):
            new_format = None
            if col == 0:
                new_format = self._wb.add_format(base_opts)
                new_format.set_left(2)
            elif col == len(row) - 1:
                new_format = self._wb.add_format(base_opts)
                new_format.set_right(2)
        
            self._default_ws.set_column(col, col, min(15, len(str(cell))))
            self._default_ws.write(self._row, col, str(cell), new_format or default_format)
        
        max_len = max(sorted([len(str(x)) for x in row]))
        self._default_ws.set_row(self._row, (15 * max_len // 15) + 1)
        self._row += 1
    
    def write_table_row(self, row):
        self.writerow(row, self.formats['table_row'])
    
    def writerow(self, row, fmt):
        # TODO: this is way too ugly and must be rewritten.
        for col, item in enumerate(row):
            c_fmt = fmt
            
            if isinstance(item, datetime):
                c_item = item.strftime("%Y-%m-%d-%H.%M.%S")
            elif isinstance(item, (LazyObject, SimpleLazyObject)):
                c_item = '-----'
            else:
                c_item = str(item)

            if col == len(row) - 1:
                c_fmt.set_right(2)
            
            self._default_ws.write(self._row, col, c_item, c_fmt)
        self._row += 1
    
    def __enter__(self):
        self._wb = xlsxwriter.Workbook(self.filename,
                                       {'default_date_format': 'dd.mm.yyyy'}
        )
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

        # from openpyxl.writer.excel import save_virtual_workbook
        # from django.core.files import File
        # myfile = File(self._wb)
        datafile = DataFile(type=choices.TYPES_FILE[3][0], created_by=self.user, updated_by=self.user)
        # self.instance.file.save(self.filename, save_virtual_workbook(self._wb))
        datafile.file.name = self.filename
        datafile.save()

        
class HealthCheckBookkeepingWriter(BookkeepingWriter):
    
    def write_table_header(self, row):
        for col, key in enumerate(row.keys()):
            value: str = f'{row[key]["title"]}'
            if row[key].get("type"):
                value += f'({row[key]["type"]})'
            self._default_ws.write(self._row, row[key]["cell"], value)
            
    def write_position(self, position, number_line, header):
        number_line += 1
        self.write_product(position["initial_product"], header, number_line)
        
        if position["analogs"]["analog"]:
            number_line += 1
            self.write_product(position["analogs"]["analog"], header, number_line, type_record='Приор. аналог')
            
            if position["analogs"]["queryset"]:
                for analog in position["analogs"]["queryset"]:
                    number_line += 1
                    self.write_product(analog, header, number_line, type_record='Проч. аналог')
        else:
            number_line += 1
            self._default_ws.write(number_line, 0, f'Аналог в {position["analogs"].get("manufacturer_to")} не найден')
            
        return number_line + 1
    
    def write_product(self, product, header, number_line, type_record='Исходный продукт'):
        full_info = product.get_attributes()
        for key in full_info.keys():
            attribute = full_info[key]
            
            c_item = str(attribute["un_value"])
            if attribute["attribute__is_fixed"]:
                c_item = str(attribute["value__title"])
            
            self._default_ws.write(number_line, header[attribute["attribute__pk"]]["cell"], c_item)

        self._default_ws.write(number_line, header["title"]["cell"], product.title)
        self._default_ws.write(number_line, header["article"]["cell"], product.article)
        self._default_ws.write(number_line, header["category"]["cell"], product.category.title)
        self._default_ws.write(number_line, header["manufacturer"]["cell"], product.manufacturer.title)
        self._default_ws.write(number_line, header["additional_article"]["cell"], product.additional_article)
        self._default_ws.write(number_line, header["pk"]["cell"], product.pk)
        self._default_ws.write(number_line, 0, type_record)
        
    def dump(self, books):
        for data in books:
            self.create_page(data['top_header']['name'])
            self.write_table_header(data['table_header'])
            line = 2
            for position in data['table_data']:
                line = self.write_position(position, line, data["table_header"])
                
    def write(self):
        pass


def dump_csv(name, data):
    with open('{}/{}'.format(settings.FILES_ROOT, name), 'w', newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file, dialect='excel', delimiter=';')
        for row in data:
            writer.writerow(row)
