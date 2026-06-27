from django.urls import path
from . import views
app_name = "diaries"
urlpatterns = [
    path("", views.diary_view, name="diary"),
    path("save/", views.save_entry, name="save_entry"),
    path("bio/", views.update_bio, name="update_bio"),
    path("avatar/", views.set_avatar, name="set_avatar"),
]
