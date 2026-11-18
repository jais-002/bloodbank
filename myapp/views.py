from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django import forms
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.contrib import messages
from .models import Donor, BloodRequest
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
# Brevo (Sendinblue) API Imports
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required


# --- STEP 1: Custom Signup Form ---
class CustomSignupForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email',)

    def clean_username(self):
        username = self.cleaned_data.get('username', '')
        if ' ' in username:
            raise forms.ValidationError("Username cannot contain spaces.")
        return username

    def clean_password1(self):
        password = self.cleaned_data.get('password1', '')
        if ' ' in password:
            raise forms.ValidationError("Password cannot contain spaces.")
        return password

@never_cache
def index(request):
    now = timezone.now().date()
    ninety_days_ago = now - timedelta(days=90)
    donors = Donor.objects.filter(is_available=True).exclude(last_donation_date__gte=ninety_days_ago)

    visible_donors = donors.order_by('-id')[:6]

    # --- THE HANDSHAKE LOGIC ---
    if request.user.is_authenticated:
        cutoff = timezone.now() - timedelta(hours=24)
        for donor in visible_donors:
            req = BloodRequest.objects.filter(requester=request.user, donor=donor).last()
            if req is None:
                donor.my_request_status = None
            elif req.status == 'Rejected' and req.created_at < cutoff:
                # Rejection cooldown expired — allow re-requesting
                donor.my_request_status = None
            else:
                donor.my_request_status = req.status

    blood_compat = [
        {'group': 'A+',  'gives': 'A+, AB+',               'receives': 'A+, A−, O+, O−'},
        {'group': 'A−',  'gives': 'A+, A−, AB+, AB−',      'receives': 'A−, O−'},
        {'group': 'B+',  'gives': 'B+, AB+',               'receives': 'B+, B−, O+, O−'},
        {'group': 'B−',  'gives': 'B+, B−, AB+, AB−',      'receives': 'B−, O−'},
        {'group': 'O+',  'gives': 'A+, B+, O+, AB+',       'receives': 'O+, O−'},
        {'group': 'O−',  'gives': 'Everyone (Universal)',   'receives': 'O− only'},
        {'group': 'AB+', 'gives': 'AB+ only',               'receives': 'Everyone (Universal)'},
        {'group': 'AB−', 'gives': 'AB+, AB−',              'receives': 'A−, B−, O−, AB−'},
    ]

    return render(request, 'home.html', {
        'donors': visible_donors,
        'total_donors': donors.count(),
        'blood_compat': blood_compat,
    })


def signup(request):
    if request.method == "POST":
        form = CustomSignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome {user.username}!")
            return redirect('index')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = CustomSignupForm()
    return render(request, 'signup.html', {'form': form})


@login_required
def register(request):
    """
    Handles Donor Profile creation.
    """
    if request.method == 'POST':
        # --- Server-side eligibility validation ---
        try:
            age = int(request.POST.get('age', 0))
        except (ValueError, TypeError):
            age = 0

        try:
            weight = float(request.POST.get('weight', 0))
        except (ValueError, TypeError):
            weight = 0

        errors = []
        if age < 18 or age > 65:
            errors.append("Age must be between 18 and 65 years to be eligible as a donor.")
        if weight < 45:
            errors.append("Weight must be at least 45 kg to be eligible as a donor.")

        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'register.html')

        Donor.objects.create(
            user=request.user,
            name=request.POST.get('name'),
            phone=request.POST.get('phone'),
            age=request.POST.get('age'),
            gender=request.POST.get('gender'),
            blood_group=request.POST.get('blood_group'),
            district=request.POST.get('district'),
            city=request.POST.get('city'),
            weight=request.POST.get('weight'),
            height=request.POST.get('height'),
            last_donation_date=request.POST.get('last_donation') or None,
            profile_pic=request.FILES.get('profile_pic')
        )
        messages.success(request, "Donor profile created successfully!")
        return redirect('donor_dashboard')
    return render(request, 'register.html')


# --- STEP 3: Request & Notification Logic ---

