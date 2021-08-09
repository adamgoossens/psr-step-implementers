"""A `StepImplementer` that allows a user to run arbitrary shell commands within the container.

Step Configuration
------------------
Step configuration expected as input to this step.
Could come from:

  * static configuration
  * runtime configuration
  * previous step results

Configuration Key  | Required? | Default | Description
-------------------|-----------|---------|-----------
`shell-script`     | Yes       |         | Bash script to run.
`shell-parameters` | No        |         | Environment variables to inject to the script.

Result Artifacts
----------------
Results artifacts output by this step depend on the script that executes.

Artifacts output from this step should be placed within the 'artifacts' subdirectory under
the script's working directory. One file per artifact. The name of the file is the key for
the artifact. The first line of the file is the description for the artifact; everything after
that is taken to be the value.

Evidence from this step must be placed in the 'evidence' subdirectory under the script's
working directory. One file per piece of evidence. The name of the file is the key for the
evidence. The first line of the file is the description for the evidence; everything after that
is taken to be the value.

""" # pylint: disable=line-too-long

import os
import sys
import re
import uuid
import tempfile

from distutils import util

import sh
from ploigos_step_runner import StepImplementer, StepResult

DEFAULT_CONFIG = {
    'shell-parameters': {},
}

REQUIRED_CONFIG_OR_PREVIOUS_STEP_RESULT_ARTIFACT_KEYS = [
    'shell-script'
]

class Shell(StepImplementer):
    """`StepImplementer` to run an arbitrary shell script.
    """

    SUBSTITUTION_REGEX = '\${(?P<key>\S+)}'

    @staticmethod
    def step_implementer_config_defaults():
        """Getter for the StepImplementer's configuration defaults.

        Returns
        -------
        dict
            Default values to use for step configuration values.

        Notes
        -----
        These are the lowest precedence configuration values.
        """
        return DEFAULT_CONFIG

    @staticmethod
    def _required_config_or_result_keys():
        """Getter for step configuration or previous step result artifacts that are required before
        running this step.

        See Also
        --------
        _validate_required_config_or_previous_step_result_artifact_keys

        Returns
        -------
        array_list
            Array of configuration keys or previous step result artifacts
            that are required before running the step.
        """
        return REQUIRED_CONFIG_OR_PREVIOUS_STEP_RESULT_ARTIFACT_KEYS

    def _run_step(self):
        """Runs the step implemented by this StepImplementer.

        Returns
        -------
        StepResult
            Object containing the dictionary results of this step.
        """
        step_result = StepResult.from_step_implementer(self)

        # get shell script - we'll write this to a temporary file
        # then execute it
        script = self.get_value('shell-script')
        parameters = {}
        for param, value in self.get_value('shell-parameters').items():
            # if value starts with ${, then it's a substitution.
            match = re.match(Shell.SUBSTITUTION_REGEX, value)
            if match is not None:
                lookup_key = match.groupdict()['key']
                lookup_value = self.get_value(lookup_key)
                if lookup_value is None:
                    raise ValueError(f'Parameter {param}: config value/artifact with name {lookup_key} does not exist.')
                else:
                    parameters[param] = lookup_value
            else:
                parameters[param] = value

        # script executes in a randomly generated subdirectory under
        # the workdir.
        random_uuid = uuid.uuid4()

        script_workdir = os.path.join(
                          self.work_dir_path,
                          str(random_uuid)
                         )
        evidence_path = os.path.join(
                            script_workdir,
                            'evidence'
                        )
        artifacts_path = os.path.join(
                            script_workdir,
                            'artifacts'
                         )

        os.makedirs(script_workdir, exist_ok=True)
        os.makedirs(evidence_path, exist_ok=True)
        os.makedirs(artifacts_path, exist_ok=True)

        tempfile = os.path.join(
                     script_workdir,
                     'script.sh'
                   )

        with open(tempfile, 'w') as fp:
            fp.write(script)

        try:
            sh.bash(
                tempfile,
                _env=parameters,
                _out=sys.stdout,
                _err=sys.stderr,
                _cwd=script_workdir,
                _tee='err'
            )
        except sh.ErrorReturnCode as error:
            step_result.success = False
            step_result.message = f'Script failed to run: {error}'

        # go through each file in 'artifacts' and 'evidence';
        # populate the artifacts and evidence from the step
        # accordingly
        for f in os.listdir(artifacts_path):
            artifact_name = f
            path = os.path.join(artifacts_path, artifact_name)
            with open(path, 'r', encoding='utf8') as artifact:
                artifact_desc = artifact.readline().strip()
                artifact_value = artifact.read().strip()

            step_result.add_artifact(
                name=artifact_name,
                value=artifact_value,
                description=artifact_desc
            )

        for f in os.listdir(evidence_path):
            evidence_name = f
            path = os.path.join(evidence_path, evidence_name)
            with open(path, 'r', encoding='utf8') as evidence:
                evidence_desc = evidence.readline().strip()
                evidence_value = evidence.read().strip()

            step_result.add_evidence(
                name=evidence_name,
                value=evidence_value,
                desc=evidence_desc
            )

        return step_result
