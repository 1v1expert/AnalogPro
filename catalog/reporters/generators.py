import datetime
from collections import OrderedDict
from time import time
from typing import Optional, Tuple

from django.db.models import QuerySet
from catalog.reporters.writers import HealthCheckBookkeepingWriter
from catalog.models import AnalogSearch, Attribute, Manufacturer, Product
from catalog.utils import get_or_create_tech_user

class BaseGenerator:
    def __init__(self, *args, **kwargs):
        self.start_at = time()
        
    def generate(self):
        raise NotImplemented


class DefaultGeneratorTemplate(object):
    """ Default generator per manufacturer """
    def __init__(self, manufactures=None):
        self.manufactures = manufactures
        self.date = datetime.datetime.now()
        self.attributes = Attribute.objects.values_list('title', flat=True)
    
    def _get_data(self, manufacturer=None, name_sheet=None, products=None) -> dict:
        data = {
            "top_header": {
                'spread': None,
                'row': [],
                'name': name_sheet if name_sheet else str(manufacturer)
            },
            "table_header": OrderedDict(
                [
                    ('seq', '№ п/п'),
                    ('title', 'Наименование'),
                    ('article', 'Артикул'),
                    ('manufacturer', 'Производитель'),
                    ('additional_article', 'Доп. артикул'),
                    ('series', 'Серия'),
                    ('category', 'Категория'),
                ] + list(Attribute.objects.values_list('id', 'title'))
            ),
            "table_data": self.do_products(manufacturer=manufacturer, products=products)
        }
        data["top_header"]["spread"] = len(data['table_header'])
    
        return data
    
    def generate(self) -> dict:
        for manufacturer in self.manufactures:
            yield self._get_data(manufacturer=manufacturer)
            
    def do_products(self, manufacturer=None, products=None) -> OrderedDict:
        if products is None:
            products = Product.objects.filter(
                manufacturer=manufacturer
            ).prefetch_related(
                'attributevalue_set',
                'attributevalue_set__value',
                'attributevalue_set__attribute'
            )

        for seq, product in enumerate(products):
            yield OrderedDict(
                [
                    ('seq', seq),
                    ('title', product.title),
                    ('article', product.article),
                    ('manufacturer', product.manufacturer.title),
                    ('additional_article', product.additional_article),
                    ('series', product.series),
                    ('category', product.category.title),
                ] + self._get_attributes(product))

    def _get_attributes(self, product) -> list:
        list_attributes = []
        values = product.attributevalue_set.all()

        for i, attribute in enumerate(self.attributes):
            is_found = False
            for value in values:
                if attribute in value.attribute.title:
                    list_attributes.append((i, value.un_value if value.is_fixed else value.value.title))
                    is_found = True
                    break

            if not is_found:
                list_attributes.append((i, ''))

        return list_attributes


class AdditionalGeneratorTemplate(object):
    """Генератор отчётов по инстансам базовых классов с произвольным фильтром"""
    
    def __init__(self, classes, *args, **kwargs):
        self.classes = classes
        self.local_fields = None
        self.kwargs = kwargs
        
    def _get_data(self, cls_obj):
        data = {
            "top_header": {
                'spread': None,
                'row': [],
                'name': str(cls_obj._meta.verbose_name),
            },
            "table_header": OrderedDict(
                [
                    (field.name, field.verbose_name) for field in cls_obj._meta.local_fields
                ]
            ),
            "table_data": self.values(cls_obj, **self.kwargs),
        }
        data["top_header"]["spread"] = len(data['table_header'])
        
        return data
    
    def generate(self):
        for cls_obj in self.classes:
            yield self._get_data(cls_obj)
    
    @staticmethod
    def values(cls_obj, **kwargs):
        return cls_obj.objects.filter(**kwargs).values_list()


class HealthCheckGenerator(object):
    def __init__(self, manufacturer=None, user=None):
        assert manufacturer is not None, 'Manufacturer is not be None'
        self.manufacturer = manufacturer
        self.start_at = time()
        self.writer = HealthCheckBookkeepingWriter
        self.user = user or get_or_create_tech_user()

    def generate(self) -> dict:
        data = {
            "top_header": {
                'spread': None,
                'row': [],
                'name': str(self.manufacturer)[:31],
            },
            'table_header': {
                attribute["pk"]: {
                    key: attribute[key] for key in attribute.keys()
                } for attribute in Attribute.objects.values('pk', 'title', 'type').order_by('pk', 'type')},
            'table_data': self.get_data(self.manufacturer)
        }
        
        for idx, key in enumerate(data["table_header"].keys(), 7):
            data["table_header"][key]["cell"] = idx

        data["table_header"]["category"] = {"title": "подкласс", "cell": 5}
        data["table_header"]["title"] = {"title": "наименование", "cell": 4}
        data["table_header"]["article"] = {"title": "артикул", "cell": 2}
        data["table_header"]["pk"] = {"title": "идентификатор", "cell": 1}
        data["table_header"]["additional_article"] = {"title": "доп. артикул", "cell": 3}
        data["table_header"]["manufacturer"] = {"title": "производитель", "cell": 6}
        
        yield data
        
    def get_data(self, manufacturer):
        manufactures_to = Manufacturer.objects.exclude(pk=manufacturer.pk).filter(is_tried=True)
        
        pr_counts = Product.objects.filter(manufacturer=manufacturer).count()
        limit = int(pr_counts/4)
        for initial_product in Product.objects.filter(manufacturer=manufacturer)[limit*2:3*limit]:
            for manufacturer_to in manufactures_to:
                
                analog = initial_product.get_analog(manufacturer_to)
                
                # if analog is None:
                #     continue

                queryset__pk = initial_product.raw.get("analogs", {}).get(manufacturer_to.pk, {}) if initial_product.raw is not None else {}
                yield {
                    'initial_product': initial_product,
                    'analogs': {
                        'analog': analog,
                        'manufacturer_to': manufacturer_to,
                        'queryset': Product.objects.filter(pk__in=queryset__pk.get("analog_seconds")) if queryset__pk.get("analog_seconds") is not None else []
                    }
                }
    
    def generate_and_write(self):
        with self.writer(f'HealthCheck for {self.manufacturer.title} p3', self.user) as writer:
            writer.dump(self.generate())
