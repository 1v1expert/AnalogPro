import hashlib
from smtplib import SMTPDataError

from django.contrib.auth import login, models
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from app.decorators import a_decorator_passing_logs
from app.forms import FeedBackForm, MyAuthenticationForm, MyRegistrationForm, SearchFromFile, SubscribeForm
from app.trans import trans_text
from catalog import choices
from catalog.handlers import ProcessingSearchFile
from catalog.internal.messages import send_email_with_connection
from catalog.models import DataFile, Manufacturer


@login_required(login_url='login/')
@a_decorator_passing_logs
def search_from_file_view(request):

    if request.method == 'POST':
        form = SearchFromFile(request.POST, request.FILES)
        if form.is_valid():
            instance = DataFile(file=request.FILES['file'],
                                type=choices.TYPES_FILE[1][0],
                                created_by=request.user,
                                updated_by=request.user)
            instance.save()
            file_response = ProcessingSearchFile(request.FILES['file'], instance.file, form, request).file_search()
            
            message = u'Скачать результат подбора вы можете по ссылке: \n %s' \
                      % 'http://analogpro.ru/' + file_response.url
            try:
                send_email_with_connection(
                    'Результат подбора',
                    message,
                    [request.user.email])
            except SMTPDataError as e:
                pass
            return JsonResponse({'OK': True, 'file': file_response.url})
        else:
            return JsonResponse({'OK': False, 'error': 'Not valid form'})
            
    else:
        form = SearchFromFile()
        return Http404()
        # return render(request, 'search_from_file.html', {'form': form})


@a_decorator_passing_logs
@login_required(login_url='login/')
def advanced_search(request):
    return redirect('catalog:search')


#  ========================
#  Landing page, new design
#  ========================


@a_decorator_passing_logs
def landing_page_view(request, lang="ru") -> HttpResponse:
    """  The function renders the main project page """
    # https://ianlunn.github.io/Hover/
    if lang not in ("en", "ru"):
        lang = "ru"
        
    feedback_form = FeedBackForm()
    auth_form = MyAuthenticationForm(request)
    reg_form = MyRegistrationForm()
    subscribe_form = SubscribeForm()
    manufacturers = Manufacturer.objects.filter(is_tried=True)
    return render(request, 'index.html', {
        'manufacturers': manufacturers,
        'feedback': feedback_form,
        'auth_form': auth_form,
        'reg_form': reg_form,
        'subscribe_form': subscribe_form,
        'text': trans_text[lang]
    })


@a_decorator_passing_logs
def landing_confirm_mail_page(request, verification_code, user_id) -> HttpResponse:
    """  The function renders the main project page with mail confirmation """
    user = get_object_or_404(models.User, pk=user_id)
    check_code = hashlib.md5('{}'.format(user.pk).encode()).hexdigest()
    feedback_form = FeedBackForm()
    auth_form = MyAuthenticationForm(request)
    reg_form = MyRegistrationForm()
    manufacturers = Manufacturer.objects.all()
    args = {
        'manufacturers': manufacturers,
        'feedback': feedback_form,
        'auth_form': auth_form,
        'reg_form': reg_form,
        'confirm_email': True
    }
    if verification_code == check_code and user:
        user.is_active = True
        user.save()
        login(request, user)
        return render(request, 'index.html', args)
    else:
        args['confirm_email'] = False
        return render(request, 'index.html', args)
