from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", RedirectView.as_view(pattern_name="dashboard:home"), name="root"),
    path("chat/", include("chat.urls", namespace="chat")),
    path("home/", include("dashboard.urls", namespace="dashboard")),
    path("diaries/", include("diaries.urls", namespace="diaries")),
    path("voice/", include("voice.urls", namespace="voice")),
    path("accounts/", include("accounts.urls", namespace="accounts")),
]
