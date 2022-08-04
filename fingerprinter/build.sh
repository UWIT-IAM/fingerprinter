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
   -b, --build-arg  Provide a "key=value" argument to pass into the docker builds
                    where configured.

   --cache          When used, will push all images that are built.

   -c, --config-file  The name of your config file. The default is 'fingerprints.yaml'

   -d, --deploy <stage>  Creates a deployment image tagged in a format that
                         can use the uw-iti-app-platform/basic-web-service
                         helm chart for automation. The tag will be in the format:
                            deploy-<stage>.YYYY.MM.DD.hh.mm.ss.v<deploy-version>

                         The resulting tag will always be pushed, unless '-dx' is
                         passed.
     The following options can be supplied along with the --deploy directive:

     -ddry                   Build the deployment image, but do not push it.
     -ddockerfile   <D>      Supply a path to a dockerfile you want to use instead of
                             the one provided.
     -dv, -dversion <V>      Supply the version that you want to deploy.
                             Not required if using the '--release' flag.


   -f, --force     Execute docker builds even if no changes are detected

   -g, --debug     Show commands as they are executing
   -h, --help      Show this message and exit

   -p, --poetry    Use this mode if fingerprinter is installed in a poetry environment.
                   This ensures that the build script will run the python module inside
                   a poetry env.

                     '$(poetry run fingerprinter -o build-script) -p # ...'

   --release <V>   Creates a "release" image with your app name and the given release
                   version. Note that releases are not necessarily deployments. You
                   must have a release-target defined in your configuration.

   -t, --add-tag   Can be supplied multiple times. Tags each layer with this
                   additional tag.

EOF
}

fingerprint_args=""
fp_prefix=""  # Updated by the -p tag to ensure fingerprinter runs inside poetry
              # without the user having to explicitly open the poetry shell.
target_config=""
fingerprint_config_file='fingerprints.yaml'
release_tag=""
source_image=""  # Updated if a release and/or deployment is created
app_image_name=""  # Updated if a release and/or deployment is created
deploy_dockerfile="$(dirname $0)/deployment.dockerfile"


function parse_args {
  while (( $# ))
  do
    case $1 in
      -b|--build-arg)
        shift
        arg_name="${1}"
        fingerprint_args+="--build-arg ${arg_name} "  # whitespace intentional
        ;;
      --cache)
        CACHE_LAYERS=1
        ;;
      -c|--config)
        shift
        fingerprint_config_file="${1}"
        ;;
      -d|--deploy)
        shift
        deploy_stage="${1}"
        ;;
      -ddry)
        deploy_dry=1
        ;;
      -dv|-dversion)
        shift
        deploy_version="${1}"
        ;;
      -ddockerfile)
        shift
        deploy_dockerfile=${1}
        ;;
      -f|--force)
        FORCE_REBUILD=1
        ;;
      -g|--debug)
        DEBUG=1
        ;;
      --help|-h)
        print_help
        exit 0
        ;;
      --poetry|-p)
        fp_prefix="poetry run"
        ;;
      --release)
        shift
        release_tag="${1}"
        ADDITIONAL_TAGS+="${release_tag} "
        ;;
      -t|--add-tag)
        shift
        ADDITIONAL_TAGS+="${1} "  # whitespace intentional
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

function image_exists_locally {
  local image=${1:-${image_tag}}
  test -n "$(docker images -q ${image} 2>/dev/null)" || return 1
}

function build_target {
  local target_name=$1
  local target_config=$(fingerprinter_run -t ${target_name} -o json) || return 1
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
  $fp_prefix fingerprinter -f "${fingerprint_config_file}" ${fingerprint_args} $@ || return $?
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

function get_release_target {
  local release_target=$(fingerprinter_run -o release-target) || return $?
  fingerprinter_run -t ${release_target} -o json || return $?
}

function get_app_image_name {
  echo "${1}" | rev | cut -f2-99 -d. | rev
}

function tag_release {
  local release_target="$(get_release_target)" || return $?
  local source_image=$(echo "$release_target" | jq -r .dockerTag)
  local app_image=$(get_app_image_name "${source_image}")
  local release_image="${app_image}:${release_tag}"
  echo "Tagging release image: ${release_image}"
  docker tag "${source_image}" "${release_image}"
  test -z "${CACHE_LAYERS}" || docker push "${release_image}"
}

function deploy {
  local deploy_version=${deploy_version:-${release_tag}}
  if [[ -z "${deploy_version}" ]]
  then
    echo "Could not determine version to deploy. Please provide the -dv/-dversion
          argument or create a new release with '--release'"
  fi
  local deploy_ts="$(date +%Y.%m.%d.%H.%M.%S)"
  local deploy_id="${deploy_ts}.v${deploy_version}"
  local deploy_tag="deploy-${deploy_stage}.${deploy_id}"
  local release_target=$(get_release_target | jq -r .dockerTag)
  local app_image="$(get_app_image_name ${release_target})"
  local source_image="${app_image}:${deploy_version}"
  local deploy_image="${app_image}:${deploy_tag}"
  if image_exists_locally ${source_image} || docker pull ${source_image}
  then
    docker build -f $deploy_dockerfile \
      --build-arg IMAGE=${source_image} \
      --build-arg DEPLOYMENT_ID="${deploy_id}" \
      -t ${deploy_image} .
    test -n "${deploy_dry}" || docker push ${deploy_image}
    return
  fi
  echo "Expected to find ${source_image} locally or in the docker repository, but it
        did not exist."
  return 1
}

parse_args "$@" || exit 1

if ! type jq >/dev/null
then
  >&2 echo "jq is not installed. Cannot continue."
  >&2 echo "Find and install the right release for you: https://stedolan.github.io/jq/download/"
  exit 1
fi

# If a user is only deploying a pre-built release, we don't need to
# re-build.
if [[ -z "${deploy_stage}" ]] || [[ -n "${release_tag}" ]]
then
  build_targets
fi

if [[ -n "${release_tag}" ]]
then
  tag_release || exit $?
fi

if [[ -n "${deploy_stage}" ]]
then
  deploy || exit $?
fi
