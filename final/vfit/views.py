from django.http import JsonResponse
from django.shortcuts import redirect, render,get_object_or_404
from django.contrib.auth.hashers import check_password
from django.utils.timezone import now
from django.core.paginator import Paginator
from celery import shared_task
from datetime import datetime, timedelta
from django.contrib import messages
import json
from .models import *
from .forms import *


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
                return render(request, 'login_register.html', {'error_login': 'Invalid credentials!'})
        except Users.DoesNotExist:
            return render(request, 'login_register.html', {'error_login': 'User not found!'})

    return render(request, 'login_register.html')

def logout(request):
    request.session.flush() 
    return redirect('login')


def main_view(request):
    if 'user_id' not in request.session:
        return redirect('login')  # หากไม่ได้ Login ให้กลับไปหน้า Login

    # ดึงข้อมูลผู้ใช้จาก session
    user_id = request.session['user_id']
    user = Users.objects.get(id=user_id)

    return render(request, 'main.html', {'user': user})


def home_view(request):
    return render(request, 'home.html')

def profile(request):
    if 'user_id' not in request.session:
        return redirect('login')  

    # ดึงข้อมูลผู้ใช้จาก session
    user_id = request.session['user_id']
    try:
        user = Users.objects.get(id=user_id)
    except Users.DoesNotExist:
        return redirect('login')  # หากไม่มีผู้ใช้ ให้กลับไปหน้า Login

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


def user_rental_history(request):
    if 'user_id' not in request.session:
        return redirect('login')

    user_id = request.session['user_id']
    try:
        user = Users.objects.get(id=user_id)
    except Users.DoesNotExist:
        return redirect('login')
    rentals = RentalRecord.objects.filter(user_id=user_id).select_related('product')

    now = datetime.now()
    for rental in rentals:
        rental.update_time_status()

    context = {
        'rental_history': rentals,
        'user': user,
        }
    return render(request, 'user/user_rental.html', context)


def user_buy_history(request):
    if 'user_id' not in request.session:
        return redirect('login')  

    user_id = request.session['user_id']  # ดึง user_id จาก session
    try:
        user = Users.objects.get(id=user_id)
    except Users.DoesNotExist:
        return redirect('login')

    # ดึงข้อมูลการสั่งซื้อเฉพาะของ User คนนั้น
    buy_history = buy_record.objects.filter(user_id=user_id).select_related('product')

    context = {
        'buy_history': buy_history,
        'user': user,
    }
    return render(request, 'user/user_buy.html', context)

def dashboard(request):
    if 'user_id' not in request.session:
        return redirect('login')

    user_id = request.session['user_id']
    try:
        user = Users.objects.get(id=user_id)
        if not user.is_superuser:  # ตรวจสอบว่าเป็น superuser หรือไม่
            return redirect('main')  # ถ้าไม่ใช่ superuser ให้กลับไปหน้า login
    except Users.DoesNotExist:
        return redirect('login')

    if request.method == "POST" and 'avatar' in request.FILES:
        user.avatar = request.FILES['avatar']
        user.save()
        return redirect('dashboard')

    return render(request, 'admin/dashboard.html', {'user': user})

