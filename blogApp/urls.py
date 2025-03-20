from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.index, name="index"),
    path('register/', views.register, name="register"),
    path('login/', views.user_login, name="login"),
    path('logout/', views.logout, name="logout"),
    
    path('blog/<int:post_id>/', views.blog_detail, name="blog_detail"),
    path('profile/<str:username>/', views.profile, name="profile"),

    path('post/add_post/', views.add_post, name="add_post"),
    path('post/update/<int:post_id>/', views.update_post, name='update_post'),
    path('post/delete/<int:post_id>/', views.delete_post, name='delete_post'),
    path('like_post/<int:post_id>/', views.like_post, name='like_post'),
    path('post/<int:post_id>/comment/', views.add_comment, name='add_comment'),
    path('blog/stats/<int:post_id>/', views.get_post_stats, name='get_post_stats'),
    path('profile/<str:username>/update/', views.profile_update, name='profile_update'),
    path('follow/<str:username>/', views.follow_user, name='follow_user'),
    path('unfollow/<str:username>/', views.unfollow_user, name='unfollow_user'),
    path("profile/<str:username>/", views.user_profile, name="user_profile"),
    path('notifications/mark-read/', views.mark_notifications_as_read, name='mark_notifications_as_read'),
    path('chat/<str:username>/', views.chat_page, name='chat_page'),
    path("send_message/", views.send_message, name="send_message"),
    path("get-messages/<str:username>/", views.get_messages, name="get_messages"),
    path("get-new-messages/<str:username>/", views.get_new_messages, name="get_new_messages"),
    path('test-chat-link/', views.test_chat_link, name='test_chat_link'),
    path('post/<int:post_id>/comments/', views.post_comments, name='post_comments'),
    path("send_friend_request/", views.send_friend_request, name="send_friend_request"),
    path("accept_friend_request/<int:request_id>/", views.accept_friend_request, name="accept_friend_request"),
    path("reject_friend_request/<int:request_id>/", views.reject_friend_request, name="reject_friend_request"),
    #path("search_users/", views.search_users, name="search_users"),
    path("search_friends/", views.search_friends_page, name="search_friends"),  # Page for searching
    path("search_friends_ajax/", views.search_friends_ajax, name="search_friends_ajax"),
    path('chat-page/', views.chat_list, name='chat_page'),
    path('chat-page/<str:receiver_username>/', views.chat_list, name='chat_page'),
    path('delete_message/<int:message_id>/', views.delete_message, name='delete_message'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
