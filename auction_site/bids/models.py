from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import datetime

class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    image = models.ImageField(upload_to='products/')
    starting_price = models.IntegerField(default=0)
    current_price = models.IntegerField(default=0)
    start_time = models.DateTimeField(default=timezone.now, db_index=True)
    end_time = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    anti_sniping_active = models.BooleanField(default=False)

    class Meta:
        # ✅ AGREGAR índices compuestos para queries complejas
        indexes = [
            models.Index(fields=['start_time', 'end_time', 'is_active'], name='active_auctions_idx'),
            models.Index(fields=['-end_time'], name='finished_auctions_idx'),
        ]
    
    @property
    def is_upcoming(self):
        """Verifica si la subasta está programada para el futuro"""
        return self.start_time > timezone.now()
    
    @property
    def is_ongoing(self):
        """Verifica si la subasta está en curso"""
        now = timezone.now()
        return self.start_time <= now <= self.end_time
    
    @property
    def is_finished(self):
        """Verifica si la subasta ha finalizado"""
        return self.end_time < timezone.now()
    
    @property
    def status(self):
        """Devuelve el estado de la subasta"""
        if self.is_upcoming:
            return "upcoming"
        elif self.is_ongoing:
            return "ongoing"
        else:
            return "finished"
    
    @property
    def time_remaining(self):
        """Devuelve el tiempo restante en segundos"""
        if self.is_ongoing:
            return (self.end_time - timezone.now()).total_seconds()
        return 0
    
    @property
    def is_in_anti_sniping_period(self):
        """Verifica si está en el período de anti-sniping (últimos 30 segundos)"""
        return self.is_ongoing and self.time_remaining <= 30
    
    @property
    def should_show_anti_sniping(self):
        """
        Determina si debe mostrarse la alerta de anti-sniping.
        Se muestra si:
        1. Quedan <= 30 segundos, O
        2. El modo anti-sniping fue activado por una puja (y aún está en curso)
        """
        if not self.is_ongoing:
            return False
        return self.is_in_anti_sniping_period or self.anti_sniping_active
    
    @property
    def winning_bid(self):
        """Obtiene la puja ganadora"""
        if self.is_finished:
            return self.bid_set.order_by('-amount').first()
        return None
    
    @property
    def winner(self):
        """Obtiene el ganador de la subasta"""
        winning_bid = self.winning_bid
        if winning_bid:
            if winning_bid.user:
                return winning_bid.user.username
            else:
                return winning_bid.guest_user.username
        return None
    
    @property
    def current_price_formatted(self):
        """Precio actual formateado con separadores de miles"""
        return f"{self.current_price:,}".replace(",", ".")
    
    @property
    def starting_price_formatted(self):
        """Precio inicial formateado con separadores de miles"""
        return f"{self.starting_price:,}".replace(",", ".")
    
    def extend_auction_if_needed(self, bid_amount, previous_price):
        """
        Extiende la subasta si es necesario (anti-sniping)
        Solo extiende si el incremento de la puja es de al menos 1,000,000
        NO hace save() - esto lo maneja la vista dentro de la transacción
        """
        increment = bid_amount - previous_price
        if self.is_in_anti_sniping_period and increment >= 1000000:
            self.end_time += datetime.timedelta(seconds=30)
            self.anti_sniping_active = True
            return True
        return False
    
    def save(self, *args, **kwargs):
        # Si es un nuevo producto y current_price es 0, establecerlo al starting_price
        if self.current_price == 0 and self.starting_price > 0:
            self.current_price = self.starting_price
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name

class GuestUser(models.Model):
    username = models.CharField(max_length=100, unique=True)
    session_key = models.CharField(max_length=40, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_bid_time = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return self.username
    

class BannedIP(models.Model):
    ip_address = models.CharField(max_length=45, unique=True)  # Soporta IPv6
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.ip_address

class ChatMessage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    guest_user = models.ForeignKey(GuestUser, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.guest_user.username}: {self.message[:50]}"

class Bid(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    guest_user = models.ForeignKey(GuestUser, on_delete=models.CASCADE, null=True, blank=True)
    amount = models.IntegerField()  # Dólares enteros
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    @property
    def amount_formatted(self):
        """Monto de puja formateado con separadores de miles"""
        return f"{self.amount:,}".replace(",", ".")
    
    class Meta:
        ordering = ['-created_at']
        # ✅ Índice compuesto para queries de pujas por producto
        indexes = [
            models.Index(fields=['product', '-created_at'], name='product_bids_idx'),
        ]
    
    def __str__(self):
        if self.user:
            return f"{self.user.username} - ${self.amount}"
        else:
            return f"{self.guest_user.username} - ${self.amount}"