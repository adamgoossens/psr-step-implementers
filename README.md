# Custom Ploigos Step Implementers

This is my working location for step implementers that are under development.

## shell

This allows you to execute arbitrary commands in the container. Example:

```
  container-image-static-compliance-scan:
  - name: acs-build-policy-check
    implementer: user.Shell
    config:
      shell-script: |
        export ROX_API_TOKEN
        roxctl -e "$ROX_CENTRAL_ADDRESS" image check --json --image $IMAGE_TAG --insecure-skip-tls-verify --json-fail-on-policy-violations=false > policy-check-results
        echo "Check results from ACS policy" > artifacts/policy-check-results
        echo "$(pwd)/policy-check-results" >> artifacts/policy-check-results        
      shell-parameters:
        IMAGE_TAG: ${container-image-tag}
        ROX_API_TOKEN: ${acs-api-token}
        ROX_CENTRAL_ADDRESS: ${acs-endpoint-url}
```

The `bash` shell is used to execute the script, so `bash` must be present in the container.

### Passing in artifacts

Artifacts can be passed in via environment variables set by the implementer when
the bash shell is executed. The `${artifact}` syntax allows you to specify which
artifact you want passed in under that environment variable. In the example above,
the artifacts `container-image-tag`, `acs-api-token` and `acs-endpoint-url` are
passed in under the `IMAGE_TAG`, `ROX_API_TOKEN` and `ROX_CENTRAL_ADDRESS` environment
variables.

You can omit the `${}` syntax to pass strings directly in via environment variables.

### Saving artifacts and evidence

Artifacts and evidence are saved under the `artifacts` and `evidence` directories
under the script current working directory.

Each artifact or piece of evidence is a single file. The name of the file is the name of
the artifact or evidence, and the contents of that file must look like so:

```
The first line is the description
Everything after the first line is the value of the artifact or evidence
```

The first line of the file is taken to be the description of that artifact or piece of evidence.
Everything following the first line is the value.

Example:

```
$ cat evidence/compliance-check-result
The result of the Stackrox build time compliance check
pass
```

The implementer will loop through all of these files and add the artifact/evidence
to the step result. They will then be available to steps later in the pipeline.
