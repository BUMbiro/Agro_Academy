from rest_framework.pagination import PageNumberPagination


class CustomPagination(PageNumberPagination):
    """Кастомная пагинация для курсов и уроков."""
    page_size = 10  # Количество элементов на странице по умолчанию
    page_size_query_param = 'page_size'  # Параметр для изменения размера страницы
    max_page_size = 50  # Максимально допустимый размер страницы