def buy_history(request):
    if 'user_id' not in request.session:
        return redirect('login')
    user_id = request.session['user_id']
    try:
        user = Users.objects.get(id=user_id)
        if not user.is_superuser:  # ตรวจสอบว่าเป็น superuser หรือไม่
            return redirect('main')  # ถ้าไม่ใช่ superuser ให้กลับไปหน้า login
    except Users.DoesNotExist:
        return redirect('login')
    
    if request.method == "POST" and 'avatar' in request.FILES:
        user.avatar = request.FILES['avatar']
        user.save()
        return redirect('buy_history')
    
    orders = buy_record.objects.select_related('product', 'user').all()

    # การแบ่งหน้า
    paginator = Paginator(orders, 6)  # กำหนดให้แสดง 6 รายการต่อหน้า
    page_number = request.GET.get('page')  # รับเลขหน้าจาก URL
    page_obj = paginator.get_page(page_number)  # ดึงรายการของหน้าที่เลือก

    # สถิติต่าง ๆ
    total_orders = orders.count()
    pending_items = orders.filter(get_date__gte=now().date(), is_received=False).count()
    
    context = {
        'user': user,
        'page_obj': page_obj,  # ส่ง page_obj ไปยัง template
        'total_orders': total_orders,
        'pending_items': pending_items,
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

def redirect_profile(request):
    if 'user_id' in request.session: 
        user = Users.objects.get(id=request.session['user_id'])
        if user.is_superuser:
            return redirect('dashboard')
        else:
            return redirect('profile')
    else:
        return redirect('login')

def add_product(request):
    if 'user_id' not in request.session:
        return redirect('login')

    user_id = request.session['user_id']
    try:
        user = Users.objects.get(id=user_id)
    except Users.DoesNotExist:
        return redirect('login') 

    if request.method == "POST" and 'avatar' in request.FILES:
        user.avatar = request.FILES['avatar']
        user.save()
        return redirect('add_product')

    if request.method == 'POST':
        name = request.POST.get('name')
        descriptions = request.POST.get('descriptions')
        category = request.POST.get('category')
        price = request.POST.get('price')
        type_ = request.POST.get('type')
        image = request.FILES.get('image')

        product = Product(
            name=name,
            descriptions=descriptions,
            category=category,
            price=price,
            type=type_,
            image=image
        )
        product.save()
        return redirect('add_product')  

    products = Product.objects.filter(is_available=True)

    paginator = Paginator(products, 6) 
    page_number = request.GET.get('page')  # รับเลขหน้าปัจจุบันจาก URL
    page_obj = paginator.get_page(page_number)  # ดึงสินค้าของหน้าที่เลือก

    total_items = products.count()
    rental_items = products.filter(type="เช่ายืม").count()
    second_hand_items = products.filter(type="มือสอง").count()

    return render(request, 'admin/productlist.html', {
        'page_obj': page_obj,  # ส่ง Pagination object ไปยัง template
        'user': user,
        'total_items': total_items,
        'rental_items': rental_items,
        'second_hand_items': second_hand_items,
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




def shop(request):
    if 'user_id' not in request.session:
        return redirect('login')
    
    # รับค่าหมวดหมู่และชนิดสินค้า
    category = request.GET.get('category', None)
    product_type = request.GET.get('type', None)

    # เริ่ม Query
    products = Product.objects.filter(is_available=True)
    if category:
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
    
    if request.method == 'POST':
        rental_duration = request.POST.get('rental_duration')
        pickup_date = request.POST.get('pickup_date')
        
        if not rental_duration or not pickup_date:
            messages.error(request, 'กรุณาระบุระยะเวลาเช่าและวันที่รับสินค้า')
            return redirect('rental_detail', pk=pk)
        
        try:
            pickup_date_obj = datetime.strptime(pickup_date, '%Y-%m-%d').date()
            current_date = now().date()
            
            if pickup_date_obj < current_date:
                messages.error(request, 'ไม่สามารถเลือกวันที่ย้อนหลังได้')
                return redirect('rental_detail', pk=pk)
            
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
    
    return render(request, 'user/rental_detail.html', {'product': product})

def rental_confirm(request, pk):
    if 'user_id' not in request.session:
        return redirect('login')
    
    rental_info = request.session.get('rental_info')
    if not rental_info:
        return redirect('rental_detail', pk=pk)
    
    product = get_object_or_404(Product, pk=rental_info['product_id'])
    rental_duration = int(rental_info['rental_duration'])
    pickup_date = rental_info['pickup_date']
    
    if request.method == 'POST':
        quantity = 1
        # Calculate total price based on duration and daily rate
        total_price = product.price * rental_duration
        
        pickup_date_obj = datetime.strptime(pickup_date, '%Y-%m-%d')
        return_date_obj = pickup_date_obj + timedelta(days=rental_duration)
        
        # Create new rental record
        rental = RentalRecord.objects.create(
            order_code=f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            product=product,
            user_id=request.session['user_id'],
            total_price=total_price,
            amount=quantity,
            ren_time=rental_duration,
            get_date=pickup_date,
            return_date=return_date_obj.strftime('%Y-%m-%d'),
            status="pending"  # Set initial status as pending until pickup date
        )
        
        # Initialize the time status
        rental.update_time_status()
        
        # Clear the session data
        del request.session['rental_info']
        
        # Redirect to success page or shop
        messages.success(request, 'การเช่าสำเร็จ')
        return redirect('shop')
    
    # Calculate return date and total price for preview
    pickup_date_obj = datetime.strptime(pickup_date, '%Y-%m-%d')
    return_date_obj = pickup_date_obj + timedelta(days=rental_duration)
    total_price = product.price * rental_duration
    
    # Prepare rental record data for template
    preview_data = {
        'quantity': 1,
        'rental_duration': rental_duration,
        'pickup_date': pickup_date,
        'return_date': return_date_obj.strftime('%Y-%m-%d'),
        'total_price': total_price,
    }
    
    return render(request, 'user/rental_confirm.html', {
        'product': product,
        'rental_record': preview_data
    })


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

            # ตรวจสอบว่าสินค้าและผู้ใช้งานมีอยู่ในระบบหรือไม่
            product = get_object_or_404(Product, id=product_id)
            user = get_object_or_404(Users, id=user_id)

            import random, string
            order_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

            # บันทึกคำสั่งซื้อ
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


