from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('main/main_page', views.main_page, name='main_page'),
    path('logout/', views.logout_view, name='logout'),
    path('news/', views.news, name='news'),
    path('do/', views.news, name='do'),
]
