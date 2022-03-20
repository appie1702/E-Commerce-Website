from django.urls import path
from . import views
from django.views.generic import TemplateView

app_name = 'ecom'
urlpatterns = [
    path('', views.HomePageView.as_view(), name='ecom_home'),
    path('detail/<slug>/', views.ItemDetailView.as_view(), name='ecom_detail'),
    path('login', views.LoginPage.as_view(), name='ecom_login'),
    path('signup', views.SignUpPage.as_view(), name='ecom_signup'),
    path('logout', views.LogoutPage.as_view(), name='ecom_logout'),
    path('cart', views.CartView.as_view(), name='ecom_cart'),
    path('add_To_cart/<slug>/', views.add_to_cart, name='add_to_cart'),
    path('buy_now/<slug>/', views.buy_now, name='buy_now'),
    path('remove_from_cart/<slug>/', views.remove_from_cart, name='remove_from_cart'),
    path('decrease_quantity/<slug>/', views.decrease_quantity, name='decrease_quantity'),
    path('increase_quantity/<slug>/', views.increase_quantity, name='increase_quantity'),
    path('checkout', views.CheckOutView.as_view(), name='ecom_checkout'),
    path('handle_payment/<int:amount>', views.handle_payment, name='handle_payment'),
    path('payment_success', views.success_payment, name='payment_success'),
    path('add_coupon', views.AddCouponView.as_view(), name='add_coupon'),
    path('request_refund', views.RequestRefundView.as_view(), name='request_refund')
]
