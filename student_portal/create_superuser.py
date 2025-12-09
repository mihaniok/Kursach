import os
from django.contrib.auth import get_user_model

User = get_user_model()

email = os.getenv("DJANGO_SUPERUSER_EMAIL", "admin@mail.com")
password = os.getenv("DJANGO_SUPERUSER_PASSWORD", "admin123")

if not User.objects.filter(email=email).exists():
    User.objects.create_superuser(email=email, password=password)
    print(f"Superuser {email} created")
else:
    print("Superuser already exists")
