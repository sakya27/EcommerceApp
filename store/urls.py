from django.urls import path

from . import views

urlpatterns = [

	#Leave as empty string for base url
	path('', views.store, name="store"),
	path('cart/', views.cart, name="cart"),
	path('checkout/', views.checkout, name="checkout"),
	path('product_detail/<int:product_id>',views.product_detail, name="product_detail"),
	path('update_item/', views.updateItem, name="update_item"),
	path('process_order/', views.processOrder, name="process_order"),
	path('chat/',views.chat_window,name="chat_window"),
	path('chat/chat_with_product/',views.chat_with_product,name="chat_with_product"),

]