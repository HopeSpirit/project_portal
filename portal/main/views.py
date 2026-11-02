from django.shortcuts import render
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

# Create your views here.

def index(request):
    if request.user.is_authenticated:
        return redirect('main_page')

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
            return redirect('main_page')
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
def news(request):
    return render(request, 'news/news.html')


@login_required(login_url='index')
def news(request):
    return render(request, 'do/do.html')