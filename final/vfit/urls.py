from django.urls import path, include
from .views import *

urlpatterns = [
    path("__reload__/", include("django_browser_reload.urls")),

    # mainpage
    path('', home_view, name='home'),
    path('main/', main_view, name='main'),


    # Auth
    path('register/', register, name='register'),
    path('login/', login, name='login'),
    path('logout/', logout, name='logout'),
    path('reset_password/', reset_password, name='reset_password'),
    path('reset_password_confirm/', reset_password_confirm, name='reset_password_confirm'),


    #NavToProfile
    path('redirect-profile/', redirect_profile, name='redirect_profile'),


    # User
    path('profile/', profile, name='profile'),
    path('delete-address/', delete_address, name='delete_address'),
    path('edit-address/', edit_address, name='edit_address'),
    path('shop/',shop, name="shop"),
    path('product/<int:pk>/',shop_detail, name='shop_detail'),

    path('rental/product/<int:pk>/', rental_detail, name='rental_detail'),
    path('rental/confirm-view/<int:pk>/', rental_confirm, name='rental_confirm'),
    path('save_address/', save_address, name='save_address'),
    path('delete-address/', shop_delete_address, name='shop_delete_address'),
    path('edit-address/', shop_edit_address, name='shop_edit_address'),
   
    path('shop/confirm/<int:product_id>/', shop_confirm, name='shop_confirm'),
    path('create-order/', create_order, name='create_order'),

    path('user_buy', user_buy_history, name='user_buy' ),
    path('user_rental', user_rental_history, name='user_rental' ),
    path('report/', report_issue, name='report_issue'),


    # Admin
    path('dashboard/', dashboard, name='dashboard'),

    path('add-product/', add_product, name='add_product'),
    path('delete-product/<int:product_id>/', delete_product, name='delete_product'),
    path('edit-product/', edit_product, name='edit_product'),

    path('buy-history/', buy_history, name='buy_history'),
    path('buy-history/status/<str:order_code>/received/', received, name='received'),
    path('buy-history/status/<str:order_code>/not-received/', not_received, name='not_received'),

    path('rental-list/', admin_rental_list, name='admin_rental_list'),
    
    path('report-list', report_list, name='report_list'),


    #Exercise
    path('exercise/', exercise_view, name='exercise'),
]
