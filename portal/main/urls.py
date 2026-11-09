from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('main/main_page', views.main_page, name='main_page'),
    path('logout/', views.logout_view, name='logout'),
    path('employees/', views.employees, name='employees'),
    path('employees/add/', views.add_employee, name='add_employee'),
    path('employees/export/<str:file_format>/', views.export_employees, name='export_employees'),
    path('employees/<int:employee_id>/edit/', views.edit_employee, name='edit_employee'),
    path('employees/<int:employee_id>/deactivate/', views.deactivate_employee, name='deactivate_employee'),
    path('news/', views.news, name='news'),
    path('news/add/', views.add_news, name='add_news'),
    path('news/<int:news_id>/delete/', views.deactivate_news, name='deactivate_news'),
    path('news/<int:news_id>/rate/', views.rate_news, name='rate_news'),
    path('news/<int:news_id>/change/', views.change_news, name='change_news'),
    path('do/', views.do_page, name='do'),
    path('rate/', views.rate_page, name='rate'),
    
]
