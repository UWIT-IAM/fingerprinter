# Fingerprinter

This build utility can be used to:

- create fingerprints for any collection of assets in your repository
- associate fingerprint targets with docker build layers, so that you
  can build your appplication artifacts,
  only updating what is necessary based on changes to your repository,
  while still taking advantage of docker's native caching capabilities.


You can choose to use this utility natively by preparing your environment,
but you can also invoke a docker image. Refer to [invoking the docker image](#invoking-the-docker-image).

Requirements for direct use:

- python 3.8+
- To use the `build-script` utility, you must have `jq` installed. 



## Installation

```
pip install uw-it-build-fingerprinter
```

## Use

You can invoke the fingerprinter yourself:

```
# linux/unix shell
fingerprinter -f build-config.yaml -t target -o json
```

You can also use the fingerprinter to run your builds:

```
$(fingerprinter -o build-script) --build-arg foo=bar
```


### Configuration File

In most situations, you can just create your config file, and then
invoke the provided build script. 

Below is a fully annotated configuration file.

For a more practical example, refer to [fingerprints.yaml](fingerprints.yaml).

```yaml
# ALL FIELDS ARE OPTIONAL

# This example shows all possible fields and examples of how to use them.
# You do not need redefine or use every field.

# If there are paths you always want to ignore, no matter the target,
# you may include them here. .pyc, __pycache__, and .pytest_cache files are
# always ignored no matter what is listed here.
ignore-paths:  # Default: empty
  - '**/ignore-me.py'  # Ignore every 'ignore-me.py' in the tree
  - 'src/special/ignore-me-also.py'  # Ignores this specific file 


# If you are taking advantage of the build capabilities, you need
# to define some information about your project's docker context
# You can omit the docker section entirely if you 
# are only interested in fingerprinting
docker:
    # The path to the dockerfile your builds will use, relative to your working
    # directory. This can be overridden on a target-by-target basis.
    dockerfile: Dockerfile  # default is 'Dockerfile'
    
    # Define your docker repository; this is used to push, pull, and build images
    repository: ghcr.io/uwit-iam  # (default: empty)
    
    # This is used to push, pull, and build images.
    app-name: fingerprinter  # (default: empty)
    
    build-args:
      # In the list of args, each entry requires an 'arg' field, which defines
      # the name of the arg as it appears in your dockerfile.
      # In this example, you would expect to find the line:
      #   `ARG BUILD_ID` somewhere in the associated dockerfile.
      - arg: BUILD_ID
        # You can pass build-arg values into the fingerprinter cli
        # using `--build-arg name=value`. You can also set them
        # as environment variables.
        #
        # The 'sources' configuration allows you to tweak where
        # values are accepted from, and in what order. The higher
        # a source is on this list, the higher its precedence. 
        # 
        sources:  # default: ['cli', 'env']
          # You can wire in the fields from any other target by
          # using the format: "target:<target-name>:<field-name>
          # Available fields are:
          #  - fingerprint
          #  - dockerTag
          #  - dockerCommand
          #  - dockerTarget
          #  - dockerfile
          # Be aware that this sets up a passive dependency on that target.
     
          # In this example, we are setting the BUILD_ID to be the fingerprint of 
          # the build-config target, and since this is in the global docker
          # config, it will be shared for all layers!
          - target:build-config:fingerprint
          
          # The 'cli' source will search for the arg from the passed command line
          # args. (e.g., `fingerprinter -t app --build-arg BUILD_ID=foo`)
          - cli  
          
          # The 'env' source will search environment variables for the 
          # value. In our example, we would expect the 'BUILD_ID' environment 
          # variable to be set.
          - env  
 

# You can set one of your build targets as a release target. 
# When you want to build a release image (i.e., an updated version number), 
# the current configuration of this target will be used to tag
# the new release image. 
# The new release image will be tagged using the app name and the release name
# only (no layer annotations).
# In this example, ghcr.io/uwit-iam/fingerprinter.app:f1ng3rpr1nt
# would be re-tagged as ghcr.io/uwit-iam/fingerprinter:1.2.3 (assuming 1.2.3 was the 
# release name).
release-target: app 

# A "target" represents a collection of files whose contents are
# hashed together to create a unique fingerprint. Targets can depend on other targets.
# 
# If any of a target's files or dependencies changes, the fingerprint for that target
# will also change. 
targets:
  # Name your target here. If you are using docker layers, it is easiest to 
  # name your docker layers and targets the same, however it is possible to 
  # associate them if you want to name them differently.
  # This target is named "build-config"; you can name it whatever you like.
  build-config:
    # Some targets are only used for fingerprinting and not builds; if you don't wish
    # to try and build a docker layer associated with a target, you can set this to
    # false.
    build-target: false  # default: true
   
    # Each line of include-paths is a glob representing a directory, filename,
    # or collection of files that should be included when calculating a 
    # target's fingerprint. A later example in this file will show other
    # ways to use include-paths.
    include-paths:
      - Dockerfile
      - poetry.lock
      - fingerprints.yaml
  
  app:  # This is a target named "app"; you can name it whatever you like.
    # You can declare dependencies on other targets,
    # to ensure that a target will be rebuilt if one of 
    # its dependencies changes.
    depends-on: [build-config]  # default: empty
    
    docker:
      # You can use a different dockerfile for a target, if the target
      # is not configured in the root dockerfile
      dockerfile: alternate.dockerfile  # (default: empty)
      
      # If your target and your docker layer have different names,
      # you can associate the correct docker target here.
      # In this example, you would expect to find something like:
      #    FROM ubuntu:latest AS runtime
      target: runtime  # (default: empty)

      # Build args here work the same as they do in the global docker config.
      # These can be defined in addition to the globally configured args.
      # In this example, we are requiring that it be passed in via the CLI.
      build-args:
        - arg: APP_VERSION
          sources: [cli]
```

**All paths will be lexicographically sorted at runtime**, however dependencies
are always resolved in the order provided.


## Publishing a new release

To publish a new release of this tool, use `poetry`
to update the version (e.g., `poetry version minor`).

Make sure to `git add` and `git commit` to commit the version to the repository. 

Then, run `poetry build && poetry publish`

You will need credentials which authenticated IAM maintainers can obtain from 
the mosler vault at: kv/data/team-shared/pypi.org

## Invoking the docker image

```
 docker run \
  # Mount your current directory onto the container so that the utility
  # can read your configuration and file contents to generate fingerprints.
  --mount "type=bind,source=$(pwd),target=/app" \
  # Set the working directory to the mount
  -w /app -it ghcr.io/uwit-iam/fingerprinter:0.2.3 
  # After the image name, provide args to the fingerprinter utility
  # just like you would if you are running it natively.
  -t cli
```

One limitation of invoking this via docker is that you cannot
invoke the build script, because without a sophisticated setup,
you can't build docker images inside another docker image.
