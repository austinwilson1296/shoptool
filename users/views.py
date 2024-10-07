from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
import logging

# Get an instance of a logger
logger = logging.getLogger(__name__)

def login_user(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        if not username or not password:
            messages.error(request, "Both username and password are required.")
            return redirect('login')

        try:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                if user.is_active:
                    login(request, user)
                    return redirect('home')
                else:
                    messages.error(request, "Your account is inactive. Please contact the administrator.")
                    logger.warning(f"Inactive user {username} attempted to log in.")
            else:
                messages.error(request, "Invalid username or password. Please try again.")
                logger.warning(f"Failed login attempt for username: {username}")

        except Exception as e:
            messages.error(request, "There was an error processing your request. Please try again later.")
            logger.error(f"An error occurred during login attempt for username: {username} - {str(e)}")

        return redirect('login')

    return render(request, 'authentication/login.html', {})

def logout_user(request):
    logout(request)
    messages.success(request, "You were logged out!")
    return redirect('login')
