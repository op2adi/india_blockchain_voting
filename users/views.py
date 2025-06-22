from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .forms import VoterRegistrationForm
from .models import Voter, Constituency

def register_view(request):
    if request.method == 'POST':
        form = VoterRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Registration successful. Please log in.')
            return redirect('users:login')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = VoterRegistrationForm()
    return render(request, 'users/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        voter_id = request.POST.get('voter_id')
        password = request.POST.get('password')
        # We need to authenticate using the voter_id field
        user = authenticate(request, voter_id=voter_id, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, 'You have successfully logged in.')
            return redirect('users:profile')
        else:
            messages.error(request, 'Invalid voter ID or password.')
    return render(request, 'users/login.html')

@login_required
def profile_view(request):
    return render(request, 'users/profile.html', {'user': request.user})

def logout_view(request):
    logout(request)
    messages.info(request, "You have successfully logged out.")
    return redirect('users:login')

def get_constituencies(request):
    """API endpoint to get constituencies for a state"""
    state_id = request.GET.get('state')
    if not state_id:
        return JsonResponse([], safe=False)
    
    constituencies = Constituency.objects.filter(state_id=state_id).values('id', 'name')
    return JsonResponse(list(constituencies), safe=False)
