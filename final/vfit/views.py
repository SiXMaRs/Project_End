from django.http import JsonResponse
from django.db import transaction
from django.shortcuts import redirect, render,get_object_or_404
from django.contrib.auth.hashers import check_password
from django.utils.timezone import now
from django.core.paginator import Paginator
from django.core.cache import cache
from django.core.mail import send_mail
from celery import shared_task
from datetime import datetime, timedelta
from django.utils.dateparse import parse_date
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.db.models import Sum, Q
import random, string
import math
import json
from .models import *
from .forms import *

# register&login
def register(request):
    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')

        if password != password_confirm:
            return render(request, 'login_register.html', {'error_register': 'Passwords do not match!'})

        if Users.objects.filter(email=email).exists():
            return render(request, 'login_register.html', {'error_register': 'Email already exists!'})

        user = Users.objects.create(
            full_name=full_name,
            tel_number=phone,
            email=email,
            password=make_password(password)
        )
        user.save()
        return redirect('login')

    return render(request, 'login_register.html')

def login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        try:
            user = Users.objects.get(email=email)
            if check_password(password, user.password):
                request.session['user_id'] = user.id
                return redirect('main')  
            else:
                return render(request, 'login_register.html', {'error_login': 'รหัสผ่านไม่ถูกต้อง'})
        except Users.DoesNotExist:
            return render(request, 'login_register.html', {'error_login': 'ไม่พบผู้ใช้ในระบบ'})

    return render(request, 'login_register.html')

def logout(request):
    request.session.flush() 
    return redirect('login')

def reset_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')

        try:
            user = Users.objects.get(email=email)

            # สร้าง OTP แบบสุ่ม 6 หลัก
            otp = random.randint(100000, 999999)

            # บันทึก OTP ใน Cache (หมดอายุใน 5 นาที)
            cache.set(f'otp_{email}', otp, timeout=300)

            # ส่ง OTP ไปยังอีเมล
            send_mail(
                'Your OTP for Reset Password',
                f'Your OTP code is: {otp}. This code will expire in 5 minutes.',
                'wuttinan0934426621@gmail.com',
                [email],
                fail_silently=False,
            )

            request.session['reset_email'] = email  # เก็บอีเมลไว้ใช้ในขั้นตอนถัดไป
            return redirect('reset_password_confirm')

        except Users.DoesNotExist:
            messages.error(request, 'Email not found!')

    return render(request, 'reset_password.html')


def reset_password_confirm(request):
    email = request.session.get('reset_email')

    if not email:
        messages.error(request, "Session expired! Please request OTP again.")
        return redirect('reset_password') 

    if request.method == 'POST':
        otp_input = request.POST.get('otp')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')

        # ดึง OTP ที่เก็บไว้ใน Cache
        otp_stored = cache.get(f'otp_{email}')
        print(f"Checking OTP for {email}: {otp_stored} (User entered: {otp_input})")  

        if not otp_stored or otp_input != str(otp_stored):
            messages.error(request, 'Invalid or expired OTP!')
            return redirect('reset_password_confirm')  

        if password != password_confirm:
            messages.error(request, 'Passwords do not match!')
            return redirect('reset_password_confirm') 

        try:
            user = Users.objects.get(email=email)
            print(f"User found: {user}")  

            user.set_password(password)
            user.save()

            # ลบ OTP หลังจากใช้งาน
            cache.delete(f'otp_{email}')
            del request.session['reset_email']

            messages.success(request, 'Your password has been reset successfully!')

            print("Redirecting to login page")  # Debug
            return redirect('login')  # Redirect ไปหน้า Login หลังจากเปลี่ยนรหัสผ่านสำเร็จ

        except Users.DoesNotExist:
            messages.error(request, 'Something went wrong. Try again!')
            print("User does not exist in database")  # Debug
            return redirect('reset_password')

    return render(request, 'reset_password_confirm.html')


# mainpage
def home_view(request):
    return render(request, 'home.html')

def main_view(request):
    if 'user_id' not in request.session:
        return redirect('login') 
    
    user_id = request.session['user_id']
    user = Users.objects.get(id=user_id)

    return render(request, 'main.html', {'user': user})

