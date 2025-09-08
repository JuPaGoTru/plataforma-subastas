from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_http_methods
import json
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
    )
    
    # Subastas programadas (futuras)
    upcoming_auctions = Product.objects.filter(
        start_time__gt=now,
        is_active=True
    ).order_by('start_time')
    
    # Subastas finalizadas
    finished_auctions = Product.objects.filter(
        end_time__lt=now
    ).order_by('-end_time')[:10]  # Últimas 10 finalizadas
    
    return render(request, 'index.html', {
        'ongoing_auctions': ongoing_auctions,
        'upcoming_auctions': upcoming_auctions,
        'finished_auctions': finished_auctions,
        'now': now
    })

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
            
            # Si el usuario actual existe y queremos cambiarlo, actualizarlo
            if change_user and current_username:
                try:
                    old_user = GuestUser.objects.get(username=current_username)
                    old_user.username = username
                    old_user.save()
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
            request.session['guest_user_id'] = guest_user.id if 'guest_user' in locals() else None
            
            return redirect('product_detail', product_id=product_id)
            
        except Exception as e:
            return render(request, 'join_auction.html', {
                'product': product,
                'error': f'Error: {str(e)}'
            })
    
    return render(request, 'join_auction.html', {'product': product})

def change_username(request, product_id):
    """Vista para cambiar el nombre de usuario"""
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        new_username = request.POST.get('new_username', '').strip()
        
        if not new_username:
            return render(request, 'change_username.html', {
                'product': product,
                'error': 'Por favor ingresa un nuevo nombre de usuario'
            })
        
        current_username = request.session.get('username', '')
        
        if not current_username:
            return redirect('join_auction', product_id=product_id)
        
        # Verificar si el nuevo nombre ya existe
        if new_username != current_username and GuestUser.objects.filter(username=new_username).exists():
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
            # Si el usuario no existe, crear uno nuevo
            guest_user = GuestUser.objects.create(
                username=new_username,
                session_key=request.session.session_key
            )
            request.session['username'] = new_username
            request.session['guest_user_id'] = guest_user.id
            
            return redirect('product_detail', product_id=product_id)
    
    return render(request, 'change_username.html', {'product': product})

@csrf_exempt
@require_http_methods(["GET"])
def get_bids_data(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    bids = Bid.objects.filter(product=product).select_related('guest_user').order_by('-created_at')[:10]
    
    bids_data = [
        {
            'user': bid.guest_user.username if bid.guest_user else "Anónimo",
            'amount': bid.amount,  # Ya es entero
            'amount_formatted': bid.amount_formatted,  # ← Añade esto
            'time': bid.created_at.strftime('%H:%M:%S')
        }
        for bid in bids
    ]
    
    return JsonResponse({
        'bids': bids_data,
        'current_price': product.current_price,  # Ya es entero
        'current_price_formatted': product.current_price_formatted  # ← Y esto
    })

@method_decorator(csrf_exempt, name='dispatch')
class SubmitBidView(View):
    def post(self, request, product_id):
        try:
            product = get_object_or_404(Product, id=product_id)
            
            # Verificar si la subasta está en curso
            if not product.is_ongoing:
                if product.is_upcoming:
                    return JsonResponse({'success': False, 'error': 'La subasta aún no ha comenzado'})
                else:
                    return JsonResponse({'success': False, 'error': 'La subasta ha finalizado'})
            
            data = json.loads(request.body)
            amount = int(data.get('amount', 0))
            
            # Verificar tope máximo de 510 millones
            MAX_BID = 510000000
            if amount > MAX_BID:
                return JsonResponse({
                    'success': False, 
                    'error': f'La puja no puede exceder los ${MAX_BID:,}'
                })
            
            # Verificar sesión de guest
            if 'username' not in request.session:
                return JsonResponse({'success': False, 'error': 'Usuario no identificado'})
            
            username = request.session['username']
            guest_user = get_object_or_404(GuestUser, username=username)

            # Verificar tiempo entre pujas (mínimo 2 segundos)
            if guest_user.last_bid_time:
                time_since_last_bid = (timezone.now() - guest_user.last_bid_time).total_seconds()
                if time_since_last_bid < 2:  # 2 segundos mínimo entre pujas
                    time_to_wait = round(2 - time_since_last_bid, 1)
                    return JsonResponse({
                        'success': False, 
                        'error': f'Espera {time_to_wait} segundos antes de hacer otra puja'
                    })
            
            if amount <= product.current_price:
                return JsonResponse({
                    'success': False, 
                    'error': f'La puja debe ser mayor al precio actual (${product.current_price:,})'
                })
            
            # VERIFICACIÓN CORREGIDA: Validar incremento mínimo en modo anti-sniping
            increment = amount - product.current_price
            if product.is_in_anti_sniping_period and increment < 1000000:
                return JsonResponse({
                    'success': False, 
                    'error': f'Modo anti-sniping activado. El incremento debe ser de al menos $1,000,000 (incrementaste ${increment:,})'
            })
            
            # Guardar el precio actual antes de actualizarlo
            previous_price = product.current_price
            
            # Create new bid
            bid = Bid.objects.create(
                product=product,
                guest_user=guest_user,
                amount=amount
            )
            
            # Update product current price
            product.current_price = amount
            
            # Verificar y aplicar anti-sniping si es necesario (usando el precio anterior)
            extended = product.extend_auction_if_needed(amount, previous_price)
            
            # Guardar cambios en el producto
            product.save()
            
            # Actualizar el timestamp de la última puja del usuario
            guest_user.last_bid_time = timezone.now()
            guest_user.save()


            return JsonResponse({
                'success': True, 
                'message': f'Puja de ${amount:,} realizada con éxito',
                'extended': extended,
                'new_end_time': product.end_time.isoformat() if extended else None
            })
            
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Por favor ingresa un número entero válido'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
        
# Añadir una nueva vista para obtener el estado del producto
@csrf_exempt
@require_http_methods(["GET"])
def get_product_status(request, product_id):
    """Obtener el estado actual del producto para el frontend"""
    try:
        product = get_object_or_404(Product, id=product_id)
        
        return JsonResponse({
            'anti_sniping_active': product.anti_sniping_active,
            'time_remaining': product.time_remaining,
            'current_price': product.current_price,
            'is_ongoing': product.is_ongoing,
            'end_time': product.end_time.isoformat()
        })
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Producto no encontrado'}, status=404)


@csrf_exempt
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

@csrf_exempt
@require_http_methods(["POST"])
def send_chat_message(request, product_id):
    """Enviar un nuevo mensaje al chat"""
    try:
        data = json.loads(request.body)
        message_text = data.get('message', '').strip()
        
        if not message_text:
            return JsonResponse({'success': False, 'error': 'Mensaje vacío'})
        
        # Verificar sesión de guest
        if 'username' not in request.session:
            return JsonResponse({'success': False, 'error': 'Usuario no identificado'})
        
        username = request.session['username']
        
        product = get_object_or_404(Product, id=product_id)
        guest_user = get_object_or_404(GuestUser, username=username)
        
        # Crear nuevo mensaje
        chat_message = ChatMessage.objects.create(
            product=product,
            guest_user=guest_user,
            message=message_text
        )
        
        return JsonResponse({'success': True, 'message': 'Mensaje enviado'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
    
@require_POST
def logout_guest(request, product_id):
    """Cerrar sesión como usuario guest"""
    if 'username' in request.session:
        del request.session['username']
    if 'guest_user_id' in request.session:
        del request.session['guest_user_id']
    
    return redirect('join_auction', product_id=product_id)