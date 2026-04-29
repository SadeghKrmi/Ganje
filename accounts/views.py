from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required, login_not_required
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from .forms import EmailAuthenticationForm, ProfileForm, StyledPasswordChangeForm


@login_not_required
@never_cache
def login_view(request):
    if request.user.is_authenticated:
        return redirect("artifact_list")

    if request.method == "POST":
        form = EmailAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            if not form.cleaned_data.get("remember_me"):
                request.session.set_expiry(0)  # browser session
            else:
                request.session.set_expiry(60 * 60 * 24 * 30)  # 30 days
            next_url = request.GET.get("next") or request.POST.get("next") or reverse("artifact_list")
            return redirect(next_url)
    else:
        form = EmailAuthenticationForm(request)

    return render(request, "registration/login.html", {
        "form": form,
        "next": request.GET.get("next", ""),
    })


@require_http_methods(["GET", "POST"])
def logout_view(request):
    auth_logout(request)
    messages.success(request, "You have been signed out.")
    return redirect("login")


@login_required
def profile_view(request):
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect("profile")
    else:
        form = ProfileForm(instance=request.user)
    return render(request, "accounts/profile.html", {"form": form})


@login_required
def change_password_view(request):
    if request.method == "POST":
        form = StyledPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Password changed successfully.")
            return redirect("profile")
    else:
        form = StyledPasswordChangeForm(request.user)
    return render(request, "accounts/change_password.html", {"form": form})