def redirect_profile(request):
    if 'user_id' in request.session: 
        user = Users.objects.get(id=request.session['user_id'])
        if user.is_superuser:
            return redirect('dashboard')
        else:
            return redirect('profile')
    else:
        return redirect('login')

def contact(request):
    if 'user_id' not in request.session:
        return redirect('login')

    user_id = request.session.get('user_id')
    user = Users.objects.filter(id=user_id).first()

    try:
        contact = Contact.objects.get(id=1)
    except Contact.DoesNotExist:
        contact = None  

    context = {
        'contact': contact,
        'user': user  
    }
    return render(request, 'contact.html', context)


def update_contact(request):
    if 'user_id' not in request.session:
        return redirect('login')

    user_id = request.session.get('user_id')
    user = Users.objects.filter(id=user_id).first()
    
    if not user or not user.is_superuser:
        return redirect('contact')

    if request.method == 'POST':
        try:
            contact = Contact.objects.get(id=1)  
        except Contact.DoesNotExist:
            return redirect('contact')  

        # อัปเดตข้อมูล
        contact.email = request.POST.get('email', contact.email)
        contact.facebook = request.POST.get('facebook', contact.facebook)
        contact.instagram = request.POST.get('instagram', contact.instagram)
        contact.line = request.POST.get('line', contact.line)
        contact.phone = request.POST.get('phone', contact.phone)
        contact.address = request.POST.get('address', contact.address)
        contact.save()

        return redirect('contact')

    return redirect('contact')

# user function
def profile(request):
    if 'user_id' not in request.session:
        return redirect('login')  

    user_id = request.session['user_id']
    try:
        user = Users.objects.get(id=user_id)
    except Users.DoesNotExist:
        return redirect('login') 

    if request.method == "POST":
        if 'avatar' in request.FILES:
            user.avatar = request.FILES['avatar']
        
        # อัปเดตข้อมูลทั่วไป
        user.full_name = request.POST.get('full_name', user.full_name)
        user.email = request.POST.get('email', user.email)
        user.tel_number = request.POST.get('tel_number', user.tel_number)
        user.sex = request.POST.get('sex', user.sex)
        
        # อัปเดตที่อยู่จากป๊อปอัป
        if 'new_address_line1' in request.POST:
            user.address = request.POST.get('new_address_line1', user.address)
        
        user.save()
        return redirect('profile')  

    return render(request, 'user/profile.html', {'user': user})

def delete_address(request):
    if 'user_id' not in request.session:
        return redirect('login')

    try:
        user = Users.objects.get(id=request.session['user_id'])
        user.address = ""
        user.save()
        return redirect('profile') 
    except Users.DoesNotExist:
        return redirect('login')

def edit_address(request):
    if 'user_id' not in request.session:
        return redirect('login')

    try:
        user = Users.objects.get(id=request.session['user_id'])
        if request.method == "POST":
            # อัปเดตที่อยู่
            user.address = request.POST.get('edit_address_line1', user.address)
            user.save()
            return redirect('profile')  # กลับไปหน้าโปรไฟล์หลังแก้ไขที่อยู่
    except Users.DoesNotExist:
        return redirect('login')

    return redirect('profile')


def user_rental_history(request):
    if 'user_id' not in request.session:
        return redirect('login')

    user_id = request.session['user_id']
    try:
        user = Users.objects.get(id=user_id)
    except Users.DoesNotExist:
        return redirect('login')

    rentals = RentalRecord.objects.filter(user_id=user_id).select_related('product')

    # อัปเดตสถานะเวลา
    for rental in rentals:
        rental.update_time_status()

    # กรองข้อมูลตามสถานะ
    status = request.GET.get('status', 'all')
    if status == 'pending':
        rentals = rentals.filter(status='pending')
    elif status == 'renting':
        rentals = rentals.filter(status='renting')
    elif status == 'overdue':
        rentals = rentals.filter(status__in=['returned', 'overdue'])

    # ✅ ใช้ Paginator (5 รายการต่อหน้า)
    paginator = Paginator(rentals, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,  # ใช้แทน rental_history
        'user': user,
        'status': status,   
    }
    return render(request, 'user/user_rental.html', context)


