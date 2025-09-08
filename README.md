# 🎯 Subastas en Tiempo Real

Este proyecto es una aplicación desarrollada en **Django** que permite gestionar **subastas en línea** con actualizaciones en tiempo real.  
Los usuarios pueden ofertar por ítems (cartas de eFootball en este caso), y el sistema maneja la lógica de pujas, control de tiempo y actualización dinámica.

---

## 🚀 Características principales
- Gestión de subastas de distintos ítems (ejemplo: cartas épicas y destacadas).
- Actualización en tiempo real de las pujas mediante **HTTP Polling**.
- Panel de administración de Django para gestionar ítems y subastas.
- Interfaz sencilla para que los usuarios puedan participar fácilmente en las pujas.
- Extensible para distintos escenarios (no limitado a cartas de eFootball).

---

## 📂 Estructura del proyecto
```
subastas_project/
├── .gitignore
├── requirements.txt
├── manage.py
├── auction_site/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── bids/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── tests.py
│   ├── views.py
│   ├── urls.py
│   └── middleware.py
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── product_detail.html
│   ├── join_auction.html
│   └── change_username.html

```
---

## ⚙️ Instalación y configuración

### 1. Clonar el repositorio
```bash
git clone https://github.com/JuPaGoTru/plataforma-subastas.git
cd subastas
```

### 2. Crear entorno virtual e instalar dependencias
```bash
python -m venv venv
source venv/bin/activate  # En Linux / Mac
venv\Scripts\activate     # En Windows


pip install -r requirements.txt
```
### 3. Configurar la base de datos
Por defecto, el proyecto usa SQLite.
Puedes migrar la base de datos con:
```bash
cd .\auction_site\
python manage.py migrate
```
### 4. Crear superusuario
```
python manage.py createsuperuser
```
### 5. Ejecutar el servidor
```
python manage.py runserver
```
El proyecto estará disponible en:
👉 http://127.0.0.1:8000/

## 🔌 WebSockets con Django Channels
Este proyecto está configurado para funcionar con HTTP Polling activo (ya implementado). La idea es configurar el websocket para mayor eficiencia

## 🛠 Tecnologías utilizadas
Python 3.x

Django

HTML, CSS, JavaScript

## 📌 Próximas mejoras
Integrar Redis como backend de Channels para mayor escalabilidad.

Mejorar el frontend con un framework moderno (React / Vue).

Implementar notificaciones push en tiempo real.

Añadir autenticación de usuarios para personalizar la experiencia de puja.

## 👨‍💻 Autor
Proyecto desarrollado por Juan Pablo Gonzalez.
Este repositorio está pensado como base para sistemas de subastas en tiempo real, adaptable a múltiples escenarios.


---