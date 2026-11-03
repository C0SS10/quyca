<center><img src="https://raw.githubusercontent.com/colav/colav.github.io/master/img/Logo.png"/></center>

# Quyca

ImpactU Backend written in Python with flask, it is used to provide the API for the Colav platform.

# Installation

## Dependencies

Docker and docker-compose is required.

- https://docs.docker.com/engine/install/ubuntu/ (or https://docs.docker.com/engine/install/debian/, etc)
- Install `docker-compose`:

```bash
apt install docker-compose
```

or

```bash
pip install docker-compose
```

- https://docs.docker.com/engine/install/linux-postinstall/

- Deploy Elastic Search from Chia https://github.com/colav/Chia/tree/main/elasticsaerch

To install the package, you can use the following command:

```shell
pip install quyca
```

But this package us deployed with docker, then you need to install docker and docker-compose to run the package.

To deploy, copy `.env.example` to:
- `.env.dev` for the development environment (`develop` branch).
- `.env.prod` for the production environment (`main` branch).

### Pre-commit

If you dont have pre-commit installed

```bash
poetry add --dev pre-commit
```

Then install the hook in `.pre-commit-config.yaml` in your local repo, using:

```bash
pre-commit install
```

And then you have it. But it is **important that you have poetry, pre-commit and pre-commit hook installed.**

## Data

Required data is stored in MongoDB, produced with kahi.
usually database named kahi or kahi_dev, please read

# Usage

Copy `.env.example` to `.env.dev` or `.env.prod` and set the variables. Every variable is documented there;
the ones marked *(optional)* have a default. The file is selected by `ENVIRONMENT` (`dev` | `prod`),
which each Docker target already sets. Real environment variables override the file.

Please read the Makefile to see the available commands to run the package.
https://github.com/colav/quyca/blob/develop/Makefile

The API has no route prefix: the web application and the expert API share the same endpoints.

- Development: https://api.dev.impactu.colav.co/your/endpoint/here
- Local: http://localhost:8080/your/endpoint/here (`APP_PORT` in the .env file)

# Start the application

```bash
make up-dev    # build and start the dev container (gunicorn with auto-reload if APP_DEBUG=True)
make logs-dev  # follow the logs
```

or

```bash
make up-prod   # build and start the prod container
make logs-prod # follow the logs
```

## Running tests

```bash
make tests-dev    # to run the tests
```

could be the same for prod with

```bash
make tests-prod    # to run the tests
```

### Format the code

Dependencies:

```shell
pip install black poetry autoflake
```

To format the code, you can use the following command:

```shell
python format.py
```

# List of endpoints

Run the next command to see the list of endpoints

```bash
docker compose  exec dev bash
```

luego dentro del contenedor

```bash
FLASK_APP='app' flask routes
```

# License

BSD-3-Clause License

# Links

http://colav.udea.edu.co/

## Business Rules

- Staff validation and normalization: docs/business-rules/staff-validation-normalization.md

## Conventions

- Naming of modules, functions and parameters: docs/conventions/naming.md