def user_buy_history(request):
    if 'user_id' not in request.session:
        return redirect('login')  

    user_id = request.session['user_id']
    try:
        user = Users.objects.get(id=user_id)
    except Users.DoesNotExist:
        return redirect('login')

    # รับค่าหมวดหมู่จาก URL parameter (ค่าเริ่มต้นคือ 'all')
    status = request.GET.get('status', 'all')

    # ดึงข้อมูลการซื้อของผู้ใช้
    buy_history = buy_record.objects.filter(user_id=user_id).select_related('product')

    # กรองข้อมูลตามหมวดหมู่ที่เลือก
    if status == 'pending':  # อุปกรณ์ที่ยังไม่ได้รับ
        buy_history = buy_history.filter(is_received=False)

    # ใช้ Paginator เพื่อแบ่งหน้า
    paginator = Paginator(buy_history, 5)  # 5 รายการต่อหน้า
    page_number = request.GET.get('page')  # กำหนดเลขหน้า
    page_obj = paginator.get_page(page_number)

    context = {
        'buy_history': page_obj,  # ส่ง page_obj ไปที่ template
        'user': user,
        'status': status,  # ส่งไปใช้กับ Template
    }
    return render(request, 'user/user_buy.html', context)


def report_issue(request):
    if 'user_id' not in request.session:
        return redirect('login')

    user_id = request.session['user_id']
    try:
        user = Users.objects.get(id=user_id)
    except Users.DoesNotExist:
        return redirect('login')

    # ดึงเฉพาะอุปกรณ์ที่มีสถานะเป็น "renting"
    rental_records = RentalRecord.objects.filter(user_id=user_id, status="renting")

    if request.method == 'POST':
        rental_code_id = request.POST.get('rental_code')
        issue_description = request.POST.get('issue_description')

        if not rental_code_id or not issue_description:
            messages.error(request, 'กรุณากรอกข้อมูลให้ครบถ้วน')
            return redirect('report_issue')

        try:
            rental_record = RentalRecord.objects.get(order_code=rental_code_id)

            Report.objects.create(
                rental_code=rental_record,
                issue_description=issue_description,
                status='in_progress'
            )
            messages.success(request, 'แจ้งปัญหาสำเร็จแล้ว')
        except RentalRecord.DoesNotExist:
            messages.error(request, 'ไม่พบข้อมูลการเช่า')
            return redirect('report_issue')
        except Exception as e:
            messages.error(request, f'เกิดข้อผิดพลาด: {str(e)}')
            return redirect('report_issue')

        return redirect('report_issue')

    reports = Report.objects.filter(rental_code__user_id=user_id).order_by('-status')

    paginator = Paginator(reports, 5)  # 5 รายการต่อหน้า
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'rental_records': rental_records,
        'reports': page_obj,  
        'user': user,
    }
    return render(request, 'user/report.html', context)



