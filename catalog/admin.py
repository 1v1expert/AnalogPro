from datetime import datetime

from django.contrib import admin
from django.contrib import messages
from django.contrib.admin.models import LogEntry
from django.contrib.admin.views.main import ChangeList
from django.contrib.auth.models import User
from django.utils.safestring import mark_safe

from app.models import MainLog
from catalog.file_utils import ProcessingUploadData, XLSDocumentReader
from catalog.models import Attribute, Category, DataFile, FixedValue, GroupSubclass, Manufacturer, Product, \
    Specification, AlternativeCategory
from catalog.reporters import generators, writers


def mark_as_published(modeladmin, request, queryset):
    queryset.update(is_public=True)
    
    
mark_as_published.short_description = u"Опубликовать"


def mark_as_unpublished(modeladmin, request, queryset):
    queryset.update(is_public=False)
    
    
mark_as_unpublished.short_description = u"Снять с публикации"


class BaseAdmin(admin.ModelAdmin):

    list_display = ['title', 'id', 'is_public', 'deleted', 'created_at', 'created_by', 'updated_at', 'updated_by']
    save_on_top = True
    actions = [mark_as_published, mark_as_unpublished]
    list_filter = ['is_public', 'deleted', 'created_at', 'updated_at']
    search_fields = ['id', 'title']
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        obj.save()

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            if not change:
                instance.created_by = request.user
            instance.updated_by = request.user
            instance.save()


class SubCatValInline(admin.TabularInline):
    model = Category


class AttributeshipInline(admin.TabularInline):
    model = Category.attributes.through


class CategoryAdmin(BaseAdmin):
    list_display = ('title', 'get_attributes')
    
    #inlines = [AttributeshipInline]
    #exclude = ('attributes', )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        obj.save()
        if obj.parent and not obj.attributes.all().count():
            obj.attributes.add(*list(obj.parent.attributes.all()))
            # obj.attributes.save()
            # obj.save()  ## what is it??
        
    def get_attributes(self, obj):
        """Атрибуты"""
        return "; ".join(['{}: {}'.format(p.type, p.title) for p in obj.attributes.all()])
    get_attributes.short_description = 'Атрибуты'


class AttributeAdmin(BaseAdmin):
    list_display = ['title', 'unit', 'weight', 'id', 'type', 'priority', 'is_public', 'deleted']


class ProductChangeList(ChangeList):
    def __init__(self, request, model, list_display, list_display_links,
                 list_filter, date_hierarchy, search_fields, list_select_related,
                 list_per_page, list_max_show_all, list_editable, model_admin, sortable_by):
        super(ProductChangeList, self).__init__(request, model, list_display, list_display_links,
                 list_filter, date_hierarchy, search_fields, list_select_related,
                 list_per_page, list_max_show_all, list_editable, model_admin, sortable_by)
    
        # these need to be defined here, and not in MovieAdmin
        self.list_display = ['title', 'article', 'manufacturer', 'attrs_vals', 'category','is_public', 'deleted']
        self.list_display_links = ['attrs_vals']
        # self.list_editable = ['genre']


class ProductAdmin(BaseAdmin):
    list_display = ['title', 'article', 'manufacturer', 'category', 'get_attributes', 'series', 'priority', 'is_public', 'deleted', ]
    list_select_related = True
    autocomplete_fields = ['category', 'manufacturer',]

    def get_attributes(self, obj):
        return "; ".join(
            [
                '{}: {}'.format(
                    p['attribute__title'],
                    p['value__title'] if p['attribute__is_fixed'] else p['un_value']) for p in obj.get_full_info()
            ]
        )

    get_attributes.short_description = 'Атрибуты'
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related(
            'attributevalue_set',
            'attributevalue_set__attribute',
            'attributevalue_set__value'
        ).select_related(
            'manufacturer',
            'category'
        )


