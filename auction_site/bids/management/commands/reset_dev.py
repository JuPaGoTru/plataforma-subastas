from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection

class Command(BaseCommand):
    help = 'Resetea la base de datos (flush) y crea un superusuario admin/admin123'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-confirm',
            action='store_true',
            help='Salta la confirmación del flush',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('⚠️  ADVERTENCIA: Este comando borrará TODOS los datos!'))
        
        # Confirmación (a menos que se use --skip-confirm)
        if not options['skip_confirm']:
            confirm = input('¿Estás seguro de que quieres continuar? (escribe "yes" para confirmar): ')
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR('❌ Operación cancelada'))
                return
        
        # 1. Hacer flush (borrar todos los datos)
        self.stdout.write(self.style.MIGRATE_HEADING('\n🗑️  Borrando todos los datos...'))
        call_command('flush', '--no-input')
        self.stdout.write(self.style.SUCCESS('✅ Datos borrados exitosamente'))
        
        # 2. Crear superusuario
        self.stdout.write(self.style.MIGRATE_HEADING('\n👤 Creando superusuario...'))
        User = get_user_model()
        
        username = 'LigaMaster'
        email = 'test@test.co'
        password = 'GUBajosRecursos'
        
        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
            self.stdout.write(self.style.SUCCESS(f'✅ Superusuario creado:'))
            self.stdout.write(f'   Username: {username}')
            self.stdout.write(f'   Password: {password}')
            self.stdout.write(f'   Email: {email}')
        else:
            self.stdout.write(self.style.WARNING('⚠️  El superusuario ya existe'))
        
        # 3. Resumen final
        self.stdout.write(self.style.SUCCESS('\n🎉 ¡Reset completado!'))
        self.stdout.write(self.style.MIGRATE_HEADING('\n🚀 Iniciando servidor de desarrollo...\n'))
        
        # 4. Iniciar servidor
        call_command('runserver')
