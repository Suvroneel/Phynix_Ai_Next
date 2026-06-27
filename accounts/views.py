"""
accounts/views.py — Supabase auth, session-based (mirrors Streamlit Logout.py)
No Django User model. Auth lives in request.session.
"""
import os
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from django.contrib.auth import logout
from django.conf import settings


def _sb():
    from supabase import create_client
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

def _sb_service():
    from supabase import create_client
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


def login_view(request):
    """GET → show login page. POST → handle login or signup."""
    if request.session.get("user_email"):
        return redirect("dashboard:home")

    if request.method != "POST":
        return render(request, "accounts/login.html", {})

    form_type = request.POST.get("form_type")

    # ── LOGIN ──────────────────────────────────────────────────────
    if form_type == "login":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        try:
            sb = _sb()
            resp = sb.auth.sign_in_with_password({"email": email, "password": password})
            user = resp.user
            if not user:
                return render(request, "accounts/login.html", {"error": "Login failed. Check credentials."})

            # Fetch username from user_credentials
            username = user.user_metadata.get("display_name", email.split("@")[0])
            try:
                cred = _sb_service().table("user_credentials").select("user_name") \
                    .eq("email", email).execute()
                if cred.data:
                    username = cred.data[0]["user_name"]
            except:
                pass

            _store_session(request, user, resp.session, username)
            return redirect("dashboard:home")

        except Exception as e:
            return render(request, "accounts/login.html", {"error": str(e)})

    # ── SIGNUP ─────────────────────────────────────────────────────
    if form_type == "signup":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        confirm = request.POST.get("confirm_password", "")

        if " " in username:
            return render(request, "accounts/login.html",
                          {"error": "Username cannot contain spaces.", "active_tab": "signup"})
        if password != confirm:
            return render(request, "accounts/login.html",
                          {"error": "Passwords do not match.", "active_tab": "signup"})

        try:
            sb = _sb()
            resp = sb.auth.sign_up({
                "email": email,
                "password": password,
                "options": {"data": {"display_name": username}}
            })
            user = resp.user
            if user:
                # Insert into user_credentials
                try:
                    svc = _sb_service()
                    count = svc.table("user_credentials").select("user_id", count="exact").execute().count or 0
                    svc.table("user_credentials").insert({
                        "user_id": count + 1,
                        "email": email,
                        "user_name": username,
                    }).execute()
                except:
                    pass
                return render(request, "accounts/login.html", {
                    "success": f"Account created, {username}! Check your email to verify, then login."
                })
            return render(request, "accounts/login.html",
                          {"error": "Signup failed.", "active_tab": "signup"})
        except Exception as e:
            return render(request, "accounts/login.html",
                          {"error": str(e), "active_tab": "signup"})

    return render(request, "accounts/login.html", {})


def google_login(request):
    """Redirect to Google OAuth via Supabase."""
    try:
        sb = _sb()
        redirect_url = getattr(settings, "GOOGLE_REDIRECT_URL", "http://127.0.0.1:8000/accounts/callback/")
        resp = sb.auth.sign_in_with_oauth({
            "provider": "google",
            "options": {"redirect_to": redirect_url}
        })
        return redirect(resp.url)
    except Exception as e:
        return render(request, "accounts/login.html", {"error": str(e)})


def google_callback(request):
    """Handle Google OAuth callback — Supabase puts tokens in URL fragment."""
    # Tokens come in fragment (#), not query string — JS handles this.
    # This view just serves the page; JS grabs the token and POSTs it.
    return render(request, "accounts/callback.html", {})


@require_POST
def store_oauth_session(request):
    """Called by callback.html JS with access_token from URL fragment."""
    import json
    try:
        data = json.loads(request.body)
        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        if not access_token:
            from django.http import JsonResponse
            return JsonResponse({"error": "No token"}, status=400)

        sb = _sb()
        sb.auth.set_session(access_token, refresh_token)
        user = sb.auth.get_user()
        if not user or not user.user:
            from django.http import JsonResponse
            return JsonResponse({"error": "Invalid token"}, status=400)

        u = user.user
        email = u.email
        username = u.user_metadata.get("full_name", email.split("@")[0])

        # Check / insert user_credentials
        try:
            svc = _sb_service()
            existing = svc.table("user_credentials").select("user_name").eq("email", email).execute()
            if existing.data:
                username = existing.data[0]["user_name"]
            else:
                count = svc.table("user_credentials").select("user_id", count="exact").execute().count or 0
                svc.table("user_credentials").insert({
                    "user_id": count + 1,
                    "email": email,
                    "user_name": username,
                }).execute()
        except:
            pass

        # Build a fake session object
        class FakeSession:
            pass
        sess = FakeSession()
        sess.access_token = access_token
        sess.refresh_token = refresh_token

        _store_session(request, u, sess, username)
        from django.http import JsonResponse
        return JsonResponse({"ok": True})

    except Exception as e:
        from django.http import JsonResponse
        return JsonResponse({"error": str(e)}, status=500)


def logout_view(request):
    try:
        sb = _sb()
        sb.auth.sign_out()
    except:
        pass
    request.session.flush()
    return redirect("accounts:login")


# ── Helpers ───────────────────────────────────────────────────────
def _store_session(request, user, session, username):
    request.session["user_email"] = getattr(user, "email", "")
    request.session["username"] = username
    request.session["access_token"] = getattr(session, "access_token", "")
    request.session["refresh_token"] = getattr(session, "refresh_token", "")
    request.session["logged_in"] = True
    request.session.modified = True
