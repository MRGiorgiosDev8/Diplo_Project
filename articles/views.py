from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Article, Comment, Bookmark, Category
from accounts.models import User
from .forms import ArticleForm, CommentForm, ArticleEditForm, BookmarkForm
from django.http import JsonResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DeleteView
from django.urls import reverse_lazy, reverse
from django.utils.html import mark_safe

# Базовый шаблон для отображения статей
BASE_TEMPLATE = 'core/base.html'

# Вывод статей на главной странице
def base_with_articles(request):
    # Получение списка статей, сортированных по дате создания
    articles_list = Article.objects.order_by('-created_at')
    # Создание пагинатора для списка статей
    paginator = Paginator(articles_list, 5)

    # Получение номера страницы
    page = request.GET.get('page', 1)
    try:
        # Получение объектов статей для текущей страницы
        articles = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        # Если страница не является целым числом или пуста, показываем первую страницу
        articles = paginator.page(1)

    # Создание формы для добавления статьи
    article_form = ArticleForm()
    # Создание формы для добавления комментария
    comment_form = CommentForm()
    # Проверка, добавлены ли статьи в закладки текущим пользователем
    user_has_bookmarks = False
    if request.user.is_authenticated:
        user_has_bookmarks = Bookmark.objects.filter(user=request.user, article__in=articles_list).exists()

    # Получение использованных категорий
    used_categories = Article.objects.values_list('category', flat=True).distinct()
    categories = Category.objects.filter(id__in=used_categories)

    # Перенаправление на страницу с отфильтрованными статьями по категории
    if 'category' in request.GET:
        category_id = request.GET['category']
        return redirect('category_articles', category_id=category_id)

    return render(request, BASE_TEMPLATE, {'articles': articles, 'article_form': article_form, 'comment_form': comment_form, 'user_has_bookmarks': user_has_bookmarks, 'categories': categories})

# Отображение деталей статьи
def article_detail(request, pk):
    # Получение статьи по ее идентификатору
    article = get_object_or_404(Article, pk=pk)

    # Проверка, добавлена ли статья в закладки текущим пользователем
    user_has_bookmark = False
    if request.user.is_authenticated:
        user_has_bookmark = article.bookmark_set.filter(user=request.user).exists()

    return render(request, BASE_TEMPLATE, {'article': article, 'user_has_bookmark': user_has_bookmark})

# Добавление новой статьи
@login_required
def add_article(request):
    if request.method == 'POST':
        # Создание формы для добавления статьи
        form = ArticleForm(request.POST, request.FILES)
        if form.is_valid():
            article = form.save(commit=False)
            article.content = mark_safe(form.cleaned_data['content'])
            article.author = request.user
            category_name = form.cleaned_data.get('categories')
            category, created = Category.objects.get_or_create(name=category_name)
            article.category = category
            article.save()

            return redirect('base_with_articles')
    else:
        form = ArticleForm()

    return render(request, 'articles/add_article.html', {'form': form})

# Добавление комментария к статье
@login_required
def add_comment(request, article_id):
    article = get_object_or_404(Article, pk=article_id)

    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.article = article
            comment.author = request.user
            comment.save()

            return redirect('review_article', pk=article.id)
    else:
        form = CommentForm()

    return render(request, 'articles/review_article.html', {'article': article, 'comment_form': form})

# Поставить лайк статье
@login_required
def like_article(request, article_id):
    if request.method == 'POST':
        article = Article.objects.get(pk=article_id)
        user = request.user

        if not article.likes.filter(id=user.id).exists():
            article.likes.add(user)
            article.dislikes.remove(user)
            article.save()

            return JsonResponse({'likes': article.likes.count(), 'dislikes': article.dislikes.count(), 'is_liked': True, 'is_disliked': False})

    return JsonResponse({'error': 'Неверный запрос'})

# Поставить дизлайк статье
@login_required
def dislike_article(request, article_id):
    if request.method == 'POST':
        article = Article.objects.get(pk=article_id)
        user = request.user

        if not article.dislikes.filter(id=user.id).exists():
            article.dislikes.add(user)
            article.likes.remove(user)
            article.save()

            return JsonResponse({'likes': article.likes.count(), 'dislikes': article.dislikes.count(), 'is_liked': False, 'is_disliked': True})

    return JsonResponse({'error': 'Неверный запрос'})