# admin function
def dashboard(request):
    if 'user_id' not in request.session:
        return redirect('login')

    user_id = request.session['user_id']
    try:
        user = Users.objects.get(id=user_id)
    except Users.DoesNotExist:
        return redirect('login')
    
    today = now().date()
    selected_date = request.GET.get('date', str(today))
    range_type = request.GET.get('range', 'daily')

    try:
        selected_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
    except ValueError:
        selected_date = today  

    total_income = 0
    rental_income = 0
    buy_income = 0
    rental_orders = 0
    buy_orders = 0
    weekly_data = []
    monthly_data = []

    if range_type == "daily":
        rental_income = RentalRecord.objects.filter(get_date=selected_date).aggregate(Sum('total_price'))['total_price__sum'] or 0
        buy_income = buy_record.objects.filter(get_date=selected_date).aggregate(Sum('total_price'))['total_price__sum'] or 0
        rental_orders = RentalRecord.objects.filter(get_date=selected_date).count()
        buy_orders = buy_record.objects.filter(get_date=selected_date).count()
        total_income = rental_income + buy_income

    elif range_type == "weekly":
        start_week = selected_date - timedelta(days=selected_date.weekday())
        for i in range(7):
            day = start_week + timedelta(days=i)
            rental_income_day = RentalRecord.objects.filter(get_date=day).aggregate(Sum('total_price'))['total_price__sum'] or 0
            buy_income_day = buy_record.objects.filter(get_date=day).aggregate(Sum('total_price'))['total_price__sum'] or 0
            rental_orders_day = RentalRecord.objects.filter(get_date=day).count()
            buy_orders_day = buy_record.objects.filter(get_date=day).count()

            total_income += rental_income_day + buy_income_day
            rental_income += rental_income_day
            buy_income += buy_income_day
            rental_orders += rental_orders_day
            buy_orders += buy_orders_day

            weekly_data.append({
                'label': day.strftime('%d/%m'),
                'rental_income': rental_income_day,
                'buy_income': buy_income_day,
                'rental_orders': rental_orders_day,
                'buy_orders': buy_orders_day
            })

    elif range_type == "monthly":
        current_year = today.year
        total_income = 0
        rental_income = 0
        buy_income = 0
        rental_orders = 0
        buy_orders = 0

        monthly_data = []
        for i in range(1, 13):
            rental_income_month = RentalRecord.objects.filter(
                get_date__month=i, get_date__year=current_year
            ).aggregate(Sum('total_price'))['total_price__sum'] or 0

            buy_income_month = buy_record.objects.filter(
                get_date__month=i, get_date__year=current_year
            ).aggregate(Sum('total_price'))['total_price__sum'] or 0

            rental_orders_month = RentalRecord.objects.filter(
                get_date__month=i, get_date__year=current_year
            ).count()

            buy_orders_month = buy_record.objects.filter(
                get_date__month=i, get_date__year=current_year
            ).count()

            total_income += rental_income_month + buy_income_month
            rental_income += rental_income_month
            buy_income += buy_income_month
            rental_orders += rental_orders_month
            buy_orders += buy_orders_month

            monthly_data.append({
                'label': datetime.strptime(str(i), "%m").strftime("%B"),
                'rental_income': rental_income_month,
                'buy_income': buy_income_month,
                'rental_orders': rental_orders_month,
                'buy_orders': buy_orders_month
            })

    total_reports = Report.objects.count()

    daily_data = json.dumps({
    "label": selected_date.strftime("%d/%m/%Y"),
    "rental_income": rental_income,
    "buy_income": buy_income,
    "rental_orders": rental_orders if rental_orders else 0,  # ✅ ถ้าไม่มี ให้กำหนดค่าเป็น 0
    "buy_orders": buy_orders if buy_orders else 0  # ✅ ถ้าไม่มี ให้กำหนดค่าเป็น 0
    })

    context = {
        'user': user,
        'selected_date': selected_date.strftime('%Y-%m-%d'),
        'range_type': range_type,
        'total_income': total_income,
        'buy_income': buy_income,
        'rental_income': rental_income,
        'rental_orders': rental_orders,
        'buy_orders': buy_orders,
        'total_reports': total_reports,
        'daily_data': daily_data,  # ✅ ส่ง daily_data เป็น JSON
        'weekly_data': json.dumps(weekly_data) if range_type == "weekly" else "[]",
        'monthly_data': json.dumps(monthly_data) if range_type == "monthly" else "[]",
    }

    return render(request, 'admin/dashboard.html', context)


