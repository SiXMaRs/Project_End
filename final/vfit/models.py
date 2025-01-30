from django.db import models
from django.contrib.auth.hashers import make_password
from django.utils.timezone import now, make_aware
from datetime import datetime, timedelta


class Users(models.Model):
    full_name = models.CharField(unique=True,max_length=255)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    tel_number = models.CharField(max_length=10)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    sex = models.CharField(max_length=10, choices=[('M', 'Male'), ('F', 'Female')])
    address = models.TextField()
    is_superuser = models.BooleanField(default=False)  #แยก superuser

    def __str__(self):
        return self.full_name

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        from django.contrib.auth.hashers import check_password
        return check_password(raw_password, self.password)
    

class Product(models.Model):
    name = models.CharField(max_length=255)  
    descriptions = models.TextField()  
    category = models.CharField(max_length=255)  
    price = models.IntegerField()  
    image = models.ImageField(upload_to='products/') 
    type = models.CharField(max_length=255, null=True, blank=True)  
    is_available = models.BooleanField(default=True)  

    def __str__(self):
        return self.name

    
class buy_record(models.Model):
    order_code = models.CharField(max_length=8, primary_key=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    amount = models.IntegerField()
    buy_date = models.DateField(auto_now_add=True)
    get_date = models.DateField()
    total_price = models.FloatField()
    user = models.ForeignKey(Users, on_delete=models.CASCADE)
    is_received = models.BooleanField(default=False)  # เพิ่มสถานะ

    def __str__(self):
        return self.order_code

class RentalRecord(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),  # Added new status for rentals that haven't started
        ('renting', 'Renting'),
        ('return', 'Return'),
        ('overdue', 'Overdue'),
        ('returned', 'Returned'),
    ]

    order_code = models.CharField(max_length=50, primary_key=True)
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='rentals')
    user = models.ForeignKey('Users', on_delete=models.CASCADE, related_name='rental_records')
    total_price = models.IntegerField()
    amount = models.IntegerField(default=1)
    ren_time = models.IntegerField()
    get_date = models.DateField()
    return_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    overdue_time = models.IntegerField(default=0)
    time_remaining = models.IntegerField(default=0)

    def update_time_status(self):
        now_time = now().date()
        
        # Convert get_date and return_date to datetime.date if they're strings
        if isinstance(self.get_date, str):
            self.get_date = datetime.strptime(self.get_date, '%Y-%m-%d').date()
        if isinstance(self.return_date, str):
            self.return_date = datetime.strptime(self.return_date, '%Y-%m-%d').date()

        # หยุดการอัปเดตเมื่อสถานะเป็น 'returned'
        if self.status == 'returned':
            self.time_remaining = 0
            self.overdue_time = 0
            self.save()
            return

        # อัปเดตสถานะและเวลาตามวันที่ปัจจุบัน
        if now_time < self.get_date:
            self.status = 'pending'
            self.time_remaining = self.ren_time
            self.overdue_time = 0
        elif now_time == self.get_date:
            self.status = 'renting'
            self.time_remaining = self.ren_time
            self.overdue_time = 0
        elif now_time <= self.return_date:
            self.status = 'renting'
            self.time_remaining = (self.return_date - now_time).days
            self.overdue_time = 0
        else:
            self.status = 'overdue'
            self.time_remaining = 0
            self.overdue_time = (now_time - self.return_date).days
        
        self.save()

class Report(models.Model):
    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]
    rental_code = models.ForeignKey('RentalRecord', on_delete=models.CASCADE, related_name='reports') 
    report_date = models.DateField(auto_now_add=True)  # วันที่รายงาน (อัตโนมัติเมื่อสร้าง)
    issue_description = models.CharField(max_length=255)  # คำอธิบายปัญหา
    status = models.CharField( max_length=50, choices=STATUS_CHOICES, default='in_progress')

    def __str__(self):
        return f"Report {self.id} - Rental: {self.rental_code.order_code} (Status: {self.get_status_display()})"