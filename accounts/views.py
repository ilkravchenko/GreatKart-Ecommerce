from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import RegistrationForm, UserForm, UserProileForm
from .models import Account, UserProfile
from django.contrib import auth
from django.contrib.auth.decorators import login_required

# VERIFICATION EMAIL
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMessage

from carts.views import _cart_id
from carts.models import Cart, CartItem
from orders.models import Order

import requests


# Create your views here.
def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        
        if form.is_valid():
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            email = form.cleaned_data['email']
            phone_number = form.cleaned_data['phone_number']
            password = form.cleaned_data['password']
            username = email.split('@')[0]
            
            user = Account.objects.create_user(first_name=first_name, last_name=last_name, email=email,
                                               password=password, username=username)
            user.phone_number = phone_number
            user.save()
            
            # Create UserProfile
            profile = UserProfile()
            profile.user_id = user.id
            profile.profile_picture = 'default/default-user.png'
            profile.save()
            
            # USER ACTIVATION
            current_site = get_current_site(request)
            mail_subject = 'Please activate your account'
            message = render_to_string('accounts/account_verification_email.html', {
                'user': user,
                'domain': current_site,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user),
            })
            
            to_email = email
            send_email = EmailMessage(mail_subject, message, to=[to_email])
            send_email.send()
            
            # messages.success(request, 'Thank you for registering with us. We have sent you an verification email to your email address [example@ex.com]. Please verify it.')
            
            return redirect('/accounts/login/?command=verification&email='+email)
    else:
    
        form = RegistrationForm()
        
    context = {
        'form': form,
    }
    
    return render(request, 'accounts/register.html', context=context)


def login(request):
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']
        
        user = auth.authenticate(request, email=email, password=password)
        
        if user is not None:
            try:
                cart = Cart.objects.get(cart_id=_cart_id(request))
                is_cart_item_exists = CartItem.objects.filter(cart=cart).exists()
                
                if is_cart_item_exists:
                    cart_item = CartItem.objects.filter(cart=cart)
                    
                    # Getting product variations by cart_id
                    product_variations = []
                    
                    for item in cart_item:
                        variation = item.variations.all()
                        product_variations.append(list(variation))
                        
                    # Get the cart items from the user to access his product variations
                    cart_item = CartItem.objects.filter(user=user)
            
                    # existing variations -> database
                    # current variation -> product_variation
                    # item id -> database
                    
                    existing_variations_list = []
                    id = []
                    
                    for item in cart_item:
                        existing_variations = item.variations.all()
                        existing_variations_list.append(list(existing_variations))
                        id.append(item.id)
                        
                    for pr in product_variations:
                        if pr in existing_variations_list:
                            index = existing_variations_list.index(pr)
                            item_id = id[index]
                            item = CartItem.objects.get(id=item_id)
                            item.quantity += 1
                            item.user = user
                            item.save()
                        else:
                            cart_item = CartItem.objects.filter(cart=cart)
                    
                            for item in cart_item:
                                item.user = user
                                item.save()
            except:
                pass
            auth.login(request, user)
            messages.success(request, 'You are now logged in')
            url = request.META.get('HTTP_REFERER')
            try:
                query = requests.utils.urlparse(url).query
                # next=/cart/checkout/
                params = dict(x.split('=') for x in query.split('&'))
                
                if 'next' in params:
                    next_page = params['next']
                    return redirect(next_page)
            except:
                return redirect('dashboard')
            
        else:
            messages.error(request, 'Invalid login credentails')
            return redirect('login')
    
    return render(request, 'accounts/login.html')


@login_required(login_url = 'login')
def logout(request):
    auth.logout(request)
    messages.success(request, 'You are Loged out')
    
    return redirect('login')


def activate(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = Account._default_manager.get(pk=uid)
    except (TypeError, ValueError, OverflowError, Account.DoesNotExist):
        user = None
        
    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, 'Congratulations! Your account is activated.')
        return redirect('login')
    else:
        messages.error(request, 'Invalid activation link')
        return redirect('register')
    

@login_required(login_url = 'login')
def dashboard(request):
    orders = Order.objects.order_by('-created_at').filter(user_id=request.user.id, is_ordered=True)
    orders_count = orders.count()
    
    context = {
        'orders_count': orders_count,
    }
    
    return render(request, 'accounts/dashboard.html', context=context)


def forgotPassword(request):
    if request.method == 'POST':
        email = request.POST['email']
        
        if Account.objects.filter(email=email).exists():
            user = Account.objects.get(email__exact=email)
            
            # RESET PASSWORD EMAIL
            current_site = get_current_site(request)
            mail_subject = 'Reset your Password'
            message = render_to_string('accounts/reset_password_email.html', {
                'user': user,
                'domain': current_site,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user),
            })
            
            to_email = email
            send_email = EmailMessage(mail_subject, message, to=[to_email])
            send_email.send()
            
            messages.success(request, 'Password reset email has been sent to your email address.')
            return redirect('login')
                        
        else:
            messages.error(request, 'Account with this email does not exist!')
            return redirect('forgotPassword')
    
    return render(request, 'accounts/forgotPassword.html')


def resetpassword_validate(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = Account._default_manager.get(pk=uid)
    except (TypeError, ValueError, OverflowError, Account.DoesNotExist):
        user = None
        
    if user is not None and default_token_generator.check_token(user, token):
        request.session['uid'] = uid
        messages.success(request, 'Please reset your password.')
        
        return redirect('resetPassword')
    else:
        messages.error(request, 'Invalid activation link')
        return redirect('forgotPassword')
    
    
def resetPassword(request):
    if request.method == 'POST':
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']
        
        if password == confirm_password:
           uid = request.session.get('uid')
           user = Account.objects.get(pk=uid)
           user.set_password(password)
           user.save()
           
           messages.success(request, 'Password Reset was successful!')
           return redirect('login')
            
        else:
            messages.error(request, 'Password do not match')
            return redirect('resetPassword')
    else:       
        return render(request, 'accounts/resetPassword.html')
    
    
def my_orders(request):
    orders = Order.objects.filter(user=request.user, is_ordered=True).order_by('-created_at')
    
    context = {
       'orders': orders, 
    }
    
    return render(request, 'accounts/my_orders.html', context=context)


def edit_profile(request):
    userprofile = get_object_or_404(UserProfile, user=request.user)
    
    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=request.user)
        user_profile_form = UserProileForm(request.POST, request.FILES, instance=userprofile)
        if user_form.is_valid() and user_profile_form.is_valid():
            user_form.save()
            user_profile_form.save()
            messages.success(request, 'Your profile has been updated')
            
            return redirect('edit_profile')
    else:
        user_form = UserForm(instance=request.user)
        user_profile_form = UserProileForm(instance=userprofile) 
    
    context = {
        'user_form': user_form,
        'user_profile_form': user_profile_form,
        'userprofile': userprofile,
    }
    
    return render(request, 'accounts/edit_profile.html', context=context)