def admin_rental_list(request):
    if 'user_id' not in request.session:
        return redirect('login')

    user_id = request.session['user_id']
    try:
        user = Users.objects.get(id=user_id)
        if not user.is_superuser:
            return redirect('main')
    except Users.DoesNotExist:
        return redirect('login')

    if request.method == "POST":
        order_code = request.POST.get("order_code")
        rental = RentalRecord.objects.filter(order_code=order_code).first()

        if rental:
            rental.status = "returned"
            rental.save()

    status = request.GET.get('status', 'all')
    rental_records = RentalRecord.objects.select_related('product', 'user').all()

    if status == 'renting':
        rental_records = rental_records.filter(status='renting')
    elif status == 'pending':
        rental_records = rental_records.filter(status='pending')
    elif status == 'returned':
        rental_records = rental_records.filter(status='returned')
    elif status == 'overdue':
        rental_records = rental_records.filter(status='overdue')

    renting_count = RentalRecord.objects.filter(status='renting').count()
    pending_count = RentalRecord.objects.filter(status='pending').count()
    returned_count = RentalRecord.objects.filter(status='returned').count()
    overdue_count = RentalRecord.objects.filter(status='overdue').count()

    paginator = Paginator(rental_records, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'user': user,
        'renting_count': renting_count,
        'pending_count': pending_count,
        'returned_count': returned_count,
        'overdue_count': overdue_count,
        'status': status,
    }

    return render(request, 'admin/rental_history.html', context)


