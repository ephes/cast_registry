# Typical Command Lines

Run tests:
```shell
$ pytest
```

Run tests and show coverage:
```shell
$ coverage run && coverage html && open htmlcov/index.html
```

Mypy:
```shell
$ mypy apps/registry
```

# Create Database

Create the database directory:

```shell
$ mkdir databases/postgres
```

Initialize the database:

```shell
$ initdb -D databases/postgres
```

Start the postgres server:

```shell
$ honcho start
```

Create the application database:

```shell
$ createdb cast_registry
```

Create the database user:

```shell
$ createuser cast_registry
```

Grant access for database to user:

```shell
$ psql -d cast_registry -c "GRANT ALL PRIVILEGES ON DATABASE cast_registry to cast_registry;"
```

Migrate:

```shell
$ python manage.py migrate
```

# Services

There are two preconfigured services for [fastdeploy](https://github.com/ephes/fastdeploy)
living in the `ansible` directory:
- registry
- cast
- wordpress

The registry service is used to deploy other things like cast hosting or wordpress services.
It's deployed via:
```
$ ansible-playbook register.yml
```
