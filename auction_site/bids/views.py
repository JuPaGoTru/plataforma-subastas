import json, html
from django.shortcuts import render, get_object_or_404, redirect
from django.db import transaction, IntegrityError, DatabaseError
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views import View
from django.views.decorators.http import require_http_methods
from django.views.decorators.http import require_POST
from .models import Product, Bid, GuestUser, ChatMessage
from django.utils import timezone


def index(request):
    now = timezone.now()
    
    # Subastas en curso (activas)
    ongoing_auctions = Product.objects.filter(
        start_time__lte=now, 
        end_time__gte=now,
        is_active=True
    ).order_by('end_time')
    
    # Subastas programadas (futuras)
    upcoming_auctions = Product.objects.filter(
        start_time__gt=now,
        is_active=True
    ).order_by('start_time')
    
    # Subastas finalizadas
    finished_auctions = Product.objects.filter(
        end_time__lt=now
    ).order_by('-end_time')
    
    return render(request, 'index.html', {
        'ongoing_auctions': ongoing_auctions,
        'upcoming_auctions': upcoming_auctions,
        'finished_auctions': finished_auctions,
        'now': now
    })

@ensure_csrf_cookie
def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    # Verificar si la subasta aún no ha comenzado
    if product.is_upcoming:
        return render(request, 'auction_upcoming.html', {
            'product': product,
            'time_until_start': product.start_time - timezone.now()
        })
    
    # Verificar sesión de guest para subastas en curso
    if product.is_ongoing and 'username' not in request.session:
        return redirect('join_auction', product_id=product_id)
    
    # Verificar que el usuario guest exista
    if product.is_ongoing:
        try:
            guest_user = GuestUser.objects.get(username=request.session['username'])
        except GuestUser.DoesNotExist:
            if 'username' in request.session:
                del request.session['username']
            return redirect('join_auction', product_id=product_id)
    
    if product.is_silent_auction:
        # Silenciosas: Por monto desc, luego tiempo asc (primero en llegar gana en empate)
        bids = Bid.objects.filter(product=product).select_related('guest_user').order_by('-amount', 'created_at')[:10]
    else:
        # Normales: Por tiempo desc (más reciente primero)
        bids = Bid.objects.filter(product=product).select_related('guest_user').order_by('-created_at')[:10]
    
    return render(request, 'product_detail.html', {
        'product': product,
        'bids': bids,
        'username': request.session.get('username', '')
    })

