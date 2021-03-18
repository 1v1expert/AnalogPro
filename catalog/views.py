from django.shortcuts import render, redirect, reverse
from .forms import *
from catalog.models import Product, FixedValue, Category, DataFile
from catalog import choices
from catalog.handlers import ProcessingSearchFile, result_processing
from catalog.utils import SearchProducts
import os
from django.http import HttpResponse, Http404
from django.contrib.auth.decorators import login_required


def render_search(request, queryset):
    return render(request, 'admin/catalog/search.html', queryset)


# Create your views here.


def advanced_search_view(request, product_id, manufacturer_to, *args, **kwargs):
    # be sure to rewrite form formation
    product = Product.objects.get(pk=product_id)
    # attributes = product.category.attributes.all()#.exclude(type='hrd')
    fix_attributes = product.fixed_attrs_vals.all()  # category.attributes.all()
    unfix_attributes = product.unfixed_attrs_vals.all()  # category.attributes.all()
    # attributes = product.attrs_vals.all()
    # attributes_array = {str(attr.pk): {'title': attr.title,
    #                                    'type_display': attr.get_type_display(),
    #                                    'attribute': attr,
    #                                    'type': attr.type} for attr in attributes}
    attributes_array = {
        'fix' + str(attr.pk): {'title': attr.attribute.title, 'type_display': attr.attribute.get_type_display(),
                               'choices': FixedValue.objects.filter(attribute=attr.attribute).values_list('pk',
                                                                                                          'title'),
                               # 'choices': [attribute.title for attribute in FixedValue.objects.filter(attribute=attr.attribute)],
                               'type': attr.attribute.type} for attr in fix_attributes}
    
    fix_attributes_array = {'fix' + str(attr.pk): {'title': attr.attribute.title,
                                                   'type_display': attr.attribute.get_type_display(),
                                                   'choices': FixedValue.objects.filter(
                                                       attribute=attr.attribute).values_list('pk', 'title'),
                                                   # 'choices': [attribute.title for attribute in FixedValue.objects.filter(attribute=attr.attribute)],
                                                   'type': attr.attribute.type} for attr in fix_attributes}
    
    unfix_attributes_array = {
        'unfix' + str(attr.pk): {'title': attr.attribute.title, 'type_display': attr.attribute.get_type_display(),
                                 'choices': TYPES_SEARCH,
                                 # 'choices': [attribute.title for attribute in FixedValue.objects.filter(attribute=attr.attribute)],
                                 'type': attr.attribute.type} for attr in unfix_attributes}
    
    attributes_array.update(fix_attributes_array)
    attributes_array.update(unfix_attributes_array)
    
    data = {'article': product.article}
    advanced_form = AdvancedSearchForm(extra=attributes_array, initial=data)
    # advanced_form = AdvancedSearchForm(extra=attributes_array, initial=data)
    if request.method == 'POST':
        advanced_form = AdvancedSearchForm(request.POST, extra=attributes_array)
        if advanced_form.is_valid():
            advanced_form.cleaned_data['manufacturer_from'] = product.manufacturer
            advanced_form.cleaned_data['manufacturer_to'] = manufacturer_to
            result = SearchProducts(request, advanced_form, product)
            return result_processing(result, request, product, default=False)
    
    return render(request, 'admin/catalog/advanced_search.html', {'advanced_form': advanced_form, 'product': product,
                                                                  'manufacturer_to': manufacturer_to})  # , {'advanced_form': advanced_form})


@login_required(login_url='/admin/login')
def search_view(request):
    form = SearchForm()
    if request.method == 'POST':
        form = SearchForm(request.POST)
        if form.is_valid():
            advanced_search = form.cleaned_data['advanced_search']
            article = form.cleaned_data['article']
            manufacturer_from = form.cleaned_data['manufacturer_from']
            manufacturer_to = form.cleaned_data['manufacturer_to']
            
            try:
                product = Product.objects.get(article=article, manufacturer=manufacturer_from)
            except Product.DoesNotExist:
                return render(request, 'admin/catalog/search.html',
                              {'Error': {'val': True, 'msg': 'Не найден продукт с артикулом {}'.format(article)}})
            except Product.MultipleObjectsReturned:
                return render(request, 'admin/catalog/search.html',
                              {'Error': {'val': True, 'msg': 'Найдено более одного продукта с артикулом {}'
                                                             'и производителем {}'.format(article, manufacturer_from)}})
            
            if advanced_search:
                return redirect('catalog:advanced_search', product.pk, manufacturer_to.id)
            else:
                result = SearchProducts(request, form, product)
                return result_processing(result, request, product, default=True)
            # return SearchProducts(request, form, product).search()
        
        return render(request, 'admin/catalog/search.html', {'Error': {'val': True, 'msg': 'Ошибка формы'}})
    
    return render(request, 'admin/catalog/search.html', {'form': form})


@login_required(login_url='/admin/login')
def search_from_file_view(request):
    if request.method == 'POST':
        form = SearchFromFile(request.POST, request.FILES)
        
        if form.is_valid():
            instance = DataFile(file=request.FILES['file'],
                                type=choices.TYPES_FILE[1][0],
                                created_by=request.user,
                                updated_by=request.user)
            instance.save()
            file_response = ProcessingSearchFile(request.FILES['file'], instance.file, form, request).csv_processing()
            
            # return file
            # file_path = instance.file.path
            # if os.path.exists(file_path):
            # 	with open(file_path, 'rb') as fh:
            # 		response = HttpResponse(fh.read(), content_type="application/vnd.ms-excel")
            # 		response['Content-Disposition'] = 'inline; filename=' + os.path.basename(file_path)
            # 		return response
            # raise Http404
            
            response = HttpResponse(file_response, content_type='text/plain')
            response[
                'Content-Disposition'] = 'attachment; filename=' + file_response.name  # '{}/{}'.format(settings.FILES_ROOT, file_response.name) #file_response.path
            return response
    else:
        form = SearchFromFile()
    return render(request, 'admin/catalog/search.html', {'file_form': form})
