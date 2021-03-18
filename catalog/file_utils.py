# import the logging library
import logging
import time

import openpyxl
from django.contrib.auth import models as auth_md
from openpyxl.utils.exceptions import InvalidFileException
from functools import lru_cache
from app.models import MainLog
from catalog.choices import _dict, _rev_dict
from catalog.models import *

# Get an instance of a logger
logger = logging.getLogger('analog')


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
        logger.debug(f'Start parse file: {self.xlsx}')
        start_time = time.time()
        
        rows = self.sheet.rows
        for cnt, row in enumerate(rows):
            
            line = {}
            for cnt_c, cell in enumerate(row):
    
                if cell.value is None:
                    continue
                value = str(cell.value).strip()
                
                if value:
                    line.update({cnt_c: value})
                    
            self.doc.append(line)
            
        self.workbook._archive.close()
        
        logger.debug(f'Finish parse file, time left: {time.time() - start_time}s')
        return self.doc


@lru_cache()
def get_manufacturer(manufacturer: str):
    return Manufacturer.objects.get(title__icontains=manufacturer)


@lru_cache()
def get_category(product_class, product_subclass):
    return Category.objects.get(
        title__iexact=product_subclass,
        parent__title__iexact=product_class
    )


@lru_cache()
def get_attribute(category, name):
    return Attribute.objects.get(category=category, title__iexact=name)


@lru_cache()
def get_fixed_value(value, attribute):
    return FixedValue.objects.get(title__iexact=value, attribute=attribute)


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
    STRUCTURE_PRODUCT = (
        (0, "title"),
        (1, "class"),
        (2, "article"),
        (3, "additional_article"),
        (4, "series"),
        (5, "priority"),
        (6, "subclass"),
        (7, "manufacturer"),
        (8, "irrelevant"),
        (9, "attributes")
    )

    STRUCTURE_PRODUCT_REV_DICT = _rev_dict(STRUCTURE_PRODUCT)
    STRUCTURE_PRODUCT_DICT = _dict(STRUCTURE_PRODUCT)
    
    def __init__(self, data, request=None):
        
        if request is None:
            self.user = auth_md.User.objects.get(is_staff=True, username='admin')
        else:
            self.user = request.user
            
        self.start_time = time.time()
        
        self.ATTRIBUTE_LINE = 0
        self.OPTION_LINE = 0
        
        self.data = data
        self.attributes = []
        self.options = []
        self.body = []

        self.unique_manufacturer, self.unique_class, self.unique_subclass = set(), set(), set()
        self.unique_type_attributes, self.unique_value_attributes = set(), set()
        
        self.products = []
        
    def get_structured_data(self, only_check=True):
        self.to_separate()
        
        # for opt in range(6, len(self.attributes) + 4):
        #     self.unique_type_attributes.add(self.attributes[opt])
        #     self.unique_value_attributes.add(self.options[opt])
        
        for count, line in enumerate(self.body):
            if count % 100 == 0:
                logger.debug('Line #{}'.format(count))
                # messages.add_message(request, messages.INFO, 'Success processed {} lines'.format(count))
            if not line:  # empty line
                continue
                
            structured_product, attributes = {}, []
            try:
                self.unique_class.add(line[1])
                self.unique_subclass.add(line[6])
                self.unique_manufacturer.add(line[7])
            except KeyError:
                return False, 'Error in line: {}'.format(line)
            
            for key in line.keys():
                if key < 9:
                    structured_product.update({
                            self.STRUCTURE_PRODUCT[key][1]: line[key]  # article: 1234
                    })
                else:
                    attributes.append({
                        "name": self.options[key],
                        "value": line[key]
                        })

            structured_product.update({
                self.STRUCTURE_PRODUCT[9][1]: attributes
            })

            is_valid_data = self.check_exists_types(structured_product)

            if isinstance(is_valid_data, str):
                MainLog(
                    user=self.user,
                    message=f'{is_valid_data}\n reason: {structured_product}, time: {time.time() - self.start_time}'
                ).save()
                return False, is_valid_data
            else:
                self.products.append(is_valid_data)
        logger.debug('Check correct and finish, start creating products')
        # messages.add_message(request, messages.SUCCESS, 'Check correct and finish, start create products')
        if not only_check:
            self.create_products()
        
        MainLog(user=self.user, message='Processing success in {}  seconds'.format(time.time()-self.start_time)).save()
        return True, 'Success'
        
        # TODO: make correctly check_exists
        #resp = self.check_exists_category()
        
    def to_separate(self):
        self.attributes = self.data[self.ATTRIBUTE_LINE]
        self.options = self.data[self.OPTION_LINE]
        self.body = self.data[self.OPTION_LINE+1:]
    
    def create_products(self):
        
        def create_attr():
            attr_val = AttributeValue(
                value=attr['value'] if attr['attr_obj'].is_fixed else None,
                un_value=attr['value'] if not attr['attr_obj'].is_fixed else None,
                attribute=attr['attr_obj'],
                created_by=self.user,
                updated_by=self.user,
                product=new_product
            )
            attr_val.save()
            
        for count, product in enumerate(self.products):
    
            new_product = Product(
                article=product['article'],
                additional_article=product.get('additional_article', ""),
                manufacturer=product['manufacturer_obj'],
                series=product.get('series', ""),
                title=product['title'],
                category=product['category_obj'],
                priority=int(product.get('priority', 10)),
                created_by=self.user,
                updated_by=self.user,
                is_tried=True,
                irrelevant=True if product.get("irrelevant", False) in ("True", "true", 1, "1", True) else False
            )
            new_product.save()
            for attr in product['attributes']:
                create_attr()
 
    def check_exists_types(self, product):
        # check manufacturer
        try:
            manufacturer = get_manufacturer(product.get('manufacturer'))
        except Manufacturer.DoesNotExist:
            return 'Ошибка! Не найден производитель товаров: {}'.format(product.get('manufacturer'))
        # check category
        try:
            category = get_category(product['class'], product['subclass'],)
        except Category.DoesNotExist:
            return 'Ошибка! Не найден класс {} с подклассом {}'.format(product['class'], product['subclass'])
        except Category.MultipleObjectsReturned:
            return 'Ошибка! Найдено более одного подкласса {} с классом {}'.format(product['subclass'], product['class'])
        # check product
        try:
            Product.objects.get(article=product['article'], manufacturer=manufacturer, additional_article=product.get("additional_article"))
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
                attribute = get_attribute(category, attr['name'])
                attr.update({"attr_obj": attribute})
                # find fixed attribute
                if attribute.is_fixed:
                    fix_value = get_fixed_value(attr['value'], attribute)
                    attr['value'] = fix_value
                else:
                    attr['value'] = float(attr['value'].replace(',', '.')) if is_digit(attr['value'].replace(',', '.')) else attr['value']
            except Attribute.DoesNotExist:
                return f'Ошибка! Не найден атрибут с наименованием {attr["name"]} в категории {category}'
            except Attribute.MultipleObjectsReturned:
                return f'Ошибка! Найдено несколько атрибутов с наименованием {attr["name"]}'
            except FixedValue.DoesNotExist:
                return f'Ошибка! Не найден фикс. атрибут {attribute} со значением {attr["value"]}'
            #  todo: useful insert check FixedValue.DoesNotExist
        
        product.update({
            "manufacturer_obj": manufacturer,
            "category_obj": category
        })
        
        return product

    def get_attribute(self):
        pass
    

