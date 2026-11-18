from django.contrib.auth import authenticate, get_user_model, login, logout
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .audit import AuditMixin, log_action
from .exceptions import Conflict
from .models import AuditLog, CompanyProfile
from .permissions import user_role
from .serializers import AuditLogSerializer, CompanyProfileSerializer, UserSerializer

User = get_user_model()


def me_payload(user):
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.get_full_name() or user.username,
        "email": user.email,
        "role": user_role(user),
    }


@api_view(["GET"])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def csrf(request):
    return Response({"csrfToken": get_token(request)})


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    user = authenticate(
        request, username=request.data.get("username", ""), password=request.data.get("password", "")
    )
    if user is None or not user.is_active:
        return Response(
            {"error": {"code": "invalid_credentials", "status": 400, "message": "Invalid username or password.", "details": {}}},
            status=status.HTTP_400_BAD_REQUEST,
        )
    login(request, user)
    log_action(user, "login", user)
    return Response(me_payload(user))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request):
    log_action(request.user, "logout", request.user)
    logout(request)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me_view(request):
    return Response(me_payload(request.user))


class UserViewSet(AuditMixin, viewsets.ModelViewSet):
    queryset = User.objects.select_related("profile").order_by("username")
    serializer_class = UserSerializer
    admin_only = True
    search_fields = ["username", "first_name", "last_name", "email"]
    filterset_fields = ["is_active"]

    def perform_destroy(self, instance):
        if instance.pk == self.request.user.pk:
            raise Conflict("You cannot delete your own account.")
        super().perform_destroy(instance)


class CompanyProfileView(APIView):
    def get(self, request):
        return Response(CompanyProfileSerializer(CompanyProfile.load()).data)

    def patch(self, request):
        if user_role(request.user) != "admin":
            return Response(
                {"error": {"code": "permission_denied", "status": 403, "message": "Only Admin can edit the company profile.", "details": {}}},
                status=403,
            )
        obj = CompanyProfile.load()
        ser = CompanyProfileSerializer(obj, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        log_action(request.user, "update", obj)
        return Response(ser.data)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related("user")
    serializer_class = AuditLogSerializer
    admin_only = True
    filterset_fields = ["model_name", "action"]
    search_fields = ["object_repr", "model_name"]
