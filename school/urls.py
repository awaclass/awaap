from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('register', views.register, name='register'),
    path('home', views.home, name='home'),
    path('logout', views.user_logout, name='logout'),
    path('post', views.post, name='post'),
    path('search', views.search, name='search'),
    path('postcomment/<uuid:post_id>', views.post_comment, name="post_comment"),
    path('mathematics', views.mathematics, name='mathematics'),
    path('physics', views.physics, name='physics'),
    path('english', views.english, name='english'),
    path('chemistry', views.chemistry, name='chemistry'),
    path('comment_like/<uuid:comment_id>', views.comment_like, name="comment_like"),
    path('open_notify/<int:pk>', views.open_notify, name='open_notify'),
    path('notify', views.notifications, name='notifications'),
    path('follow/<str:username>', views.follow, name='follow'),
    path('like/<uuid:post_id>', views.like, name='like'),
    path('<uuid:post_id>', views.post_detail, name='post_detail'),
    path('student-scores/<str:username>/', views.student_scores_modal, name='student_scores_modal'),
    path('?/<str:username>', views.update_profile, name='update_profile'),

    # ── CBT Exam ──────────────────────────────────────────────────
    path('cbt/',             views.cbt_subjects, name='cbt_subjects'),   # subject picker page
    path('cbt/mathematics/', views.cbt_exam,     name='cbt_exam'),   
    path('cbt/physics/',     views.cbt_physics,    name='cbt_physics'),
    path('cbt/english/',     views.cbt_english,   name='cbt_english'),
    path('cbt/chemistry/',   views.cbt_chemistry, name='cbt_chemistry'),  # ← Chemistry CBT
    path('cbt/submit/',      views.cbt_submit,    name='cbt_submit'),     # score submission
    # ─────────────────────────────────────────────────────────────

    # Live video URLs
    path('live/', views.live_room_list, name='live_room_list'),
    path('live/create/', views.create_live_room, name='create_live_room'),
    path('live/<str:room_name>/', views.live_room, name='live_room'),
    path('live/<str:room_name>/end/', views.end_live_room, name='end_live_room'),
    path('live/<str:room_name>/start/', views.start_live_room, name='start_live_room'),

    # ── Chat Room / Class Discussion URLs ──────────────────────────────
    path('chat/', views.chat_room, name='chat_room'),
    path('chat/create/', views.create_class_post, name='create_class_post'),
    path('chat/post/<uuid:post_id>/', views.chat_post_detail, name='chat_post_detail'),
    path('chat/post/<uuid:post_id>/comment/', views.chat_post_comment, name='chat_post_comment'),
    path('chat/post/<uuid:post_id>/like/', views.chat_post_like, name='chat_post_like'),
    path('chat/comment/<uuid:comment_id>/like/', views.chat_comment_like, name='chat_comment_like'),
    path('chat/post/<uuid:post_id>/resolve/', views.resolve_post, name='resolve_post'),

    # profile must stay LAST – catches any remaining <str:username>
    path('edit-profile/', views.edit_profile, name='awa_edit_profile'),
    path('<str:username>', views.profile, name='profile'),
]