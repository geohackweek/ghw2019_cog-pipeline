# Tiler API

A lightweight dynamic tiler

![](https://user-images.githubusercontent.com/10407788/56367726-e4674180-61c3-11e9-86e4-c8825cc75677.png)

# Deployment

## Build Docker image

    $ docker build . -t tiler-api:latest

or

    $ docker-compose build base

## Package Lambda

    $ docker-compose run --rm package

## Tests

    $ docker-compose run --rm test


## Deploy to AWS

    $ brew install terraform
    # Set ${AWS_ACCESS_KEY_ID} and ${AWS_SECRET_ACCESS_KEY} in your env
    $ terraform init
    $ terraform apply --var region=us-east-1

# API

see [API.md](docs/API.md)

# Examples

see [demo/](demo/)


## About
Created by [Development Seed](<http://developmentseed.org>)