@login_required
def send_request(request, donor_id):
    """
    Saves request to DB and sends an automated Email via Brevo API.
    """
    if request.method == 'POST':
        donor = Donor.objects.get(id=donor_id)

        # --- 24-hour cooldown guard ---
        cutoff = timezone.now() - timedelta(hours=24)
        existing = BloodRequest.objects.filter(
            requester=request.user, donor=donor
        ).last()

        if existing:
            if existing.status in ('Pending', 'Approved', 'Accepted'):
                messages.error(request, "You already have an active request with this donor.")
                return redirect('index')
            if existing.status == 'Rejected' and existing.created_at >= cutoff:
                messages.error(request, "This donor rejected your request. You can request again after 24 hours.")
                return redirect('index')

        hospital = request.POST.get('hospital_name')
        contact  = request.POST.get('contact_number')

        # 1. Database Record
        BloodRequest.objects.create(
            requester=request.user,
            donor=donor,
            hospital_name=hospital,
            contact_number=contact,
            status='Pending'
        )

        # 2. Brevo API Broadcast
        configuration = sib_api_v3_sdk.Configuration()
        # Use your new API Key here
        configuration.api_key['api-key'] = settings.BREVO_API_KEY

        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": donor.user.email, "name": donor.name}],
            sender={"email": "josephjais21@gmail.com", "name": "Blood Bank App"},
            subject="🚨 URGENT: Blood Request Received",
            html_content=f"""
                <h3>Urgent Blood Request</h3>
                <p>Hello {donor.name},</p>
                <p><b>{request.user.username}</b> needs blood at <b>{hospital}</b>.</p>
                <p><b>Contact:</b> {contact}</p>
                <p>Log in to your dashboard to respond.</p>
            """
        )

        try:
            api_instance.send_transac_email(send_smtp_email)
            messages.success(request, "Request sent and donor notified via email!")
        except ApiException as e:
            print(f"Brevo API Error: {e}")
            messages.info(request, "Request saved to dashboard, but email notification failed.")

        return redirect('index')


# --- STEP 4: Dashboard & Status Management ---

@never_cache
@login_required
def donor_dashboard(request):
    donor_profile = Donor.objects.filter(user=request.user).first()
    if not donor_profile:
        return redirect('register')

    # Corrected: order_by instead of order_back
    incoming_requests = BloodRequest.objects.filter(donor=donor_profile).order_by('-created_at')
    return render(request, 'donor_dashboard.html', {
        'requests': incoming_requests,
        'donor_profile': donor_profile
    })


@login_required
def approve_request(request, request_id):
    req = get_object_or_404(BloodRequest, id=request_id, donor__user=request.user)
    req.status = "Accepted"
    req.save()
    messages.success(request, "Request Approved!")
    return redirect('donor_dashboard')


@login_required
def reject_request(request, request_id):
    req = get_object_or_404(BloodRequest, id=request_id, donor__user=request.user)
    req.status = "Rejected"
    req.save()
    messages.error(request, "Request Rejected.")
    return redirect('donor_dashboard')


@login_required
def confirm_donation(request, request_id):
    """
    Finalizes donation and triggers the 90-day recovery block.
    """
    req = get_object_or_404(BloodRequest, id=request_id, donor__user=request.user)
    req.status = 'Donated'
    req.save()

    donor = req.donor
    donor.last_donation_date = timezone.now().date()
    donor.save()

    messages.success(request, "Donation confirmed! You are now hidden from search for 90 days.")
    return redirect('donor_dashboard')


@login_required
def cancel_approved_request(request, request_id):
    req = get_object_or_404(BloodRequest, id=request_id, donor__user=request.user)
    req.status = 'Cancelled'
    req.save()
    messages.info(request, "Request cancelled.")
    return redirect('donor_dashboard')


@login_required
def my_sent_requests(request):
    from django.utils import timezone
    from datetime import timedelta

    cutoff = timezone.now() - timedelta(hours=24)

    # Fetch all of this user's requests, then filter out expired transient ones.
    # Rules:
    #   • Pending  → only show if created within the last 24 hours
    #   • Rejected → only show if created within the last 24 hours
    #   • All other statuses (Accepted, Donated, Cancelled) → always show
    all_requests = BloodRequest.objects.filter(
        requester=request.user
    ).order_by('-created_at')

    sent_requests = [
        req for req in all_requests
        if req.status not in ('Pending', 'Rejected') or req.created_at >= cutoff
    ]

    return render(request, 'sent_requests.html', {'sent_requests': sent_requests})


