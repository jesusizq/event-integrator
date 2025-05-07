#!/bin/sh

usage() {
    SCRIPT_NAME=$(basename "$0")
    echo "Usage: $SCRIPT_NAME [-n <name>] [-e <env>] [-d] [-c] [up|up-and-force|down|down-and-remove|stop|purge|stop-and-remove|--help]"
    echo "  up              - Runs the container"
    echo "  up-and-force    - Runs the container and force recreate"
    echo "  down            - Stops containers"
    echo "  down-and-remove - Stops and removes containers, volumes, and images"
    echo "  stop            - Stops a container without removing it"
    echo "  purge           - Stops, removes a container, its volumes, and prunes unused images"
    echo "  stop-and-remove - Stops and removes a container"
    echo "  --help          - Displays this help message"
    echo "  -n <name>       - The name of the docker service (optional for up, down, down-and-remove)"
    echo "  -e <env>        - Environment: dev or prod (defaults to dev)"
    echo "  -d              - Run in detached mode (only for up and up-and-force)"
    echo "  -c              - Build images with --no-cache (only for up and up-and-force)"
    exit 1
}

# Store all arguments
ALL_ARGS="$@"

# Initialize variables
SERVICE=""
COMMAND=""
ENV="dev"
DETACHED_MODE=""
NO_CACHE=""

# First, find the command in the arguments
for arg in $ALL_ARGS; do
    case "$arg" in
        up|up-and-force|down|down-and-remove|stop|purge|stop-and-remove)
            COMMAND="$arg"
            ;;
    esac
done

# Then process options
while getopts ":n:e:d:c" opt; do
    case ${opt} in
        n )
            SERVICE=$OPTARG
            ;;
        e )
            case $OPTARG in
                dev|prod|test)
                    ENV=$OPTARG
                    ;;
                *)
                    echo "Invalid environment: $OPTARG. Must be dev, prod, or test" 1>&2
                    usage
                    ;;
            esac
            ;;
        d ) # Handle the -d option
            DETACHED_MODE="-d"
            ;;
        c ) # Handle the -c option
            NO_CACHE="--no-cache"
            ;;
        \? )
            echo "Invalid option: $OPTARG" 1>&2
            usage
            ;;
    esac
done

# Set ENV_FILE based on environment
case "$ENV" in
    dev)
        ENV_FILE=".env"
        ;;
    prod)
        ENV_FILE=".env.production"
        ;;
    test)
        ENV_FILE=".env.test"
        ;;
esac

# Check if we have a command
if [ -z "$COMMAND" ]; then
    if [ "$1" = "--help" ]; then
        usage
    fi
    echo "ERROR: No valid command specified"
    usage
fi

# Check if SERVICE is required for the command
if [ -z "$SERVICE" ] && [ "$COMMAND" != "up" ] && [ "$COMMAND" != "up-and-force" ] && [ "$COMMAND" != "down" ] && [ "$COMMAND" != "down-and-remove" ]; then
    echo "ERROR: Service name is required for the command '$COMMAND'"
    usage
fi

COMPOSE_FILE="docker/docker-compose.yml"

echo "Docker with $ENV_FILE"

# Run the command
case "$COMMAND" in
    up)
        echo "Building images..."
        docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" build $NO_CACHE
        echo "Starting containers..."
        docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up $DETACHED_MODE
        ;;
    up-and-force)
        # Note: --force-recreate implies rebuilding if needed, but doesn't control cache.
        echo "Building images..."
        docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" build $NO_CACHE
        echo "Starting containers with --force-recreate..."
        docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up $DETACHED_MODE --force-recreate
        ;;
    down)
        docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down
        ;;
    down-and-remove)
        docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down -v --rmi all --remove-orphans
        ;;
    stop)
        docker compose -f "$COMPOSE_FILE" stop "$SERVICE"
        ;;
    purge)
        docker compose -f "$COMPOSE_FILE" stop "$SERVICE" && \
        docker compose -f "$COMPOSE_FILE" rm -v -f "$SERVICE" && \
        docker rmi $(docker images -q --filter "label=com.docker.compose.service=$SERVICE") && \
        docker image prune -f --filter "label=com.docker.compose.service=$SERVICE"
        ;;
    stop-and-remove)
        docker compose -f "$COMPOSE_FILE" stop "$SERVICE" || \
        docker compose -f "$COMPOSE_FILE" rm -f "$SERVICE"
        ;;
    *)
        echo "ERROR: Invalid command."
        usage
        ;;
esac