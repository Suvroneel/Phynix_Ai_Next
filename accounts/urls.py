from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("google/", views.google_login, name="google_login"),
    path("callback/", views.google_callback, name="google_callback"),
    path("oauth-session/", views.store_oauth_session, name="store_oauth_session"),
]
