## Installation for development

### Create a venv & activate it and install the dev requirements
```shell
     uv venv -p python3.13
     source .venv/bin/activate.fish
     uv sync
```

### Set up the database
```shell
    initdb databases/postgres
    postgres -D databases/postgres  # in a different terminal tab
    createdb cast_registry
    createuser cast_registry
    python manage.py migrate
```

### Run the tests
```shell
    pytest
```

Run tests and show coverage:
```shell
$ coverage run && coverage html && open htmlcov/index.html
```

Mypy:
```shell
$ mypy apps/registry
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