# Получить количество лайков и дизлайков для всех статей пользователя
@login_required
def get_like_dislike_count(request, article_id=None):
    user = request.user
    articles = Article.objects.filter(author=user)

    if article_id:
        article = get_object_or_404(Article, pk=article_id)
        likes = article.likes.count()
        dislikes = article.dislikes.count()
    else:
        likes = sum(article.likes.count() for article in articles)
        dislikes = sum(article.dislikes.count() for article in articles)

    return JsonResponse({'likes': likes, 'dislikes': dislikes, 'total_likes': likes, 'total_dislikes': dislikes})

# Добавить статью в закладки
@login_required()
def add_bookmark(request, article_id):
    article = get_object_or_404(Article, pk=article_id)
    user = request.user

    if not Bookmark.objects.filter(user=user, article=article).exists():
        bookmark = Bookmark(user=user, article=article)
        bookmark.save()

    return redirect('base_with_articles')

# Удалить статью из закладок
@login_required()
def remove_bookmark(request, article_id):
    article = get_object_or_404(Article, pk=article_id)
    user = request.user

    bookmark = Bookmark.objects.filter(user=user, article=article).first()
    if bookmark:
        bookmark.delete()

    return redirect('base_with_articles')

# Показать все закладки пользователя
@login_required()
def user_bookmarks(request):
    bookmarks = Bookmark.objects.filter(user=request.user)
    bookmark_form = BookmarkForm()

    return render(request, 'articles/user_bookmarks.html', {'bookmarks': bookmarks, 'bookmark_form': bookmark_form})

# Поиск статей
def search_articles(request):
    query = request.GET.get('query', '')
    results = []

    if query:
        results = Article.objects.filter(title__icontains=query)

    serialized_results = [
        {
            'id': result.id,
            'title': result.title,
            'content': result.content,
            'author': result.author.username,
            'photo': result.photo.url if result.photo else None,
            'url': reverse('article_detail', args=[result.id])
        }
        for result in results
    ]

    return JsonResponse({'results': serialized_results})

# Показать статью для рецензии
def review_article(request, pk):
    article = get_object_or_404(Article, pk=pk)

    if request.user == article.author:
        pass
    else:
        article.increment_views(request.user)

    user_has_bookmark = False

    if request.user.is_authenticated:
        user_has_bookmark = article.bookmark_set.filter(user=request.user).exists()

    comment_form = CommentForm()

    if request.method == 'POST':
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.article = article
            comment.author = request.user
            comment.save()

            return redirect('review_article', pk=pk)

    comments = Comment.objects.filter(article=article)

    return render(request, 'articles/review_article.html', {'article': article, 'user_has_bookmark': user_has_bookmark, 'comment_form': comment_form, 'comments': comments})

# Показать статьи пользователя
@login_required()
def user_articles(request, user_id):
    user = get_object_or_404(User, id=user_id)
    articles = Article.objects.filter(author=user).order_by('-created_at')

    return render(request, 'articles/user_articles.html', {'user': user, 'articles': articles})

# Класс для удаления статьи
class ArticleDeleteView(LoginRequiredMixin, DeleteView):
    model = Article
    template_name = 'articles/article_confirm_delete.html'

    def get_success_url(self):
        return reverse_lazy('user_articles', kwargs={'user_id': self.request.user.id})

    def get_queryset(self):
        return Article.objects.filter(author=self.request.user)

# Редактирование статьи
@login_required
def edit_article(request, article_id):
    article = get_object_or_404(Article, pk=article_id)
    categories = Category.objects.all()

    if request.method == 'POST':
        form = ArticleEditForm(request.POST, request.FILES, instance=article)
        if form.is_valid():
            article = form.save(commit=False)
            article.content = mark_safe(form.cleaned_data['content'])
            article.save()
            return redirect('review_article', pk=article.id)
    else:
        form = ArticleEditForm(instance=article)

    return render(request, 'articles/edit_article.html', {'form': form, 'article': article, 'categories': categories})

# Показать статьи по категории
def category_articles(request, category_id):
    category = Category.objects.get(id=category_id)
    articles_list = Article.objects.filter(category=category)
    paginator = Paginator(articles_list, 5)
    page = request.GET.get('page', 1)

    try:
        articles = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        articles = paginator.page(1)

    categories = Category.objects.all()

    return render(request, 'articles/category_articles.html', {'articles': articles, 'category': category, 'categories': categories})

# Показать информацию о проекте
def about_project(request):
    return render(request, 'articles/about_project.html')