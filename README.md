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
```Subastas/
│── bids/ # Aplicación principal de subastas
│ ├── migrations/
│ ├── templates/ # Plantillas HTML
│ ├── static/ # Archivos estáticos
│ ├── routing.py # Rutas para Channels
│ ├── consumers.py # Lógica de WebSockets
│ ├── views.py # Vistas HTTP
│ └── models.py # Modelos principales (Subasta, Oferta, Item, etc.)
│
├── Subastas/ # Configuración global de Django
│ ├── settings.py
│ ├── urls.py
│ └── asgi.py # Configuración de ASGI para Channels
│
├── manage.py
└── requirements.txt
```
---

## ⚙️ Instalación y configuración

### 1. Clonar el repositorio
```bash
git clone https://github.com/tu-usuario/subastas.git
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

Django Channels

WebSockets

HTML, CSS, JavaScript

## 📌 Próximas mejoras
Integrar Redis como backend de Channels para mayor escalabilidad.

Mejorar el frontend con un framework moderno (React / Vue).

Implementar notificaciones push en tiempo real.

Añadir autenticación de usuarios para personalizar la experiencia de puja.

## 👨‍💻 Autor
Proyecto desarrollado por [Tu Nombre].
Este repositorio está pensado como base para sistemas de subastas en tiempo real, adaptable a múltiples escenarios.


---