from django.shortcuts import render
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

# Create your views here.

def index(request):
    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, 'Вы успешно вошли в систему.')
            return redirect('main_page')
        else:
            messages.error(request, 'Неверный логин или пароль.')

        return redirect('index')

    return render(request, 'auth/auth.html')

@login_required(login_url='index')
def main_page(request):
    return render(request, 'main_page/main.html')

