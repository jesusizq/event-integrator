#!/bin/sh

usage() {
    SCRIPT_NAME=$(basename "$0")
    echo "Usage: $SCRIPT_NAME [-n <name>] [-e <env>] [-d] [-c] [up|up-and-force|build|down|down-and-remove|stop|purge|stop-and-remove|--help]"
    echo "  up              - Runs the container"
    echo "  up-and-force    - Runs the container and force recreate"
    echo "  build           - Builds images without starting containers"
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

# Initialize variables
SERVICE=""
ENV="dev"
DETACHED_MODE=""
NO_CACHE=""
# COMMAND will be determined after options are parsed

# Process options. Options must come before the command.
while getopts ":n:e:dc" opt; do
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
        d )
            DETACHED_MODE="-d"
            ;;
        c )
            NO_CACHE="--no-cache"
            ;;
        \\? ) # Invalid option
            echo "Invalid option: -$OPTARG" 1>&2
            usage
            ;;
        : ) # Missing option argument
            echo "Option -$OPTARG requires an argument." 1>&2
            usage
            ;;
    esac
done

# Shift away the parsed options and their arguments
shift $((OPTIND - 1))

# The first remaining positional argument is the command
COMMAND="$1"

# Handle --help command
if [ "$COMMAND" = "--help" ]; then
    usage
fi

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

# Check if a command was provided
if [ -z "$COMMAND" ]; then
    echo "ERROR: No valid command specified"
    usage
fi

# Check if SERVICE is required for certain commands (must happen after COMMAND is known)
if [ -z "$SERVICE" ] && [ "$COMMAND" != "up" ] && [ "$COMMAND" != "up-and-force" ] && [ "$COMMAND" != "build" ] && [ "$COMMAND" != "down" ] && [ "$COMMAND" != "down-and-remove" ]; then
    echo "ERROR: Service name is required for the command '$COMMAND'"
    usage
fi

COMPOSE_FILE="docker/docker-compose.yml"

echo "Docker with $ENV_FILE"

# Validate and run the command
case "$COMMAND" in
    up)
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
    build)
        echo "Building images..."
        docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" build $NO_CACHE
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
        echo "ERROR: Invalid command: '$COMMAND'"
        usage
        ;;
esac