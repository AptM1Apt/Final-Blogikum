from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from blog import views as blog_views

# Хендлеры для кастомных страниц ошибок
handler403 = "pages.views.csrf_failure"
handler404 = "pages.views.page_not_found"
handler500 = "pages.views.server_error"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("blog.urls")),
    path("pages/", include("pages.urls")),
    path("auth/", include("django.contrib.auth.urls")),
    path(
        "auth/registration/", blog_views.RegistrationView.as_view(), name="registration"
    ),
    
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
