from django import forms
from catalog.choices import TYPES_SEARCH
from catalog.models import Manufacturer


# class ProductChangeListForm(forms.ModelForm):
#     # here we only need to define the field we want to be editable
#     attrs_vals = forms.ModelMultipleChoiceField(
#         queryset=FixedAttributeValue.objects.only('title').all(), required=False)


class SearchFromFile(forms.Form):
    file = forms.FileField(label='Файл', required=False)
    manufacturer_from = forms.ModelChoiceField(label='Исходный производитель', empty_label=None, queryset=Manufacturer.objects.all())
    manufacturer_to = forms.ModelChoiceField(label='Необходимый производитель', empty_label=None, queryset=Manufacturer.objects.all())


class SearchForm(forms.Form):
    article = forms.CharField(label='Артикул')
    #cc = forms.ComboField(fields=[forms.CharField(max_length=20), forms.EmailField()])
    manufacturer_from = forms.ModelChoiceField(label='Исходный производитель', empty_label=None, required=False,
                                               queryset=Manufacturer.objects.all())
    manufacturer_to = forms.ModelChoiceField(label='Необходимый производитель', empty_label=None,
                                             queryset=Manufacturer.objects.all())
    advanced_search = forms.BooleanField(label='Расширенный поиск', widget=forms.CheckboxInput, required=False)
    pk = forms.CharField(label='Primary key', required=False)
    

class AdvancedSearchForm(forms.Form):
    article = forms.CharField(label='Артикул', widget=forms.TextInput(attrs={'readonly':'readonly'}))#, disabled=True, required=False)
    # advanced_search = forms.BooleanField(label='Расширенный поиск', widget=forms.CheckboxInput, required=False)
    #forms.CharField()
    # hrd_attrs = forms.ChoiceField(label='hrd attr', choices=('ss', 'gg'), required=False)

    def __init__(self, *args, **kwargs):
        print(kwargs)
        extra_fields = kwargs.pop('extra', 0)
    
        # check if extra_fields exist. If they don't exist assign 0 to them
        # if not extra_fields:
        #     extra_fields = 0
    
        super(AdvancedSearchForm, self).__init__(*args, **kwargs)
        #self.fields['total_input_fields'].initial = extra_fields
    
        for index in extra_fields.keys():
            # generate extra fields in the number specified via extra_fields
            self.fields['extra_field_{index}'.format(index=index)] = \
                forms.ChoiceField(label='{} ({})'.format(extra_fields[index]['title'],
                                                         extra_fields[index]['type_display']),
                                  required=False, choices=extra_fields[index]['choices'])
                                  # choices=TYPES_SEARCH)