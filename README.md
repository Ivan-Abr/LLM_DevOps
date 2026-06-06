## Запуск проекта

### Генерация скриптов

```commandline
python agent.py "Spring Boot app with PostgreSQL" --platform gitlab
```
Примеры описаний проектов:

- Python Flask REST API with PostgreSQL and Redis
- Spring Boot microservice with MySQL and Kafka
- Node.js Express API with MongoDB
- FastAPI application with PostgreSQL and Celery workers
- Django web application with PostgreSQL and Nginx
- Go REST API with PostgreSQL
- React frontend with Node.js backend and MongoDB

### Проверка скриптов
```commandline
python -m verify.verifier generated/
```

### Регенерация на основе полученных замечаний с проверки

Базовая регенерация WARN и FAIL
```commandline
python regenerator.py generated/
```

Регенерация только для критичных случаев (WARN)
```commandline
python regenerator.py generated/ --only-failed
```

Регенерация + перепроверка
```commandline
python regenerator.py generated/ --reverify
```
