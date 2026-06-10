"""Create a superuser + v2 API token in the live DB and print the Bearer key."""
from django.contrib.auth import get_user_model
from users.constants import TOKEN_PREFIX
from users.models import Token

User = get_user_model()
u, _ = User.objects.get_or_create(username="synctester")
u.is_superuser = True
u.save()
Token.objects.filter(user=u).delete()
t = Token.objects.create(user=u)
print(f"BEARER={TOKEN_PREFIX}{t.key}.{t.token}")
