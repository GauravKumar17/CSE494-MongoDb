from django.urls import path
from market import views as v
urlpatterns = [
 path('', v.home, name='home'), path('services/', v.services, name='services'),
 path('workers/<str:worker_id>/', v.worker_detail, name='worker_detail'),
 path('workers/<str:worker_id>/book/', v.book, name='book'),
 path('signup/', v.signup, name='signup'), path('login/', v.login, name='login'),
 path('logout/', v.logout, name='logout'), path('dashboard/', v.dashboard, name='dashboard'),
 path('bookings/<str:booking_id>/', v.booking_detail, name='booking_detail'),
 path('bookings/<str:booking_id>/action/', v.booking_action, name='booking_action'),
 path('bookings/<str:booking_id>/review/', v.review, name='review'),
 path('profile/', v.profile, name='profile'), path('community/', v.community, name='community'),
 path('how-it-works/', v.how_it_works, name='how_it_works'),
 path('admin/', v.admin, name='admin'), path('admin/workers/<str:worker_id>/', v.admin_worker, name='admin_worker'),
]
handler404 = 'market.views.not_found'
