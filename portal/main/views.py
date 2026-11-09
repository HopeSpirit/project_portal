import csv
from io import BytesIO, StringIO
from zipfile import ZIP_DEFLATED, ZipFile
from xml.sax.saxutils import escape

from django.shortcuts import render
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.db import transaction
from django.db.models import Count, Q
from django.http import FileResponse, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST
from .forms import EmployeeCreateForm, EmployeeUpdateForm, NewsForm
from .models import AudioRating, CallRate, Called, CallRecording, News, NewsRate, Task

# Create your views here.

def index(request):
    if request.user.is_authenticated:
        return redirect('news')
        #return redirect('main_page')

    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            next_url = request.POST.get('next', '')
            if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)
            return redirect('news')
            #return redirect('main_page')
        else:
            messages.error(request, 'Неверный логин или пароль.')

        return redirect('index')

    return render(request, 'auth/auth.html')


@login_required(login_url='index')
@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, 'Завтра снова на работу, а пока отдыхай!')
    return redirect('index')


@login_required(login_url='index')
def main_page(request):
    return render(request, 'main_page/main.html')


@login_required(login_url='index')
def employees(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden('Просматривать сотрудников могут только суперпользователи.')

    return render_employee_directory(request)


def render_employee_directory(request, form=None, edit_employee=None, edit_form=None, status=200):
    employees = get_user_model().objects.only(
        'username',
        'first_name',
        'last_name',
        'email',
        'last_login',
        'date_joined',
    ).order_by('username')
    per_page_options = (5, 10, 20, 50, 100)
    requested_per_page = request.GET.get('per_page', '10')
    per_page = int(requested_per_page) if requested_per_page in {str(option) for option in per_page_options} else 10
    employee_list = Paginator(employees, per_page).get_page(request.GET.get('page'))
    return render(
        request,
        'employees/employees.html',
        {
            'employee_list': employee_list,
            'employee_page_range': employee_list.paginator.get_elided_page_range(employee_list.number),
            'employees_per_page': per_page,
            'employees_per_page_options': per_page_options,
            'form': form or EmployeeCreateForm(),
            'edit_employee': edit_employee,
            'edit_form': edit_form or EmployeeUpdateForm(instance=edit_employee),
        },
        status=status,
    )


@login_required(login_url='index')
def export_employees(request, file_format):
    if not request.user.is_superuser:
        return HttpResponseForbidden('Экспортировать сотрудников могут только суперпользователи.')

    if file_format not in ('csv', 'xlsx'):
        return HttpResponseBadRequest('Неподдерживаемый формат файла.')

    columns = (
        ('Логин', 'username'),
        ('Имя', 'first_name'),
        ('Фамилия', 'last_name'),
        ('Электронная почта', 'email'),
        ('Последний вход', 'last_login'),
        ('Дата регистрации', 'date_joined'),
    )
    employees = get_user_model().objects.only(
        *(field for _, field in columns)
    ).order_by('username')
    rows = [tuple(label for label, _ in columns)]
    for employee in employees:
        row = []
        for _, field in columns:
            value = getattr(employee, field)
            if field in ('last_login', 'date_joined'):
                value = timezone.localtime(value).strftime('%d.%m.%Y %H:%M') if value else ''
            row.append(value or '')
        rows.append(tuple(row))

    if file_format == 'csv':
        output = StringIO(newline='')
        csv.writer(output).writerows(rows)
        response = HttpResponse(
            output.getvalue().encode('utf-8-sig'),
            content_type='text/csv; charset=utf-8',
        )
        response['Content-Disposition'] = 'attachment; filename="employees.csv"'
        return response

    output = BytesIO()
    with ZipFile(output, 'w', ZIP_DEFLATED) as workbook:
        workbook.writestr(
            '[Content_Types].xml',
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '</Types>',
        )
        workbook.writestr(
            '_rels/.rels',
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>',
        )
        workbook.writestr(
            'xl/workbook.xml',
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="Сотрудники" sheetId="1" r:id="rId1"/></sheets>'
            '</workbook>',
        )
        workbook.writestr(
            'xl/_rels/workbook.xml.rels',
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            '</Relationships>',
        )
        sheet_rows = []
        for row_number, row in enumerate(rows, start=1):
            cells = []
            for column_number, value in enumerate(row):
                column_name = ''
                number = column_number + 1
                while number:
                    number, remainder = divmod(number - 1, 26)
                    column_name = chr(65 + remainder) + column_name
                cell_ref = f'{column_name}{row_number}'
                cells.append(
                    f'<c r="{cell_ref}" t="inlineStr"><is><t xml:space="preserve">'
                    f'{escape(str(value))}</t></is></c>'
                )
            sheet_rows.append(f'<row r="{row_number}">{"".join(cells)}</row>')
        worksheet = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f'<sheetData>{"".join(sheet_rows)}</sheetData>'
            '</worksheet>'
        )
        workbook.writestr('xl/worksheets/sheet1.xml', worksheet)

    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="employees.xlsx"'
    return response


