import openpyxl
from collections import OrderedDict

from catalog.choices import *
from catalog.models import *

from django.contrib import messages
from django.db import models


class XLSDocumentReader(object):
    
    def __init__(self, path=None, workbook=None):
        assert path or workbook, "You should provide either path to file or XLS-object"

        if workbook:
            self.workbook = workbook
        else:
            self.workbook = openpyxl.load_workbook(path,
                                                   read_only=True,
                                                   data_only=True)
        self.xlsx = path
        self.ws = self.workbook.active
        self.sheet = self.workbook.active
        self.errors = {}
        self.all_errors = {}
        self.document = {}
        self.attributes = {}
        self.options = {}
        self.values = []
        self.doc = []
        
    def parse_file(self):
        rows = self.sheet.rows
        for cnt, row in enumerate(rows):
            line = {}
            for cnt_c, cell in enumerate(row):
                if cell.value:
                    line.update({cnt_c: str(cell.value)})
            self.doc.append(line)
            
        self.workbook._archive.close()
        return self.doc
        

class ProcessingUploadData(object):
    """Класс преобразования считанных данных из загружаемого файла
    products = [product1, product2, ...]
    product = {
        name: name,
        class: class,
        subclass: subclass,
        series: series,
        article: article,
        additional_article: additional_article,
        manufacturer: manufacturer,
        attributes: [attr1, attr2, ...]
    }
    attribute = {
        type: type.
        value: value,
        name: name
    }
    """
    
    def __init__(self, data):
        self.ATTRIBUTE_LINE = 1
        self.OPTION_LINE = 3
        
        self.data = data
        self.attributes = []
        self.options = []
        self.body = []

        self.unique_manufacturer, self.unique_class, self.unique_subclass = set(), set(), set()
        self.unique_type_attributes, self.unique_value_attributes = set(), set()
        
        self.products = []
    
    @staticmethod
    def is_digit(s):
        try:
            float(s)
            return True
        except ValueError:
            return False
        
    def get_structured_data(self, request):
        self.to_separate()
        
        for opt in range(7, len(self.attributes) + 4):
            self.unique_type_attributes.add(self.attributes[opt])
            self.unique_value_attributes.add(self.options[opt])
        
        for count, line in enumerate(self.body):
            if count % 100 == 0:
                print('Line #{}'.format(count))
                messages.add_message(request, messages.INFO, 'Success processed {} lines'.format(count))
            if not line:
                continue
            structured_product, attributes = {}, []
            try:
                self.unique_class.add(line[1])
                self.unique_subclass.add(line[2])
                self.unique_manufacturer.add(line[4])
            except KeyError:
                return False, 'Error in line: {}'.format(line)
            #print(self.options)
            for key in line.keys():
                # print('Product: ', product[key])
                if key < 7:
                    structured_product.update({
                            STRUCTURE_PRODUCT[key][1]: line[key].lstrip().rstrip()
                    })
                else:
                    attributes.append({
                        "type": TYPES_REV_DICT.get(self.attributes[key].lower()),
                        "name": self.options[key].lstrip().rstrip(),
                        "value": float(line[key].replace(',', '.')) if self.is_digit(line[key].replace(',', '.')) else line[key].lstrip().rstrip(),
                        "is_digit": self.is_digit(line[key].replace(',', '.'))
                        })
            structured_product.update({
                STRUCTURE_PRODUCT[7][1]: attributes
            })
        
            is_valid_data = self.check_exists_types(structured_product)
            if isinstance(is_valid_data, str):
                print(structured_product, 'reason: {}'.format(is_valid_data))
                return False, is_valid_data
            else:
                self.products.append(is_valid_data)
        print('Check correct and finish, start create products')
        messages.add_message(request, messages.SUCCESS, 'Check correct and finish, start create products')
        self.create_products(request)
        return True, 'Success'
        
        # TODO: make correctly check_exists
        #resp = self.check_exists_category()
        
    def to_separate(self):
        self.attributes = self.data[self.ATTRIBUTE_LINE]
        self.options = self.data[self.OPTION_LINE]
        self.body = self.data[self.OPTION_LINE+1:]
    
    def create_products(self, request):
        
        def create_attr():
            # if attr.get('type'):
            if attr.get('is_digit'):
                attr_val = UnFixedAttributeValue(value=attr['value'], attribute=attr['attr_obj'],
                                                 created_by=request.user, updated_by=request.user)
            else:
                attr_val = FixedAttributeValue(value=attr['value'], attribute=attr['attr_obj'], created_by=request.user,
                                               updated_by=request.user)
                
            attr_val.save()
            attr_val.products.add(new_product)
            attr_val.save()
            if attr.get('is_digit'):
                new_product.unfixed_attrs_vals.add(attr_val)
            else:
                new_product.fixed_attrs_vals.add(attr_val)
                
        for count, product in enumerate(self.products):
            if count % 100 == 0: print('Line #{}'.format(count))
            messages.add_message(request, messages.INFO,
                                 'Success added {} products'.format(count))
            
            new_product = Product(article=product['article'],
                                  series=product.get('series', ""),
                                  additional_article=product.get('additional_article', ""),
                                  manufacturer=product['manufacturer_obj'],
                                  title=product['name'],
                                  category=product['category_obj'],
                                  created_by=request.user,
                                  updated_by=request.user)
            new_product.save()
            for attr in product['attributes']:
                create_attr()
                    #obj_product.save()
                    #attr_val.save()
                   
    def check_exists_types(self, product):
        # check manufacturer
        try:
            manufacturer = Manufacturer.objects.get(title__icontains=product.get('manufacturer'))
        except Manufacturer.DoesNotExist:
            return 'Ошибка! Не найден производитель товаров: {}'.format(product.get('manufacturer'))
        # check category
        try:
            category = Category.objects.get(title__iexact=product['subclass'],
                                            parent__title__iexact=product['class'])
        except Category.DoesNotExist:
            return 'Ошибка! Не найден класс {} с подклассом {}'.format(product['class'], product['subclass'])
        except Category.MultipleObjectsReturned:
            return 'Ошибка! Найдено более одного подкласса {} с классом {}'.format(product['subclass'], product['class'])
        # check product
        try:
            Product.objects.get(article=product['article'], manufacturer=manufacturer)
            return 'Ошибка! Наден продукт с наименованием - {} и производителем товара - {} в БД'.format(
                product['article'], manufacturer.title)
        except Product.DoesNotExist:
            pass
        except Product.MultipleObjectsReturned:
            return 'Ошибка! Найдено несколько продуктов с наименованием - {} и производителем товара - {} в БД'.format(
                product['article'], manufacturer.title)
        # check attributes
        for attr in product['attributes']:
            # find instance attribute
            try:
                attribute = Attribute.objects.get(type=attr['type'], category=category, title=attr['name'])
                attr.update({"attr_obj": attribute})
                # find fixed attribute
                if not attr['is_digit']:
                    fix_value = FixedValue.objects.get(title=attr['value'], attribute=attribute)
                    attr['value'] = fix_value
            except Attribute.DoesNotExist:
                return 'Ошибка! Не найден атрибут с типом: {} и наименованием {} в категории {}'.format(TYPES_DICT[attr['type']], attr['name'], category)
            except Attribute.MultipleObjectsReturned:
                return 'Ошибка! Найдено несколько атрибутов с типом: {} и наименованием {}'.format(TYPES_DICT[attr['type']], attr['name'])
            except FixedValue.DoesNotExist:
                return 'Ошибка! Не найден фикс. атрибут {} со значением {}'.format(attr['value'], attribute)
            #  todo: useful insert check FixedValue.DoesNotExist
        
        product.update({
            "manufacturer_obj": manufacturer,
            "category_obj": category
        })
        
        return product
        
        
        # try:
        #     class_list = list(self.unique_class)
        #     subclass_list = list(self.unique_subclass)
        #     if (len(class_list) > 1) or (len(subclass_list) > 1):
        #         return "Too many class or subclass: {}, {}".format(class_list, subclass_list)
        #     else:
        #         category = Category.objects.get(title__icontains=class_list[0],
        #                                         parent__title__icontains=subclass_list[0])
        # except:
        #     return "Not found class or subclass"
        #
        # print(self.unique_type_attributes, self.unique_value_attributes, self.unique_manufacturer, self.unique_class, self.unique_subclass)
        #
    def get_attribute(self):
        pass
