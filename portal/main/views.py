from django.shortcuts import render
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.db import transaction
from django.db.models import Count, Q
from django.http import FileResponse, HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST
from .forms import NewsForm#, AudioRatingForm, CallRecordingUploadForm, 
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
def do_page(request):
    calls = Called.objects.filter(user_call=request.user)
    tasks = Task.objects.filter(closed_user_task=request.user)
    return render(request, 'do/do.html', {'calls': calls, 'tasks': tasks})


@login_required(login_url='index')
def news(request):
    return render_news_page(request)


def render_news_page(request, form=None, edit_news=None, edit_form=None, status=200):
    news_list = News.objects.filter(
        Q(is_active=True) | Q(is_active__isnull=True)
    ).select_related('author').annotate(
        like_count=Count('rates', filter=Q(rates__like_news=True), distinct=True),
        dislike_count=Count('rates', filter=Q(rates__dislike_news=True), distinct=True),
    )
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
    return render(request, 'rate/rate.html', {'call_ratings': call_ratings})


# @login_required(login_url='index')
# def record_page(request):
#     if not request.user.is_superuser:
#         return HttpResponseForbidden('Доступ разрешён только суперпользователям.')

#     form = AudioRatingForm(request.POST or None, request.FILES or None)
#     if request.method == 'POST':
#         if form.is_valid():
#             AudioRating.objects.create(
#                 user=form.cleaned_data['target_user'],
#                 audio_file=form.cleaned_data['audio_file'],
#                 rating=form.cleaned_data['rating'],
#             )
#             messages.success(request, 'Файл и оценка сохранены.')
#             return redirect('record')

#     return render(
#         request,
#         'record/record.html',
#         {
#             'form': form,
#             'show_upload_fields': bool(request.POST.get('target_user')),
#         },
#         status=400 if request.method == 'POST' and form.errors else 200,
#     )


# @login_required(login_url='index')
# def upload_call_recording(request):
#     if not request.user.is_superuser:
#         return HttpResponseForbidden('Доступ разрешён только суперпользователям.')

#     form = CallRecordingUploadForm(request.POST or None, request.FILES or None)
#     if request.method == 'POST' and form.is_valid():
#         call = form.cleaned_data['call']
#         recording, created = CallRecording.objects.get_or_create(
#             record_call_id=call.record_call_id,
#             defaults={'audio_file': form.cleaned_data['audio_file']},
#         )
#         if not created:
#             old_file = recording.audio_file
#             recording.audio_file = form.cleaned_data['audio_file']
#             recording.save(update_fields=['audio_file'])
#             old_file.delete(save=False)
#         messages.success(request, 'Запись звонка сохранена.')
#         return redirect('upload_call_recording')

#     return render(
#         request,
#         'record/call_recording_upload.html',
#         {'form': form},
#         status=400 if request.method == 'POST' and form.errors else 200,
#     )


@login_required(login_url='index')
def play_call_recording(request, call_id):
    call = get_object_or_404(
        Called,
        pk=call_id,
        user_call=request.user,
    )
    get_object_or_404(
        CallRate,
        id_call=call,
    )
    recording = get_object_or_404(
        CallRecording,
        record_call_id=call.record_call_id,
    )
    return FileResponse(recording.audio_file.open('rb'), content_type='audio/mpeg')


@login_required(login_url='index')
@require_POST
def add_news(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden('Добавлять новости могут только руководители.')

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