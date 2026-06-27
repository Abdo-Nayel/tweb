from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from apps.core.activity import log_activity
from apps.pharmacy.models import ActivityLog


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        user = authenticate(request, username=request.POST.get('username'), password=request.POST.get('password'))
        if user:
            login(request, user)
            log_activity(request, ActivityLog.Action.LOGIN, section='النظام', description='تسجيل دخول')
            return redirect('dashboard')
        messages.error(request, 'اسم المستخدم أو كلمة المرور غير صحيحة')
    return render(request, 'users/login.html')


@login_required
def logout_view(request):
    log_activity(request, ActivityLog.Action.LOGOUT, section='النظام', description='تسجيل خروج')
    logout(request)
    return redirect('login')