def buy_history(request):
    if 'user_id' not in request.session:
        return redirect('login')

    user_id = request.session['user_id']
    try:
        user = Users.objects.get(id=user_id)
        if not user.is_superuser:
            return redirect('main')
    except Users.DoesNotExist:
        return redirect('login')

    category_filter = request.GET.get('category', '')
    pending_filter = request.GET.get('pending', '')

    orders = buy_record.objects.select_related('product', 'user').order_by('is_received', 'get_date', '-buy_date')

    today = now().date()

    pending_items_count = orders.filter(is_received=False).count()

    if pending_filter == "true":
        orders = orders.filter(is_received=False)

    if category_filter:
        orders = orders.filter(product__category=category_filter)

    paginator = Paginator(orders, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    total_orders = buy_record.objects.count()

    context = {
        'user': user,
        'page_obj': page_obj,
        'total_orders': total_orders,
        'pending_items': pending_items_count,  
        'selected_category': category_filter,
        'pending_filter': pending_filter,
        'buy_history': orders,
    }
    return render(request, 'admin/buy_history.html', context)


def received(request, order_code):
    """เปลี่ยนสถานะเป็น 'มารับสินค้าแล้ว'"""
    order = get_object_or_404(buy_record, order_code=order_code)
    order.is_received = True  # เปลี่ยนสถานะ
    order.save()
    return redirect('buy_history')

def not_received(request, order_code):
    """เปลี่ยนสถานะสินค้าให้กลับมาว่าง"""
    order = get_object_or_404(buy_record, order_code=order_code)
    product = order.product
    product.is_available = True  # คืนสถานะสินค้า
    product.save()
    order.delete() 
    return redirect('buy_history')

def report_list(request):
    if 'user_id' not in request.session:
        return redirect('login')

    user_id = request.session['user_id']
    try:
        user = Users.objects.get(id=user_id)
        if not user.is_superuser:  
            return redirect('main')  
    except Users.DoesNotExist:
        return redirect('login')
    
    reports = Report.objects.all()

    if request.method == 'POST':
        report_id = request.POST.get('report_id')
        action = request.POST.get('action')

        report = get_object_or_404(Report, id=report_id)

        if action == 'complete':
            report.status = 'completed'
            report.save()
            messages.success(request, 'สถานะของการแจ้งซ่อมถูกเปลี่ยนเป็นสำเร็จแล้ว')

    context = {
        'user': user,
        'reports': reports,
        'in_progress_count': reports.filter(status='in_progress').count(),
        'completed_count': reports.filter(status='completed').count(),
    }
    return render(request, 'admin/report_list.html', context)


def add_product(request):
    if 'user_id' not in request.session:
        return redirect('login')

    user_id = request.session['user_id']
    try:
        user = Users.objects.get(id=user_id)
    except Users.DoesNotExist:
        return redirect('login')

    selected_category = request.GET.get('category', '')  # ดึงค่าฟิลเตอร์

    products = Product.objects.filter(is_available=True)
    if selected_category:
        products = products.filter(category=selected_category)

    paginator = Paginator(products, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'admin/productlist.html', {
        'page_obj': page_obj,
        'user': user,
        'total_items': products.count(),
        'rental_items': products.filter(type="เช่ายืม").count(),
        'second_hand_items': products.filter(type="มือสอง").count(),
        'selected_category': selected_category,  # ส่งค่าไป template
    })


def edit_product(request):
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        product = get_object_or_404(Product, id=product_id)

        product.name = request.POST.get('name')
        product.type = request.POST.get('type')
        product.price = request.POST.get('price')
        product.category = request.POST.get('category')
        product.descriptions = request.POST.get('descriptions')

        if 'image' in request.FILES:
            product.image = request.FILES['image']

        product.save()
        return redirect('add_product')


def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.delete()
    return redirect('add_product')  



# shop function
def shop(request):
    if 'user_id' not in request.session:
        return redirect('login')
    
    category = request.GET.get('category', None)
    product_type = request.GET.get('type', None)

    products = Product.objects.filter(is_available=True)
    if category and category != 'ทั้งหมด':  
        products = products.filter(category=category)
    if product_type:
        products = products.filter(type=product_type)

    context = {
        'products': products,
        'current_category': category,
        'current_type': product_type,
    }
    return render(request, 'user/shop.html', context)


def rental_detail(request, pk):
    if 'user_id' not in request.session:
        return redirect('login')
    
    product = get_object_or_404(Product, pk=pk)
    
    rentals = RentalRecord.objects.filter(product=product, status__in=['pending', 'renting'])
    unavailable_periods = [
        {"start_date": rental.get_date.strftime('%Y-%m-%d'), "end_date": rental.return_date.strftime('%Y-%m-%d')}
        for rental in rentals
    ]

    if request.method == 'POST':
        rental_duration = request.POST.get('rental_duration')
        pickup_date = request.POST.get('pickup_date')
        
        if not rental_duration or not pickup_date:
            messages.error(request, 'กรุณาระบุระยะเวลาเช่าและวันที่รับสินค้า')
            return redirect('rental_detail', pk=pk)
        
        try:
            pickup_date_obj = datetime.strptime(pickup_date, '%Y-%m-%d').date()
            current_date = now().date()
            
            # Store rental info in session
            request.session['rental_info'] = {
                'product_id': product.id,
                'rental_duration': rental_duration,
                'pickup_date': pickup_date,
            }
            return redirect('rental_confirm', pk=pk)
            
        except ValueError:
            messages.error(request, 'รูปแบบวันที่ไม่ถูกต้อง')
            return redirect('rental_detail', pk=pk)
    
    return render(request, 'user/rental_detail.html', {
        'product': product,
        'unavailable_periods': unavailable_periods,  
    })

def rental_confirm(request, pk):
    if 'user_id' not in request.session:
        return redirect('login')

    user_id = request.session['user_id']
    try:
        user = Users.objects.get(id=user_id)
    except Users.DoesNotExist:
        return redirect('login')

    rental_info = request.session.get('rental_info')
    if not rental_info:
        return redirect('rental_detail', pk=pk)

    product = get_object_or_404(Product, pk=rental_info['product_id'])
    rental_duration = int(rental_info['rental_duration'])
    pickup_date = rental_info['pickup_date']

    if request.method == 'POST':
        quantity = 1
        total_price = math.ceil((product.price * rental_duration) / 7)

        pickup_date_obj = datetime.strptime(pickup_date, '%Y-%m-%d')
        return_date_obj = pickup_date_obj + timedelta(days=rental_duration)
        order_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

        rental = RentalRecord.objects.create(
            order_code=order_code,
            product=product,
            user_id=user_id,
            total_price=total_price,
            amount=quantity,
            ren_time=rental_duration,
            get_date=pickup_date,
            return_date=return_date_obj.strftime('%Y-%m-%d'),
            status="pending"
        )

        rental.update_time_status()
        del request.session['rental_info']

        return redirect('shop')

    pickup_date_obj = datetime.strptime(pickup_date, '%Y-%m-%d')
    return_date_obj = pickup_date_obj + timedelta(days=rental_duration)
    total_price = math.ceil((product.price * rental_duration) / 7)  # ปัดขึ้น

    preview_data = {
        'quantity': 1,
        'rental_duration': rental_duration,
        'pickup_date': pickup_date,
        'return_date': return_date_obj.strftime('%Y-%m-%d'),
        'total_price': total_price,
    }

    return render(request, 'user/rental_confirm.html', {
        'product': product,
        'rental_record': preview_data,
        'user': user
    })

@csrf_exempt
def save_address(request):
    # ตรวจสอบว่าผู้ใช้ล็อกอินหรือไม่ผ่าน session
    if 'user_id' not in request.session:
        return JsonResponse({'status': 'error', 'message': 'กรุณาเข้าสู่ระบบ'}, status=401)

    if request.method == 'POST':
        try:
            user_id = request.session['user_id']
            data = json.loads(request.body)
            address = data.get('address')

            if not address:
                return JsonResponse({'status': 'error', 'message': 'กรุณากรอกข้อมูลให้ครบถ้วน'}, status=400)

            user = Users.objects.get(id=user_id)
            user.address = address
            user.save()

            return JsonResponse({'status': 'success', 'message': 'ที่อยู่ถูกบันทึกเรียบร้อยแล้ว!'})
        except Users.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'ไม่พบข้อมูลผู้ใช้'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'เกิดข้อผิดพลาด: {str(e)}'}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