def is_digit(s):
    try:
        float(s)
        return True
    except ValueError:
        return False
    except:
        return False
    
    
sheet_names = {
    'Нержавейка': 'нержавейка',
    'Лестничные': 'лестничный',
    'Оцинковка': 'хол. цинк'
}


class SubclassesReader(object):
    def __init__(self, path=None, workbook=None, only_parse=True, user=None, loadnetworkmodel=False, name_sheet=None):
        assert path or workbook, "You should provide either path to file or XLS-object"
        
        if workbook:
            self.workbook = workbook
        else:
            try:
                self.workbook = openpyxl.load_workbook(path,
                                                       read_only=True,
                                                       data_only=True)
            except InvalidFileException:
                # make read file another reader
                raise Exception('Invalid file')
        self.xlsx = path
        # self.ws = self.workbook.active
        self.sheet = self.workbook.active
        self.sheets = self.workbook.get_sheet_names()
        self.body = {}
        self.header = {}
        self.create_subclass = True
        self.user_admin = auth_md.User.objects.get(is_staff=True, username='admin')

    def parse_file(self, sheet_name=None):
        rows = self.sheet.rows
        for cnt, row in enumerate(rows):
            if cnt == 0:
                self.generate_header(row)
            else:
                self.generate_body(row, cnt)
                
        self.workbook._archive.close()
        
        return {"header": self.header, "body": self.body}
    
    def generate_body(self, row, number):
        # line = {}
        self.body[number] = {}
        for cnt_c, cell in enumerate(row):
            if cell.value is None:
                continue
            value = str(cell.value).strip()
            
            self.body[number].update({cnt_c: {"value": value, "object": None}})
            # }
            
            if cnt_c == 0:
                parent_category = Category.objects.get(title__iexact='КНС')
                self.body[number][cnt_c]["object"], created = Category.objects.get_or_create(title=value, parent=parent_category, defaults={"created_by": self.user_admin, "updated_by": self.user_admin})
            # if cell.value:
                # line.update({cnt_c: str(cell.value)})
        # self.doc.append(line)
        
    def generate_header(self, row):
        for cnt_c, cell in enumerate(row):
            if cell.value is None:
                continue
            value = str(cell.value).strip()
            if cell.value:
                self.header.update({
                    cnt_c: {
                        "value": value,
                        "object": None
                    }
                })
                
            if cnt_c != 0:
                try:
                    self.header[cnt_c]["object"] = Attribute.objects.get(title__iexact=value)
                except Attribute.DoesNotExist:
                    raise Exception(f"Not found {cell.value} attribute")
                
    def process(self):
        for key in self.body.keys():
            line = self.body[key]
            print(line)
            for cell in line.keys():
                if cell == 0: #  this is subclass
                    continue
                    
                enabled = line[cell]["value"]  # '1' or '0'
                if enabled == '1':
                    subclass: Category = line[0]["object"]
                    subclass.attributes.add(self.header[cell]["object"])
                    subclass.save()