def join_auction(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    # Asegurarse de que la sesión exista
    if not request.session.session_key:
        request.session.create()
    
    # Si ya está logueado como guest, redirigir directamente a la subasta
    if 'username' in request.session:
        try:
            GuestUser.objects.get(username=request.session['username'])
            return redirect('product_detail', product_id=product_id)
        except GuestUser.DoesNotExist:
            # Limpiar sesión inválida
            if 'username' in request.session:
                del request.session['username']
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        change_user = request.POST.get('change_user', False)
        
        if not username:
            return render(request, 'join_auction.html', {
                'product': product,
                'error': 'Por favor ingresa un nombre de usuario'
            })
        
        try:
            # Verificar si el nombre ya existe (excepto si es el mismo usuario)
            current_username = request.session.get('username', '')
            if username != current_username and GuestUser.objects.filter(username=username).exists():
                return render(request, 'join_auction.html', {
                    'product': product,
                    'error': 'Este nombre de usuario ya está en uso. Por favor elige otro.'
                })
            
            guest_user = None
            
            # Si el usuario actual existe y queremos cambiarlo, actualizarlo
            if change_user and current_username:
                try:
                    old_user = GuestUser.objects.get(username=current_username)
                    old_user.username = username
                    old_user.save()
                    guest_user = old_user
                except GuestUser.DoesNotExist:
                    # Crear nuevo usuario si el antiguo no existe
                    guest_user = GuestUser.objects.create(
                        username=username,
                        session_key=request.session.session_key
                    )
            else:
                # Crear o obtener usuario guest
                guest_user, created = GuestUser.objects.get_or_create(
                    username=username,
                    defaults={'session_key': request.session.session_key}
                )
                
                # Si el usuario ya existía pero no tenía session_key, actualizarlo
                if not created:
                    guest_user.session_key = request.session.session_key
                    guest_user.save()
            
            # Guardar username en sesión
            request.session['username'] = username
            request.session['guest_user_id'] = guest_user.id if guest_user else None
            
            return redirect('product_detail', product_id=product_id)
        
        except IntegrityError:
            # Error de integridad (nombre duplicado por race condition)
            return render(request, 'join_auction.html', {
                'product': product,
                'error': 'Este nombre ya está en uso. Intenta con otro.'
            })
        
        except DatabaseError as e:
            # Error general de base de datos
            return render(request, 'join_auction.html', {
                'product': product,
                'error': 'Error de base de datos. Por favor, intenta más tarde.'
            })
        
        except ValueError as e:
            # Error de validación de datos
            return render(request, 'join_auction.html', {
                'product': product,
                'error': 'Datos inválidos. Por favor, verifica tu información.'
            })
    
    return render(request, 'join_auction.html', {'product': product})

def change_username(request, product_id):
    """Vista para cambiar el nombre de usuario"""
    product = get_object_or_404(Product, id=product_id)
    
    current_username = request.session.get('username', '')
    
    # Si no hay usuario en sesión, redirigir a join
    if not current_username:
        return redirect('join_auction', product_id=product_id)
    
    if request.method == 'POST':
        new_username = request.POST.get('new_username', '').strip()
        
        if not new_username:
            return render(request, 'change_username.html', {
                'product': product,
                'error': 'Por favor ingresa un nuevo nombre de usuario'
            })
         
        # Si el nombre es el mismo, no hacer nada
        if new_username == current_username:
            return redirect('product_detail', product_id=product_id)
        
        # Verificar si el nuevo nombre ya existe
        if GuestUser.objects.filter(username=new_username).exists():
            return render(request, 'change_username.html', {
                'product': product,
                'error': 'Este nombre de usuario ya está en uso. Por favor elige otro.'
            })
        
        try:
            # Obtener el usuario actual y actualizar su nombre
            guest_user = GuestUser.objects.get(username=current_username)
            guest_user.username = new_username
            guest_user.save()
            
            # Actualizar la sesión
            request.session['username'] = new_username
            
            return redirect('product_detail', product_id=product_id)
        
        except GuestUser.DoesNotExist:
            # Si el usuario no existe, redirigir a join en lugar de crear uno nuevo
            # (Es más seguro porque indica que la sesión está corrupta)
            if 'username' in request.session:
                del request.session['username']
            return redirect('join_auction', product_id=product_id)
        
        except IntegrityError:
            # Error de integridad (nombre duplicado por race condition)
            return render(request, 'change_username.html', {
                'product': product,
                'current_username': current_username,
                'error': 'Este nombre ya está en uso. Intenta con otro.'
            })
        
        except DatabaseError:
            # Error general de base de datos
            return render(request, 'change_username.html', {
                'product': product,
                'current_username': current_username,
                'error': 'Error de base de datos. Por favor, intenta más tarde.'
            })
    
    return render(request, 'change_username.html', {
        'product': product,
        'current_username': current_username
    })


@require_http_methods(["GET"])
def get_bids_data(request, product_id):
    product = Product.objects.get(id=product_id)
    
    #Manejo de subastas silenciosas
    if product.is_silent_auction:
        # Si la subasta está en curso, solo mostrar la puja del usuario actual
        if product.is_ongoing:
            username = request.session.get('username')
            
            if username:
                try:
                    guest_user = GuestUser.objects.get(username=username)
                    user_bid = Bid.get_user_latest_bid(product, guest_user)
                    
                    if user_bid:
                        return JsonResponse({
                            'bids': [{
                                'user': 'Tu puja actual',
                                'amount': user_bid.amount,
                                'amount_formatted': user_bid.amount_formatted,
                                'time': user_bid.created_at.strftime('%H:%M:%S'),
                                'is_own_bid': True
                            }],
                            'current_price': product.starting_price,  # Mostrar precio inicial
                            'current_price_formatted': product.starting_price_formatted,
                            'is_silent': True,
                            'is_ongoing': True,
                            'message': '🤫 Subasta silenciosa - Solo ves tu puja'
                        })
                    else:
                        return JsonResponse({
                            'bids': [],
                            'current_price': product.starting_price,
                            'current_price_formatted': product.starting_price_formatted,
                            'is_silent': True,
                            'is_ongoing': True,
                            'message': 'Aún no has pujado'
                        })
                except GuestUser.DoesNotExist:
                    return JsonResponse({
                        'bids': [],
                        'current_price': product.starting_price,
                        'current_price_formatted': product.starting_price_formatted,
                        'is_silent': True,
                        'is_ongoing': True,
                        'message': 'Únete para pujar'
                    })
            
            return JsonResponse({
                'bids': [],
                'current_price': product.starting_price,
                'current_price_formatted': product.starting_price_formatted,
                'is_silent': True,
                'is_ongoing': True,
                'message': 'Subasta silenciosa - Únete para pujar'
            })
        
        # Si la subasta finalizó, mostrar top 10
        elif product.is_finished:
            bids = Bid.objects.filter(
                product_id=product_id
            ).select_related('guest_user').order_by('-amount', 'created_at')[:10]
            
            bids_data = [{
                'user': bid.guest_user.username,
                'amount': bid.amount,
                'amount_formatted': bid.amount_formatted,
                'time': bid.created_at.strftime('%H:%M:%S'),
                'rank': index + 1,
                'is_winner': index == 0
            } for index, bid in enumerate(bids)]
            
            return JsonResponse({
                'bids': bids_data,
                'current_price': product.current_price,
                'current_price_formatted': product.current_price_formatted,
                'is_silent': True,
                'is_ongoing': False,
                'message': '🏆 Subasta finalizada - Top 10 pujas'
            })
    
    # Subasta normal (tu código original)
    bids = Bid.objects.filter(
        product_id=product_id
    ).select_related('guest_user').order_by('-created_at')[:10]
    
    bids_data = [{
        'user': bid.guest_user.username,
        'amount': bid.amount,
        'amount_formatted': bid.amount_formatted,
        'time': bid.created_at.strftime('%H:%M:%S')
    } for bid in bids]
    
    return JsonResponse({
        'bids': bids_data,
        'current_price': product.current_price,
        'current_price_formatted': product.current_price_formatted,
        'is_silent': False
    })

class SubmitBidView(View):
    def post(self, request, product_id):
        try:
            data = json.loads(request.body)
            amount = data.get('amount')
            
            if not amount:
                return JsonResponse({'success': False, 'error': 'Monto de puja no proporcionado.'})
            
            try:
                amount = int(amount)
            except ValueError:
                return JsonResponse({'success': False, 'error': 'Monto inválido.'})
            
            with transaction.atomic():
                product = Product.objects.select_for_update().get(id=product_id)
                
                if not product.is_ongoing:
                    return JsonResponse({
                        'success': False,
                        'error': 'La subasta no está activa.'
                    })
                
                # Obtener usuario
                username = request.session.get('username')
                if not username:
                    return JsonResponse({
                        'success': False,
                        'error': 'Debes unirte a la subasta primero.'
                    })
                
                guest_user = GuestUser.objects.filter(username=username).first()
                if not guest_user:
                    return JsonResponse({
                        'success': False,
                        'error': 'Usuario no encontrado.'
                    })
                
                # 🆕 NUEVO: Lógica para subastas silenciosas
                if product.is_silent_auction:
                    # En subastas silenciosas, validar solo contra precio inicial
                    if amount < product.starting_price:
                        return JsonResponse({
                            'success': False,
                            'error': f'La puja debe ser mayor a {product.starting_price:,}.'
                        })
                    
                    # Validar límite máximo
                    if amount > 512000000:
                        return JsonResponse({
                            'success': False,
                            'error': 'El monto excede el límite permitido.'
                        })
                    
                    # 🆕 NUEVO: Buscar si el usuario ya tiene una puja en esta subasta
                    existing_bid = Bid.objects.filter(
                        product=product,
                        guest_user=guest_user
                    ).first()
                    
                    if existing_bid:
                        # Actualizar puja existente
                        old_amount = existing_bid.amount
                        existing_bid.amount = amount
                        existing_bid.created_at = timezone.now()  # Actualizar timestamp
                        existing_bid.save()
                        
                        # Actualizar current_price si es necesario
                        max_bid = Bid.objects.filter(product=product).order_by('-amount').first()
                        if max_bid:
                            product.current_price = max_bid.amount
                            product.save()
                        
                        return JsonResponse({
                            'success': True,
                            'message': 'Puja actualizada correctamente',
                            'note': f'${old_amount:,} → ${amount:,}',
                            'new_price': amount,
                            'is_silent': True
                        })
                    else:
                        # Crear nueva puja
                        new_bid = Bid.objects.create(
                            product=product,
                            guest_user=guest_user,
                            amount=amount
                        )
                        
                        # Actualizar current_price solo si es la puja más alta
                        if amount > product.current_price:
                            product.current_price = amount
                            product.save()
                        
                        return JsonResponse({
                            'success': True,
                            'message': 'Puja registrada correctamente',
                            'note': 'Puedes modificarla en cualquier momento',
                            'new_price': amount,
                            'is_silent': True
                        })
                
                # 🔄 CÓDIGO ORIGINAL para subastas normales (no tocar)
                if amount <= product.current_price:
                    return JsonResponse({
                        'success': False,
                        'error': f'La puja debe ser mayor a {product.current_price:,}.'
                    })
                
                if amount > 512000000:
                    return JsonResponse({
                        'success': False,
                        'error': 'El monto excede el límite permitido.'
                    })
                
                previous_price = product.current_price
                extended = product.extend_auction_if_needed(amount, previous_price)
                
                new_bid = Bid.objects.create(
                    product=product,
                    guest_user=guest_user,
                    amount=amount
                )
                
                product.current_price = amount
                product.save()
                
                return JsonResponse({
                    'success': True,
                    'new_price': amount,
                    'message': 'Puja realizada con éxito'
                })
                
        except Product.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Producto no encontrado.'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error al procesar la puja: {str(e)}'
            })
        