@login_required
def clear_request_history(request):
    """Delete ALL requests for the logged-in user regardless of status."""
    if request.method == 'POST':
        BloodRequest.objects.filter(requester=request.user).delete()
        messages.success(request, "All request history cleared successfully.")
    return redirect('my_sent_requests')


@login_required
def toggle_availability(request):
    donor = get_object_or_404(Donor, user=request.user)
    donor.is_available = not donor.is_available
    donor.save()
    status = "Available" if donor.is_available else "Unavailable"
    messages.info(request, f"Your status is now {status}.")
    return redirect('donor_dashboard')


@login_required
def toggle_emergency(request):
    donor = get_object_or_404(Donor, user=request.user)
    donor.is_emergency_available = not donor.is_emergency_available
    donor.save()
    return redirect('donor_dashboard')


def search_blood(request):
    blood_group = request.GET.get('blood_group')
    district = request.GET.get('district')
    city = request.GET.get('city')
    now = timezone.now().date()
    ninety_days_ago = now - timedelta(days=90)

    searched = any([blood_group, district, city])
    results = []

    if searched:
        results = Donor.objects.filter(is_available=True).exclude(last_donation_date__gte=ninety_days_ago)
        if blood_group: results = results.filter(blood_group=blood_group)
        if district: results = results.filter(district__icontains=district)
        if city: results = results.filter(city__icontains=city)

        # --- THE HANDSHAKE LOGIC ---
        if request.user.is_authenticated:
            cutoff = timezone.now() - timedelta(hours=24)
            for donor in results:
                req = BloodRequest.objects.filter(requester=request.user, donor=donor).last()
                if req is None:
                    donor.my_request_status = None
                elif req.status == 'Rejected' and req.created_at < cutoff:
                    # Rejection cooldown expired — allow re-requesting
                    donor.my_request_status = None
                else:
                    donor.my_request_status = req.status

    return render(request, 'search.html', {
        'results': results,
        'searched': searched,
        'query': {'blood_group': blood_group, 'district': district, 'city': city}
    })


@login_required
@never_cache
def edit_profile(request):
    # Fetch the Donor profile for the logged-in user
    donor = get_object_or_404(Donor, user=request.user)

    if request.method == 'POST':
        # Update the DONOR object, not the USER object
        donor.name = request.POST.get('name')
        donor.phone = request.POST.get('phone')
        donor.city = request.POST.get('city')
        donor.district = request.POST.get('district')
        donor.blood_group = request.POST.get('blood_group')

        if request.FILES.get('profile_pic'):
            donor.profile_pic = request.FILES.get('profile_pic')

        donor.save()
        messages.success(request, "Profile updated successfully!")
        return redirect('donor_dashboard')  # Redirect to your donor dashboard

    return render(request, 'edit_profile.html', {'donor': donor})


def about(request):
    return render(request, 'about.html')

# --- STEP 5: Admin Dashboard Logic ---

class CustomLoginView(LoginView):
    template_name = 'login.html'
    
    def get_success_url(self):
        if self.request.user.is_superuser:
            return reverse_lazy('admin_dashboard')
        url = self.get_redirect_url()
        return url or reverse_lazy('index')


@never_cache
@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_dashboard_view(request):
    users = User.objects.all().order_by('-date_joined')
    return render(request, 'admin_dashboard.html', {'users': users})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_reject_user(request, user_id):
    user_obj = get_object_or_404(User, id=user_id)
    user_obj.is_active = False
    user_obj.save()
    messages.error(request, f"User {user_obj.username} has been rejected (deactivated).")
    return redirect('admin_dashboard')


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_accept_user(request, user_id):
    user_obj = get_object_or_404(User, id=user_id)
    user_obj.is_active = True
    user_obj.save()
    messages.success(request, f"User {user_obj.username} has been accepted (activated).")
    return redirect('admin_dashboard')


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_view_profile(request, user_id):
    user_obj = get_object_or_404(User, id=user_id)
    try:
        donor = user_obj.donor
    except Donor.DoesNotExist:
        donor = None
    return render(request, 'admin_user_profile.html', {'user_obj': user_obj, 'donor': donor})