@login_required(login_url='index')
@require_POST
def add_employee(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden('Добавлять сотрудников могут только суперпользователи.')

    form = EmployeeCreateForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(
            request,
            'Сотрудник добавлен. Установите ему пароль через Django Admin.',
        )
        return redirect('employees')

    return render_employee_directory(request, form=form, status=400)


@login_required(login_url='index')
@require_http_methods(['GET', 'POST'])
def edit_employee(request, employee_id):
    if not request.user.is_superuser:
        return HttpResponseForbidden('Редактировать сотрудников могут только суперпользователи.')

    employee = get_object_or_404(get_user_model(), pk=employee_id)
    form = EmployeeUpdateForm(request.POST or None, instance=employee)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, 'Данные сотрудника обновлены.')
            return redirect('employees')

    return render_employee_directory(
        request,
        edit_employee=employee,
        edit_form=form,
        status=400 if request.method == 'POST' else 200,
    )


@login_required(login_url='index')
@require_POST
def deactivate_employee(request, employee_id):
    if not request.user.is_superuser:
        return HttpResponseForbidden('Отключать сотрудников могут только суперпользователи.')

    employee = get_object_or_404(get_user_model(), pk=employee_id)
    if employee.is_superuser or employee.pk == request.user.pk:
        return HttpResponseForbidden('Нельзя отключить суперпользователя.')

    if employee.is_active:
        employee.is_active = False
        employee.save(update_fields=['is_active'])
        messages.success(request, 'Сотрудник отключён.')
    else:
        messages.info(request, 'Сотрудник уже отключён.')
    return redirect('employees')


@login_required(login_url='index')
def do_page(request):
    calls = Called.objects.select_related('user_call')
    if not request.user.is_superuser:
        calls = calls.filter(user_call=request.user)
    per_page_options = (5, 10, 20, 50, 100)
    requested_per_page = request.GET.get('per_page', '10')
    per_page = int(requested_per_page) if requested_per_page in {str(option) for option in per_page_options} else 10
    calls_page = Paginator(calls, per_page).get_page(request.GET.get('calls_page'))
    tasks = Task.objects.select_related('closed_user_task')
    if not request.user.is_superuser:
        tasks = tasks.filter(closed_user_task=request.user)
    requested_tasks_per_page = request.GET.get('tasks_per_page', '10')
    tasks_per_page = int(requested_tasks_per_page) if requested_tasks_per_page in {str(option) for option in per_page_options} else 10
    tasks_page = Paginator(tasks, tasks_per_page).get_page(request.GET.get('tasks_page'))
    return render(request, 'do/do.html', {
        'calls': calls_page,
        'calls_page': calls_page,
        'calls_page_range': calls_page.paginator.get_elided_page_range(calls_page.number),
        'calls_per_page': per_page,
        'calls_per_page_options': per_page_options,
        'tasks': tasks_page,
        'tasks_page': tasks_page,
        'tasks_page_range': tasks_page.paginator.get_elided_page_range(tasks_page.number),
        'tasks_per_page': tasks_per_page,
    })


@login_required(login_url='index')
def news(request):
    return render_news_page(request)