# Añadir una nueva vista para obtener el estado del producto
@require_http_methods(["GET"])
def get_product_status(request, product_id):
    """Obtener el estado actual del producto para el frontend"""
    try:
        product = get_object_or_404(Product, id=product_id)
        
        return JsonResponse({
            'anti_sniping_active': product.should_show_anti_sniping,
            'time_remaining': product.time_remaining,
            'current_price': product.current_price,
            'is_ongoing': product.is_ongoing,
            'end_time': product.end_time.isoformat(),
            'is_silent_auction': product.is_silent_auction,
        })
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Producto no encontrado'}, status=404)


@require_http_methods(["GET"])
def get_chat_messages(request, product_id):
    """Obtener los últimos mensajes del chat"""
    messages = ChatMessage.objects.filter(product_id=product_id).select_related('guest_user').order_by('-created_at')[:50]
    
    messages_data = [
        {
            'user': msg.guest_user.username,
            'message': msg.message,
            'time': msg.created_at.strftime('%H:%M:%S')
        }
        for msg in messages
    ]
    
    # Invertir el orden para mostrar del más antiguo al más nuevo
    messages_data.reverse()
    
    return JsonResponse({
        'messages': messages_data
    })

@require_http_methods(["POST"])
def send_chat_message(request, product_id):
    """Enviar un nuevo mensaje al chat"""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False, 
            'error': 'Formato de datos inválido.'
        })
    
    message_text = data.get('message', '').strip()
    
    if not message_text:
        return JsonResponse({'success': False, 'error': 'Mensaje vacío'})
    
    # Sanitizar mensaje contra XSS y limitar a 500 caracteres
    message_text = html.escape(message_text)[:500]
    
    # Verificar sesión de guest
    if 'username' not in request.session:
        return JsonResponse({
            'success': False, 
            'error': 'Usuario no identificado. Por favor, únete a la subasta primero.'
        })
    
    username = request.session['username']
    
    try:
        # Obtener producto y usuario
        product = Product.objects.get(id=product_id)
        guest_user = GuestUser.objects.get(username=username)
        
        # Crear nuevo mensaje
        chat_message = ChatMessage.objects.create(
            product=product,
            guest_user=guest_user,
            message=message_text
        )
        
        return JsonResponse({'success': True, 'message': 'Mensaje enviado'})
    
    except Product.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'La subasta no existe.'
        })
    
    except GuestUser.DoesNotExist:
        # Limpiar sesión corrupta
        if 'username' in request.session:
            del request.session['username']
        return JsonResponse({
            'success': False,
            'error': 'Tu sesión ha expirado. Recarga la página y vuelve a unirte.'
        })
    
    except DatabaseError:
        return JsonResponse({
            'success': False,
            'error': 'Error al enviar el mensaje. Intenta de nuevo.'
        })
    
@require_POST
def logout_guest(request, product_id):
    """Cerrar sesión como usuario guest"""
    if 'username' in request.session:
        del request.session['username']
    if 'guest_user_id' in request.session:
        del request.session['guest_user_id']
    
    return redirect('join_auction', product_id=product_id)