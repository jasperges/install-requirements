# -*- coding: utf-8 -*-
"""Install the given requirements with pip
"""

import os
import tempfile
import importlib.util
import subprocess
import urllib.request
import urllib.error
import json
import logging

import bpy


class Requirements(object):
    """A class to hold the requirements and perform the needed actions

    Args:
        requirements (list): A list of dictionaries describing the
            dependencies. The dictionaries should have the keys `pip`,
            `module` and `version`. `pip` should have the name of the package
            used by pip, `module` should be the name of the module that can be
            imported with `version` you can specify the version. If `version`
            is None, the latest version will be installed.
    """

    def __init__(self, requirements):
        self._logger = logging.getLogger("install_requirements.Requirements")
        self.requirements = self._get_requirements(requirements)
        self._requirements_to_install = self.check_requirements()

    def _get_requirements(self, requirements):
        """Set the requirements from the list or file

        Returns:
            list of dict: The requirements information from the list or
            json file.
            The keys are "pip" (the name used by pip), "module" (the name of the
            module) and "version". The version can be None. If a version is given
            that specific version will be installed.
        """
        if isinstance(requirements, str):
            requirements_filepath = requirements
            if not os.path.isfile(requirements_filepath):
                self._logger.error("File not found: %s", requirements_filepath)
                return
            with open(requirements_filepath, "r") as requirements_file:
                requirements = json.load(requirements_file)
        return requirements


    def _is_pip_installed(self):
        """Check if pip is installed

        Returns:
            bool: True if pip is installed, False otherwise.
        """
        if importlib.util.find_spec("pip"):
            self._logger.debug("Pip is already installed.")
            return True
        else:
            self._logger.debug("Pip is not installed.")
            return False


    def _download_get_pip(self):
        """Download the `get-pip.py`

        Returns:
            str or None: the local filename if the download was successful,
                        None otherwise.
        """
        get_pip_url = "https://bootstrap.pypa.io/get-pip.py"
        get_pip_file = os.path.join(
            tempfile.gettempdir(),
            os.path.basename(get_pip_url),
            )
        try:
            local_file, headers = urllib.request.urlretrieve(get_pip_url, get_pip_file)
            self._logger.debug("`get-pip.py` successfully downloaded.")
            return local_file
        except urllib.error.URLError:
            self._logger.error("Couldn't download `get-pip.py`.", exc_info=True)


    def _install_pip(self, timeout=120):
        """Install pip

        Args:
            timeout (int): The timeout for the Popen process in seconds. If the
                        install process runs longer then this, it is killed.

        Returns:
            bool: True if installation of pip was successful, False otherwise.
        """
        get_pip_file = self._download_get_pip()
        if get_pip_file is None or not os.path.isfile(get_pip_file):
            return False
        proc = subprocess.Popen(
            [bpy.app.binary_path_python, get_pip_file],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            )
        try:
            outs, errs = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            outs, errs = proc.communicate()
        finally:
            os.remove(get_pip_file)
        if proc.returncode == 0:
            self._logger.debug("Pip successfully installed.")
            return True
        else:
            self._logger.error("Pip wasn't installed.\n%s", errs.decode('utf-8'))
            return False


    def _install_requirements(self):
        """Install the requirements with pip
        """
        pip_args = [requirement['pip'] for requirement in self._requirements_to_install]
        pip_args.insert(0, 'install')
        try:
            import pip
            pip.main(pip_args)
        except:
            self._logger.error(
                "An error occurred when installing the dependencies with pip.",
                exc_info=True,
                )


    def check_requirements(self):
        """Check if all requirements are available

        Returns:
            list: a list containing the requirements that are not available
                (can be an empty list).
        """
        not_installed_requirements = []
        for requirement in self.requirements:
            if not importlib.util.find_spec(requirement['module']):
                not_installed_requirements.append(requirement)
        return not_installed_requirements


    def install(self):
        """Ensure all needed requirements are available

        Check if the requirements are installed. If they are not try to install
        them with pip. If pip is not installed, try to install pip first.

        """
        if not self._requirements_to_install:
            self._logger.info("All requirements are available.")
            return
        if not self._is_pip_installed():
            if not self._install_pip():
                self._logger.error(
                    "Pip is not available and could not be installed. "
                    "Requirements are not satisfied.",
                    )
                return
        self._install_requirements()
