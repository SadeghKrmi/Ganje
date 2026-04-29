from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailBackend(ModelBackend):
    """
    Authenticate users by email address (case-insensitive).

    Falls back gracefully if multiple users share the same email by
    trying each in turn. Email uniqueness is enforced at the form level.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        email = (username or kwargs.get("email") or "").strip().lower()
        if not email or not password:
            return None

        # Try by email first; fall back to username for compatibility
        users = UserModel.objects.filter(email__iexact=email)
        for user in users:
            if user.check_password(password) and self.user_can_authenticate(user):
                return user

        try:
            user = UserModel.objects.get(username__iexact=email)
        except UserModel.DoesNotExist:
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
