#!/usr/bin/env bash
# This shell script can be used to invoke the fingerprinter to
# smartly build and cache docker layers based on your fingerprint configuration.
#
# `fingerprinter -o build-script` will always output the absolute path to this script
# within your environment.
#
# You can invoke this script from the shell with:
#   $(fingerprinter -o build-script)
#
#
# It would be great if this were a python script instead of a shell script,
# so that it would be more portable across platforms. The python docker library
# could be used to actually execute builds.
#

function print_help {
   cat <<EOF
   Use: build-layers.sh [--debug --help]
   Options:
   -t, --add-tag   Can be supplied multiple times. Tags each layer with this
                   additional tag.

   --release <V>   Creates a "release" image with your app name and the given release
                   version. Note that releases are not necessarily deployments. You
                   must have a release-target defined in your configuration.

   -f, --force     Execute docker builds even if no changes are detected

   -c, --config-file  The name of your config file. The default is 'fingerprints.yaml'

   -h, --help      Show this message and exit
   -g, --debug     Show commands as they are executing
EOF
}

fingerprint_args=""
target_config=""
fingerprint_config_file='fingerprints.yaml'
release_tag=""


function parse_args {
  while (( $# ))
  do
    case $1 in
      --help|-h)
        print_help
        exit 0
        ;;
      -g|--debug)
        DEBUG=1
        ;;
      --release)
        shift
        release_tag="${1}"
        ;;
      -c|--config)
        shift
        fingerprint_config_file="${1}"
        ;;
      -f|--force)
        FORCE_REBUILD=1
        ;;
      --cache)
        CACHE_LAYERS=1
        ;;
      -t|--add-tag)
        shift
        ADDITIONAL_TAGS+="${1} "  # whitespace intentional
        ;;
      --build-arg)
        shift
        arg_name="${1}"
        fingerprint_args+="--build-arg ${arg_name} "  # whitespace intentional
        ;;
      *)
        echo "Invalid Option: $1"
        print_help
        return 1
        ;;
    esac
    shift
  done

  test -z "${DEBUG}" || set -x
  export DEBUG="${DEBUG}"
}

function get_layer_tag {
  local layer_name="$1"
  local tag="$2"
  echo "${DOCKER_REPOSITORY}.${layer_name}:${tag}"
}


function image_exists_locally {
  test -n "$(docker images -q ${image_tag} 2>/dev/null)" || return 1
}

function build_target {
  local target_name=$1
  local target_config=$(fingerprinter_run -t ${target_name} -o json $fingerprint_args)
  local docker_cmd=$(echo "$target_config" | jq -r .dockerCommand)
  local image_tag=$(echo "$target_config" | jq -r .dockerTag)
  local fingerprint=$(echo "$target_config" | jq -r .fingerprint)
  local target_layer=$(echo "$target_config" | jq -r .dockerTarget)

  log_prefix="[${target_layer}:${fingerprint}]"
  echo "${log_prefix} Reconciling layer"
  if $(image_exists_locally "${image_tag}" >/dev/null) || $(docker pull -q "${image_tag}" >/dev/null)
  then
    echo "${log_prefix} Image already built"
    if [[ -n "${FORCE_REBUILD}" ]]
    then
      echo "${log_prefix} Rebuilding"
    else
      echo "${log_prefix} Nothing to do"
      tag_and_push_image ${image_tag}
      return
    fi
  else
    echo "${log_prefix} Image not found. Building!"
  fi
  $docker_cmd || return 1
  tag_and_push_image "${image_tag}"
}

function tag_and_push_image {
  local source_image_name="${1}"
  test -z "${CACHE_LAYERS}" || docker push ${source_image_name}
  local source_image_base_name=$(echo ${source_image_name} | cut -f1 -d:)
  tags="${ADDITIONAL_TAGS}"
  for tag in ${ADDITIONAL_TAGS}
  do
    local dest_image_name="${source_image_base_name}:${tag}"
    echo "Tagging ${dest_image_name}"
    docker tag ${source_image_name} ${dest_image_name}
    test -z "${CACHE_LAYERS}" || docker push ${dest_image_name}
  done
}

function fingerprinter_run {
  fingerprinter -f "${fingerprint_config_file}" $@
}

function build_targets {
  local targets="$(fingerprinter_run -o build-targets)"
  for target in $targets
  do
    echo "[${target}]"
    if ! build_target "${target}"
    then
      echo "Build of ${target} exited with status $?"
      return 1
    fi
    echo
  done
}

function tag_release {
  local release_target=$(fingerprinter_run -o release-target)
  local release_target=$(fingerprinter_run -t ${release_target} -o json)
  local source_image=$(echo "$release_target" | jq -r .dockerTag)
  local image_name=$(echo "${source_image}" | cut -f1 -d:)
  # We also want to slice off the `.layer-name` from the end, so that we
  # are tagging the "root" image for the app.  We don't know how many
  # dots might appear in the image name, but we can probably assume
  # it will be fewer than 99; we reverse the name, slice at the (now)
  # first dot, then reverse it again.
  image_name=$(echo "${image_name}" | rev | cut -f2-99 -d. | rev)
  local release_image="${image_name}:${release_tag}"
  echo "Tagging release image: ${release_image}"
  docker tag "${source_image}" "${release_image}"
}

parse_args "$@" || exit 1

if ! type jq >/dev/null
then
  >&2 echo "jq is not installed. Cannot continue."
  >&2 echo "Find and install the right release for you: https://stedolan.github.io/jq/download/"
  exit 1
fi

if [[ -z "${SKIP_POETRY_INSTALL}" ]]
then
  output=$(poetry install --no-interaction)
  if [[ "$?" != "0" ]]
  then
    >&2 echo $output
    exit 1
  fi
fi

build_targets
if [[ -n "${release_tag}" ]]
then
  tag_release
fi
