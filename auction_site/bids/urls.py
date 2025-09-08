from django.urls import path
from . import views
from .views import (
    get_bids_data, 
    SubmitBidView, 
    get_chat_messages, 
    send_chat_message,
    change_username, 
    logout_guest,
    get_product_status
)

urlpatterns = [
    path('', views.index, name='index'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('product/<int:product_id>/join/', views.join_auction, name='join_auction'),
    path('api/product/<int:product_id>/bids/', get_bids_data, name='get_bids_data'),
    path('api/product/<int:product_id>/bid/', SubmitBidView.as_view(), name='submit_bid'),
    path('api/product/<int:product_id>/chat/', get_chat_messages, name='get_chat_messages'),
    path('api/product/<int:product_id>/chat/send/', send_chat_message, name='send_chat_message'),
    path('api/product/<int:product_id>/status/', get_product_status, name='get_product_status'),  # Nueva URL
    path('product/<int:product_id>/change-username/', change_username, name='change_username'),
    path('product/<int:product_id>/logout/', logout_guest, name='logout_guest'),
]