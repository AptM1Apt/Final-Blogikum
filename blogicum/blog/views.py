from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Count

from .models import Post, Category, Comment, User
from .forms import PostForm, CommentForm, \
    CustomUserCreationForm, UserUpdateForm


# Константы
POSTS_PER_PAGE = 10


def annotate_posts_with_comment_count(queryset):
    """Добавляет к queryset постов количество комментариев."""
    return queryset.annotate(comment_count=Count("comments"))


def paginate_queryset(request, queryset, per_page=POSTS_PER_PAGE):
    """Применяет пагинацию к queryset и возвращает page_obj."""
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get("page")
    return paginator.get_page(page_number)


def filter_published_posts(queryset):
    """Фильтрует посты по опубликованности."""
    return queryset.filter(
        is_published=True,
        category__is_published=True,
        pub_date__lte=timezone.now()
    )


def index(request):
    """Главная страница со списком публикаций."""
    post_list = filter_published_posts(Post.objects)
    post_list = (
        post_list.select_related("author", "location", "category")
        .order_by("-pub_date")
    )
    post_list = annotate_posts_with_comment_count(post_list)

    page_obj = paginate_queryset(request, post_list)

    context = {"page_obj": page_obj}
    return render(request, "blog/index.html", context)


def post_detail(request, post_id):
    """Страница отдельной публикации с комментариями."""
    post = get_object_or_404(Post, pk=post_id)

    # Если пользователь не автор - проверяем доступность поста
    if request.user != post.author:
        post = get_object_or_404(
            filter_published_posts(Post.objects),
            pk=post_id,
        )

    comments = post.comments.select_related("author")
    form = CommentForm()

    context = {
        "post": post,
        "form": form,
        "comments": comments,
    }
    return render(request, "blog/detail.html", context)


def category_posts(request, category_slug):
    """Публикации категории с пагинацией."""
    category = get_object_or_404(Category, 
                                 slug=category_slug, 
                                 is_published=True)

    post_list = filter_published_posts(Post.objects.filter(category=category))
    post_list = (
        post_list.select_related("author", "location", "category")
        .order_by("-pub_date")
    )
    post_list = annotate_posts_with_comment_count(post_list)

    page_obj = paginate_queryset(request, post_list)

    context = {
        "category": category,
        "page_obj": page_obj,
    }
    return render(request, "blog/category.html", context)


def profile(request, username):
    """Страница пользователя с его публикациями."""
    profile_user = get_object_or_404(User, username=username)

    # Если это автор - показываем все посты
    if request.user == profile_user:
        post_list = Post.objects.filter(author=profile_user)
    else:
        # Для остальных - только опубликованные
        post_list = filter_published_posts(
            Post.objects.filter(author=profile_user)
        )

    post_list = annotate_posts_with_comment_count(
        post_list.select_related("category", "location").order_by("-pub_date")
    )

    page_obj = paginate_queryset(request, post_list)

    context = {
        "profile": profile_user,
        "page_obj": page_obj,
    }
    return render(request, "blog/profile.html", context)


@login_required
def edit_profile(request):
    """Редактирование профиля пользователя."""
    if request.method == "POST":
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect("blog:profile", username=request.user.username)
    else:
        form = UserUpdateForm(instance=request.user)

    context = {"form": form}
    return render(request, "blog/user.html", context)


class PostCreateView(LoginRequiredMixin, CreateView):
    """Создание новой публикации."""

    model = Post
    form_class = PostForm
    template_name = "blog/create.html"

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("blog:profile", kwargs={"username": self.request.user.username})


class PostUpdateView(LoginRequiredMixin, UpdateView):
    """Редактирование публикации."""

    model = Post
    form_class = PostForm
    template_name = "blog/create.html"
    pk_url_kwarg = "post_id"


    def dispatch(self, request, *args, **kwargs):
        post = self.get_object()
        if post.author != request.user:
            return redirect("blog:post_detail", post_id=post.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse("blog:post_detail", kwargs={"post_id": self.object.pk})


class PostDeleteView(LoginRequiredMixin, DeleteView):
    """Удаление публикации."""

    model = Post
    template_name = "blog/create.html"
    pk_url_kwarg = "post_id"

    def dispatch(self, request, *args, **kwargs):
        post = self.get_object()
        if post.author != request.user:
            return redirect("blog:post_detail", post_id=post.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse(
            "blog:profile", 
            kwargs={"username": self.request.user.username})


@login_required
def add_comment(request, post_id):
    """Добавление комментария."""
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST)

    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()

    return redirect("blog:post_detail", post_id=post_id)


@login_required
def edit_comment(request, post_id, comment_id):
    """Редактирование комментария."""
    comment = get_object_or_404(Comment, pk=comment_id)

    if comment.author != request.user:
        return redirect("blog:post_detail", post_id=post_id)

    form = CommentForm(request.POST or None, instance=comment)

    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("blog:post_detail", post_id=post_id)

    context = {
        "form": form,
        "comment": comment,
    }
    return render(request, "blog/comment.html", context)


@login_required
def delete_comment(request, post_id, comment_id):
    """Удаление комментария."""
    comment = get_object_or_404(Comment, pk=comment_id)

    if comment.author != request.user:
        return redirect("blog:post_detail", post_id=post_id)

    if request.method == "POST":
        comment.delete()
        return redirect("blog:post_detail", post_id=post_id)

    context = {"comment": comment}
    return render(request, "blog/comment.html", context)


class RegistrationView(CreateView):
    """Регистрация нового пользователя."""

    form_class = CustomUserCreationForm
    template_name = "registration/registration_form.html"
    success_url = reverse_lazy("login")