@shared_task
def update_rental_records():
    rentals = RentalRecord.objects.filter(status__in=['renting', 'overdue'])
    for rental in rentals:
        rental.update_time_status()


def shop_detail(request, pk):
    if 'user_id' not in request.session:
        return redirect('login')
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'user/shop_detail.html', {'product': product})

def shop_confirm(request, product_id):
    user = None
    if 'user_id' in request.session:
        try:
            user = Users.objects.get(id=request.session['user_id'])
        except Users.DoesNotExist:
            return redirect('login')
    elif request.user.is_authenticated:
        user = request.user

    if not user:
        return redirect('login')

    product = get_object_or_404(Product, id=product_id)
    quantity = int(request.POST.get('quantity', 1))
    pickup_date = request.POST.get('pickup_date')
    total_price = product.price * quantity
    
    context = {
        'product': product,
        'quantity': quantity,
        'pickup_date': pickup_date,
        'total_price': total_price,
        'user': user,
    }
    return render(request, 'user/shop_confirm.html', context)



def create_order(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            product_id = data.get('product_id')
            amount = data.get('amount')
            total_price = data.get('total_price')
            user_id = data.get('user_id')
            pickup_date = data.get('pickup_date')

            if not all([product_id, amount, total_price, user_id, pickup_date]):
                return JsonResponse({'status': 'fail', 'message': 'ข้อมูลไม่ครบถ้วน'}, status=400)

            product = get_object_or_404(Product, id=product_id)
            user = get_object_or_404(Users, id=user_id)

            with transaction.atomic():
                product = Product.objects.select_for_update().get(id=product_id)

                if not product.is_available:
                    return JsonResponse({'status': 'fail', 'message': 'สินค้าหมดแล้ว'}, status=400)

                order_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

                buy_order = buy_record.objects.create(
                    order_code=order_code,
                    product_id=product.id,
                    amount=amount,
                    buy_date=now(),
                    get_date=pickup_date,
                    total_price=total_price,
                    user_id=user.id  
                )

                # อัปเดตสถานะสินค้าให้ถูกจองแล้ว
                product.is_available = False
                product.save()

                return JsonResponse({'status': 'success', 'redirect_url': '/shop/'})
        
        except json.JSONDecodeError as e:
            print("JSON Decode Error:", e)
            return JsonResponse({'status': 'fail', 'message': 'รูปแบบ JSON ไม่ถูกต้อง'}, status=400)
        
        except Exception as e:
            print("Error:", e)
            return JsonResponse({'status': 'fail', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'fail', 'message': 'Invalid request method'}, status=405)


#Exercise function
def exercise_view(request):
    exercises = Exercise.objects.all()  # ดึงข้อมูลท่าออกกำลังกายทั้งหมด
    return render(request, 'exercise/chest.html', {'exercises': exercises})
