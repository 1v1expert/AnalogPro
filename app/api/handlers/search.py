from django.http import JsonResponse
from django.views import View

from catalog.exceptions import AnalogNotFound, ArticleNotFound
from catalog.forms import SearchForm
from catalog.models import Manufacturer, Product
from app.api.handlers.functools import make_error_json_response, make_success_json_response
from app.decorators import a_decorator_passing_logs

def get_product_info(analog: Product, original: Product):
    info = list()
    info.append(
        {
            "analog":
                {
                    "name": "наименование", "value": analog.title
                },
            "original":
                {
                    "name": "наименование", "value": original.title
                }
        }
    )

    matching = {
        analog.pk: "analog",
        original.pk: "original"
    }
    
    for attribute__pk, group in original.comparison(analog):
        elements = list(group)
        element1 = elements[0]
        
        if element1["attribute__title"].lower() in ('ед. изм.', 'цена', 'нет в прайсе'):
            continue
        
        if len(elements) == 2:
            element2 = elements[1]
            if element2 != element1:
                info.append({
                    matching[element1["product__pk"]]: {
                        "name": element1["attribute__title"].lower(),
                        "value": element1["value__title"] if element1["value__title"] is not None else element1["un_value"]
                    },
                    matching[element2["product__pk"]]: {
                        "name": element2["attribute__title"].lower(),
                        "value": element2["value__title"] if element2["value__title"] is not None else element2["un_value"]
                    },
                })
            else:
                info.append({
                    "analog": {
                        "name": element1["attribute__title"].lower(),
                        "value": element1["value__title"] if element1["value__title"] is not None else element1[
                            "un_value"]
                    },
                    "original": {
                        "name": element1["attribute__title"].lower(),
                        "value": element1["value__title"] if element1["value__title"] is not None else element1[
                            "un_value"]
                    }
                })

        elif len(elements) == 1:
            product__pk = [key for key in matching.keys() if key != element1["product__pk"]][0]
            info.append({
                matching[element1["product__pk"]]: {
                    "name": element1["attribute__title"].lower(),
                    "value": element1["value__title"] if element1["value__title"] is not None else element1["un_value"]
                },
                
                matching[product__pk]: {
                    "name": element1["attribute__title"].lower(),
                    "value": "------"
                },
            })

    info.append(
        {
            "analog":
                {
                    "name": "производитель", "value": analog.manufacturer.title
                },
            "original":
                {
                    "name": "производитель", "value": original.manufacturer.title
                }
        }
    )

    return {"result": info}


def get_analog(article: str = None, manufacturer_to: Manufacturer = None, pk: str = None) -> dict:
    if pk:
        product = Product.objects.filter(
            pk=pk
        ).first()
    else:
        product = Product.objects.filter(
            article=article,
            # is_enabled=True
        ).first()
    
    if not product:
        raise ArticleNotFound("Артикул {} не найден".format(article),
                              "Article: {}, manufacturer to: {}".format(article, manufacturer_to))
    
    analog = product.get_analog(manufacturer_to)
    if not analog:
        raise AnalogNotFound('Аналог по артикулу: {} не найден'.format(article),
                             "Not find analog for article: {}, manufacturer to: {}".format(article, manufacturer_to))
    info = get_product_info(analog=analog, original=product)
    return {"analog": analog, "info": info, "product": product}


class SearchView(View):
    LIMIT_VIEW = 50

    @a_decorator_passing_logs
    def get(self, request):
        article = request.GET.get("article")
    
        if article is not None and len(article) > 1:
            return make_success_json_response(
                list(
                    Product.objects.filter(
                        article__istartswith=article  # , is_enabled=True  # todo: maybe use later
                    ).extra(
                        select={'value': 'article'}
                    ).values(
                        'value',
                        'title',
                        'manufacturer__title',
                        'pk'
                    )[:self.LIMIT_VIEW]
                ),
                safe=False
            )
        
        return make_error_json_response(f'{article} не найден')  # JsonResponse({'error': "Not found"})

    @a_decorator_passing_logs
    def post(self, request):
        form = SearchForm(request.POST)
        if form.is_valid():
        
            article = form.cleaned_data['article']
            manufacturer_to = form.cleaned_data['manufacturer_to']
            pk = form.cleaned_data["pk"]
        
            try:
                result = get_analog(article=article, manufacturer_to=manufacturer_to, pk=pk)
                return make_success_json_response({
                    'result': [result["analog"].article],
                    'info': result["info"].get("result"),
                    "image": result["info"].get("image"),
                    'result_pk': result["analog"].pk,
                    'original_pk': result["product"].pk,
                    'error': False
                })
            except Exception as e:
                return make_error_json_response('Аналог не найден')
    
        return make_error_json_response('Некорректные данные.')

