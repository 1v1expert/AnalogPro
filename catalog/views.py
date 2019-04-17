from django.shortcuts import render
from .forms import *
from .models import Product, AttributeValue


def render_search(request, queryset):
	return render(request, 'admin/catalog/search.html', queryset)
# Create your views here.


def search_view(request):
	form = SearchForm()
	advanced_form = AdvancedeSearchForm()
	
	if request.method == 'POST':
		form = SearchForm(request.POST)
		if form.is_valid():
			try:
				# проверка на единственность и существование продукта с артикулом и поставщиком
				try:
					product = Product.objects.get(article=form.cleaned_data['article'],
					                              manufacturer=form.cleaned_data['manufacturer_from'])
				except Product.DoesNotExist:
					return render(request, 'admin/catalog/search.html', {'Error': {'val': True,
					                                                               'msg': 'Не найден продукт с артикулом {}'.format(
						                                                               form.cleaned_data['article'])}})
				except Product.MultipleObjectsReturned:
					return render(request, 'admin/catalog/search.html', {'Error': {'val': True,
					                                                               'msg': 'Найдено более одного продукта с артикулом {}'
					                                                               'и производителем {}'.format(
						                                                        form.cleaned_data['article'],
						                                                        form.cleaned_data['manufacturer_from'])}})
				# initial filter product
				find_products = Product.objects.filter(manufacturer=form.cleaned_data['manufacturer_to'], category=product.category)
				# cycle for attributes in product attributes
				for attr in product.attrs_vals.all():
					pass
					# find_product = find_product.filter(attrs_vals__attribute=attr.attribute,
					#                                    attrs_vals__title=attr.title)
					# if attr.attribute.type in ('hrd', 'sft'):
					#
					# 	find_products = find_products.filter(attrs_vals__attribute=attr.attribute, attrs_vals__title=attr.title)

				if find_products.count() == 1:
					error = {'val': False}
				elif find_products.count() == 0:
					error = {'val': True, 'msg': 'По заданным параметрам не найдено продуктов'}
				else:
					error = {'val': True, 'msg': 'По заданным параметрам найдено более одного продукта'}
				return render(request, 'admin/catalog/search.html', {'Results': find_products, 'Product': product,
				                                                     'Error': error})
				# print(products_values, find_product)
				#print(product.category)
				#print(product.category.attributes.filter(type='hrd'))
				#find_product = Product.objects.filter(manufacturer=form.cleaned_data['manufacturer_to'])
				#print(find_product)
			except Exception as e:
				return render(request, 'admin/catalog/search.html', {'Error': {'val': True,
				                                                               'msg': 'Произошла непредвиденная ошибка '
				                                                                      'при поиске артикула {}, >> {}'.format(
					                                                               form.cleaned_data['article'], e)}})
			#print(form.cleaned_data)
		return render(request, 'admin/catalog/search.html', {'Fake': 'Fake'})

	return render(request, 'admin/catalog/search.html', {'form': form, 'advanced_form': advanced_form}) #{'form': form})