def render_news_page(request, form=None, edit_news=None, edit_form=None, status=200):
    news_list = News.objects.filter(
        Q(is_active=True) | Q(is_active__isnull=True)
    ).select_related('author').annotate(
        like_count=Count('rates', filter=Q(rates__like_news=True), distinct=True),
        dislike_count=Count('rates', filter=Q(rates__dislike_news=True), distinct=True),
    ).order_by('-create_date', '-pk')
    if not request.user.is_superuser:
        user_votes = NewsRate.objects.filter(author_rate=request.user).order_by('-id')
        votes_by_news = {}
        for news_id, liked, disliked in user_votes.values_list(
            'news_id', 'like_news', 'dislike_news'
        ):
            votes_by_news.setdefault(
                news_id,
                'like' if liked else 'dislike' if disliked else None,
            )
        for item in news_list:
            item.user_vote = votes_by_news.get(item.pk)
    else:
        for item in news_list:
            item.user_vote = None

    return render(
        request,
        'news/news.html',
        {
            'news_list': news_list,
            'is_superuser': request.user.is_superuser,
            'form': form or NewsForm(),
            'edit_news': edit_news,
            'edit_form': edit_form,
        },
        status=status,
    )


@login_required(login_url='index')
def rate_page(request):
    call_ratings = CallRate.objects.filter(
        id_call__user_call=request.user,
    ).select_related('id_call')
    recording_ids = set(
        CallRecording.objects.filter(
            record_call_id__in=call_ratings.values('id_call__record_call_id'),
        ).values_list('record_call_id', flat=True)
    )
    for rating in call_ratings:
        rating.has_recording = bool(
            rating.id_call and rating.id_call.record_call_id in recording_ids
        )
    return render(request, 'rate/rate.html')#, {'call_ratings': call_ratings})



@login_required(login_url='index')
@require_POST
def add_news(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden('Добавлять новости могут только администраторы.')

    form = NewsForm(request.POST)
    if form.is_valid():
        News.objects.create(
            text=form.cleaned_data['text'],
            create_date=timezone.now(),
            author=request.user,
        )
        messages.success(request, 'Новость добавлена.')
        return redirect('news')

    return render_news_page(request, form=form, status=400)


@login_required(login_url='index')
@require_POST
def deactivate_news(request, news_id):
    if not request.user.is_superuser:
        return HttpResponseForbidden('Удалять новости могут только администраторы.')

    news_item = get_object_or_404(News, pk=news_id)
    news_item.is_active = False
    news_item.save(update_fields=['is_active'])
    messages.success(request, 'Новость удалена.')
    return redirect('news')


@login_required(login_url='index')
@require_http_methods(['GET', 'POST'])
def change_news(request, news_id):
    if not request.user.is_superuser:
        return HttpResponseForbidden('Редактировать новости могут только администраторы.')

    news_item = get_object_or_404(News, pk=news_id)
    if request.method == 'GET':
        return render_news_page(
            request,
            edit_news=news_item,
            edit_form=NewsForm(initial={'text': news_item.text}),
        )

    form = NewsForm(request.POST)
    if form.is_valid():
        news_item.text = form.cleaned_data['text']
        news_item.save(update_fields=['text'])
        messages.success(request, 'Новость обновлена.')
        return redirect('news')

    return render_news_page(
        request,
        edit_news=news_item,
        edit_form=form,
        status=400,
    )



@login_required(login_url='index')
@require_POST
def rate_news(request, news_id):
    vote = request.POST.get('vote')
    if vote not in ('like', 'dislike'):
        return HttpResponseBadRequest('нравится или не нравится')

    with transaction.atomic():
        news_item = get_object_or_404(News.objects.select_for_update(), pk=news_id)
        existing_votes = NewsRate.objects.filter(
            author_rate=request.user,
            news=news_item,
        ).order_by('pk')
        existing_vote = existing_votes.first()
        if existing_vote:
            existing_votes.exclude(pk=existing_vote.pk).delete()
            existing_vote.like_news = vote == 'like'
            existing_vote.dislike_news = vote == 'dislike'
            existing_vote.date_rate = timezone.now()
            existing_vote.save(update_fields=['like_news', 'dislike_news', 'date_rate'])
        else:
            NewsRate.objects.create(
                like_news=vote == 'like',
                dislike_news=vote == 'dislike',
                author_rate=request.user,
                date_rate=timezone.now(),
                news=news_item,
            )

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'like_count': NewsRate.objects.filter(news=news_item, like_news=True).count(),
            'dislike_count': NewsRate.objects.filter(news=news_item, dislike_news=True).count(),
            'user_vote': vote,
        })

    #messages.success(request, 'Ваш голос сохранён.')
    return redirect('news')