class ManufacturerAdmin(BaseAdmin):
    list_display = ['title', 'id', 'is_tried', 'get_product_count', 'get_kns_product_count',
                    'get_fasteners_product_count', 'get_working_product_count', 'created_at', 'created_by']
    actions = ['export_data_to_xls', 'export_full_dump', 'export_duplicate_products', 'delete_fasteners_products',
               'delete_kns_products', 'download_check_result', 'clear_analogs']
    
    def get_product_count(self, obj):
        return obj.products.count()

    get_product_count.short_description = 'Кол-во поз-й'
    
    def get_kns_product_count(self, obj):
        return obj.products.filter(
            category__parent__title__icontains="КНС",
        ).count()

    get_kns_product_count.short_description = 'Кол-во КНС'

    def get_fasteners_product_count(self, obj):
        return obj.products.filter(
            category__parent__title__icontains="крепеж",
        ).count()

    get_fasteners_product_count.short_description = 'Кол-во КРЕПЕЖ'
    
    def get_working_product_count(self, obj):
        return obj.products.exclude(raw=None).count()

    get_working_product_count.short_description = 'Кол-во обраб. поз-й'
    
    def clear_analogs(self, request, queryset):
        for manufacturer in queryset:
            Product.objects.filter(manufacturer=manufacturer).update(raw=None)
            for product in Product.objects.filter(manufacturer=manufacturer):
                product.analogs_to.clear()

        messages.add_message(request, messages.SUCCESS,
                             'Результаты подобора для выбранных производителей успешно очищены')
    clear_analogs.short_description = 'Очистить рез-ты подбора'
    
    def delete_fasteners_products(self, request, queryset):
        for manufacturer in queryset:
            products = Product.objects.filter(
                manufacturer=manufacturer,
                category__parent__title__icontains="крепеж",
            )
            c_products = products.count()
            products.delete()

            messages.add_message(request, messages.SUCCESS,
                                 f'Удалены {c_products} позиций у {manufacturer.title} в категории "Крепеж"')

    delete_fasteners_products.short_description = 'Удалить позиции "Крепеж"а'
    
    def delete_kns_products(self, request, queryset):
        for manufacturer in queryset:
            products = Product.objects.filter(
                manufacturer=manufacturer,
                category__parent__title__icontains="КНС",
            )
            c_products = products.count()
            products.delete()
    
            messages.add_message(request, messages.SUCCESS,
                                 f'Удалены {c_products} позиций у {manufacturer.title} в категории "КНС"')

    delete_kns_products.short_description = 'Удалить позиции "КНС"а'
    
    def export_full_dump(self, request, queryset):
        meta_data = generators.AdditionalGeneratorTemplate((User, Manufacturer, Category, Attribute, FixedValue))
        with writers.BookkeepingWriter('Dump another data {}'.format(datetime.now().date()), request.user) as writer:
            writer.dump(meta_data.generate())

    export_full_dump.short_description = 'Выгрузить базу'
    
    def export_data_to_xls(self, request, queryset):
        data = generators.DefaultGeneratorTemplate(queryset)
        with writers.BookkeepingWriter('Dump data {}'.format(datetime.now().date()), request.user) as writer:
            writer.dump(data.generate())
    
    export_data_to_xls.short_description = 'Выгрузить продукты производителя(-ей)'
    
    def export_duplicate_products(self, request, queryset):
        meta_data = generators.AdditionalGeneratorTemplate(
            (Product, ), **dict(**dict(is_duplicate=True))
        )
        with writers.BookkeepingWriter('Dump duplicate products {}'.format(datetime.now().date()), request.user) as writer:
            writer.dump(meta_data.generate())

    export_duplicate_products.short_description = 'Выгрузить дубликаты'
    
    def download_check_result(self, request, queryset):
        for manufacturer in queryset:
            generator = generators.HealthCheckGenerator(manufacturer, request.user)
            generator.generate_and_write()

    download_check_result.short_description = 'Download check result'


class FileUploadAdmin(admin.ModelAdmin):
    actions = ['process_file']
    list_display = ['file', 'type', 'file_link', 'created_at', 'created_by']
    
    def file_link(self, obj):
        if obj.file:
            return mark_safe("<a href='/%s'>скачать</a>" % (obj.file.url,))
        else:
            return "No attachment"

    file_link.allow_tags = True
    file_link.short_description = 'Ссылка на скачивание'
    
    def process_file(self, request, queryset):
        for qq in queryset:
            created, error = ProcessingUploadData(
                XLSDocumentReader(path=qq.file.name).parse_file(), request=request
            ).get_structured_data(only_check=False)
            
            if created:
                messages.add_message(request, messages.SUCCESS, 'Данные успешно загружены из {} файла в БД'.format(qq.file.name))
            else:
                messages.add_message(request, messages.ERROR, error)
    process_file.short_description = u'Импортировать данные(общий шаблон)'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        obj.save()
    
    #autocomplete_fields = ['category']


class MainLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'action_time', 'message', 'client_address']


class LogEntryAdmin(admin.ModelAdmin):
    list_display = ['content_type', 'user', 'action_time', 'object_id', 'object_repr', 'action_flag', 'change_message']
    readonly_fields = ('content_type', 'user', 'action_time', 'object_id', 'object_repr', 'action_flag',
                       'change_message')

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        actions = super(LogEntryAdmin, self).get_actions(request)
        # del actions['delete_selected']
        return actions
    

class FixValAdmin(BaseAdmin):
    list_display = ['title', 'attribute', 'id', 'deleted']


class GroupSubclassAdmin(BaseAdmin):
    list_display = ['category', 'fixed_attribute', 'image']
    

class AlternativeCategoryAdmin(BaseAdmin):
    list_display = ['original', 'alternative']


admin.site.register(MainLog, MainLogAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(FixedValue, FixValAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(Manufacturer, ManufacturerAdmin)
admin.site.register(Attribute, AttributeAdmin)
admin.site.register(Specification, BaseAdmin)
admin.site.register(DataFile, FileUploadAdmin)
admin.site.register(LogEntry, LogEntryAdmin)
admin.site.register(GroupSubclass, GroupSubclassAdmin)
admin.site.register(AlternativeCategory, AlternativeCategoryAdmin)

