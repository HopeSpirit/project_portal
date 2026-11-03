from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('main/main_page', views.main_page, name='main_page'),
    path('logout/', views.logout_view, name='logout'),
    path('news/', views.news, name='news'),
    path('news/add/', views.add_news, name='add_news'),
    path('news/<int:news_id>/delete/', views.deactivate_news, name='deactivate_news'),
    path('news/<int:news_id>/rate/', views.rate_news, name='rate_news'),
    path('do/', views.do_page, name='do'),
    path('rate/', views.rate_page, name='rate'),
    
]
